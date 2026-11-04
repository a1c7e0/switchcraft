#include "download.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

#ifdef __SWITCH__
extern "C" {
#include <switch/crypto/sha1.h>
#include <switch/crypto/sha256.h>
}
#else
#include <openssl/evp.h>
#endif
#include <curl/curl.h>

namespace sc {
namespace {
struct CurlRegistry {
    std::mutex mutex;
    std::vector<CURL **> handles;
    bool initialized = false;
};

CurlRegistry &curl_registry() {
    // Keep registry lifetime beyond C++ static destruction so late TLS
    // destructors can safely observe handles cleared by explicit shutdown.
    static CurlRegistry *registry = new CurlRegistry;
    return *registry;
}

struct ThreadCurl {
    CURL *handle = nullptr;
    ~ThreadCurl() {
        auto &registry = curl_registry();
        std::lock_guard<std::mutex> lock(registry.mutex);
        if (handle)
            curl_easy_cleanup(handle);
        auto it = std::find(registry.handles.begin(), registry.handles.end(), &handle);
        if (it != registry.handles.end())
            registry.handles.erase(it);
    }
};

CURL *get_thread_curl() {
    static thread_local ThreadCurl local;
    auto &registry = curl_registry();
    std::lock_guard<std::mutex> lock(registry.mutex);
    if (!registry.initialized) {
        if (curl_global_init(CURL_GLOBAL_DEFAULT) != CURLE_OK)
            throw std::runtime_error("Cannot initialize HTTPS transport");
        registry.initialized = true;
    }
    if (!local.handle) {
        local.handle = curl_easy_init();
        if (!local.handle)
            throw std::runtime_error("Cannot create HTTPS request");
        registry.handles.push_back(&local.handle);
    }
    return local.handle;
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(),
                   [](unsigned char c) { return (char)std::tolower(c); });
    return value;
}

void validate_url(const std::string &url, bool allow_http) {
    if (url.empty() || url.find_first_of("\r\n\t") != std::string::npos)
        throw std::runtime_error("Invalid download URL");
    const auto scheme = lower(url.substr(0, std::min<size_t>(url.size(), 8)));
    if (scheme.rfind("https://", 0) != 0 && !(allow_http && scheme.rfind("http://", 0) == 0))
        throw std::runtime_error("Only HTTPS download URLs are allowed");
}

std::string digest_hex(const unsigned char *data, size_t size) {
    static const char digits[] = "0123456789abcdef";
    std::string out(size * 2, '0');
    for (size_t i = 0; i < size; ++i) {
        out[2 * i] = digits[data[i] >> 4];
        out[2 * i + 1] = digits[data[i] & 15];
    }
    return out;
}

class Digest {
  public:
    explicit Digest(const std::string &algorithm) : algorithm_(lower(algorithm)) {
        if (algorithm_ != "sha1" && algorithm_ != "sha256")
            throw std::runtime_error("Unsupported digest algorithm");
#ifdef __SWITCH__
        if (algorithm_ == "sha1") {
            sha1ContextCreate(&sha1_);
        } else {
            sha256ContextCreate(&sha256_);
        }
#else
        context_ = EVP_MD_CTX_new();
        if (!context_ ||
            EVP_DigestInit_ex(context_, algorithm_ == "sha1" ? EVP_sha1() : EVP_sha256(), nullptr) != 1)
            throw std::runtime_error("Cannot initialize digest");
#endif
    }

    ~Digest() {
#ifdef __SWITCH__
        // libnx contexts own no external resources.
#else
        EVP_MD_CTX_free(context_);
#endif
    }

    void update(const void *data, size_t size) {
#ifdef __SWITCH__
        if (algorithm_ == "sha1")
            sha1ContextUpdate(&sha1_, data, size);
        else
            sha256ContextUpdate(&sha256_, data, size);
#else
        if (EVP_DigestUpdate(context_, data, size) != 1)
            throw std::runtime_error("Digest update failed");
#endif
    }

    std::string finish() {
        unsigned char out[32]{};
        size_t size = 0;
#ifdef __SWITCH__
        if (algorithm_ == "sha1")
            sha1ContextGetHash(&sha1_, out);
        else
            sha256ContextGetHash(&sha256_, out);
        size = algorithm_ == "sha1" ? 20 : 32;
#else
        unsigned int output_size = 0;
        if (EVP_DigestFinal_ex(context_, out, &output_size) != 1)
            throw std::runtime_error("Digest finalization failed");
        size = output_size;
#endif
        return digest_hex(out, size);
    }

  private:
    std::string algorithm_;
#ifdef __SWITCH__
    Sha1Context sha1_{};
    Sha256Context sha256_{};
#else
    EVP_MD_CTX *context_ = nullptr;
#endif
};

std::string hash_file(const std::string &path, const std::string &algorithm, uint64_t &size) {
    std::ifstream in(path, std::ios::binary);
    if (!in)
        throw std::runtime_error("Cannot read existing destination");
    Digest digest(algorithm);
    std::array<char, 64 * 1024> buffer{};
    size = 0;
    while (in) {
        in.read(buffer.data(), buffer.size());
        const auto count = in.gcount();
        if (count > 0) {
            size += static_cast<uint64_t>(count);
            digest.update(buffer.data(), static_cast<size_t>(count));
        }
    }
    if (!in.eof())
        throw std::runtime_error("Cannot read existing destination");
    return digest.finish();
}

void validate_target(const std::string &target) {
    if (target.empty() || target.find_first_of("\r\n\t") != std::string::npos)
        throw std::runtime_error("Invalid download destination");
    struct stat st{};
    if (lstat(target.c_str(), &st) == 0 && (!S_ISREG(st.st_mode) || S_ISLNK(st.st_mode)))
        throw std::runtime_error("Download destination is not a regular file");
    std::string parent = ".";
    const auto slash = target.find_last_of('/');
    if (slash != std::string::npos)
        parent = slash == 0 ? "/" : target.substr(0, slash);
    if (lstat(parent.c_str(), &st) != 0 || !S_ISDIR(st.st_mode) || S_ISLNK(st.st_mode))
        throw std::runtime_error("Download destination directory is unavailable");
}

struct Transfer {
    int fd = -1;
    std::string text;
    Digest *digest = nullptr;
    uint64_t bytes = 0;
    uint64_t max_bytes = 0;
    uint64_t total = 0;
    DownloadCallbacks callbacks;
    std::string error;
    bool too_large = false;
};

size_t receive_data(char *ptr, size_t size, size_t nmemb, void *opaque) {
    auto &t = *static_cast<Transfer *>(opaque);
    if (size && nmemb > SIZE_MAX / size)
        return 0;
    const size_t count = size * nmemb;
    if (count > t.max_bytes || t.bytes > t.max_bytes - count) {
        t.too_large = true;
        t.error = "Download exceeds configured size limit";
        return 0;
    }
    if (t.fd >= 0) {
        size_t written = 0;
        while (written < count) {
            const ssize_t n = write(t.fd, ptr + written, count - written);
            if (n < 0 && errno == EINTR)
                continue;
            if (n <= 0) {
                t.error = "Cannot write download temporary file";
                return 0;
            }
            written += static_cast<size_t>(n);
        }
    }
    if (t.digest) {
        try {
            t.digest->update(ptr, count);
        } catch (const std::exception &e) {
            t.error = e.what();
            return 0;
        }
    }
    if (t.fd < 0) {
        try {
            t.text.append(ptr, count);
        } catch (...) {
            t.error = "Cannot allocate metadata response";
            return 0;
        }
    }
    t.bytes += count;
    return count;
}

int transfer_progress(void *opaque, curl_off_t total, curl_off_t now, curl_off_t, curl_off_t) {
    auto &t = *static_cast<Transfer *>(opaque);
    t.total = total > 0 ? static_cast<uint64_t>(total) : 0;
    bool cancel = false;
    try {
        cancel = (t.callbacks.cancelled && t.callbacks.cancelled()) ||
                 (t.callbacks.progress &&
                  !t.callbacks.progress({static_cast<uint64_t>(std::max<curl_off_t>(0, now)), t.total,
                                         "Downloading metadata or artifact"}));
    } catch (...) {
        cancel = true;
        t.error = "Download callback failed";
    }
    if (cancel) {
        if (t.error.empty())
            t.error = "Download cancelled";
        return 1;
    }
    return 0;
}

CURLcode perform(const std::string &url, bool allow_http, const std::string &ca_bundle, Transfer &transfer,
                 long &status) {
    // Keep a worker-thread-local connection cache so large asset batches reuse
    // TLS sessions, DNS, and keep-alive connections across requests.
    CURL *curl = get_thread_curl();
    if (!curl)
        throw std::runtime_error("Cannot create HTTPS request");
    curl_easy_reset(curl);
    auto setopt = [curl](CURLoption option, auto value) {
        if (curl_easy_setopt(curl, option, value) != CURLE_OK)
            throw std::runtime_error("Cannot configure verified HTTPS request");
    };
    setopt(CURLOPT_URL, url.c_str());
    setopt(CURLOPT_FOLLOWLOCATION, 1L);
    setopt(CURLOPT_MAXREDIRS, 5L);
#if LIBCURL_VERSION_NUM >= 0x075500
    setopt(CURLOPT_PROTOCOLS_STR, allow_http ? "https,http" : "https");
    setopt(CURLOPT_REDIR_PROTOCOLS_STR, allow_http ? "https,http" : "https");
#else
    setopt(CURLOPT_PROTOCOLS, allow_http ? (CURLPROTO_HTTPS | CURLPROTO_HTTP) : CURLPROTO_HTTPS);
    setopt(CURLOPT_REDIR_PROTOCOLS, allow_http ? (CURLPROTO_HTTPS | CURLPROTO_HTTP) : CURLPROTO_HTTPS);
#endif
    setopt(CURLOPT_SSL_VERIFYPEER, 1L);
    setopt(CURLOPT_SSL_VERIFYHOST, 2L);
    setopt(CURLOPT_NOSIGNAL, 1L);
    setopt(CURLOPT_CONNECTTIMEOUT, 20L);
    setopt(CURLOPT_TIMEOUT, 600L);
    setopt(CURLOPT_USERAGENT, "Switchcraft/0.1 Prism metadata client");
    setopt(CURLOPT_WRITEFUNCTION, receive_data);
    setopt(CURLOPT_WRITEDATA, &transfer);
    setopt(CURLOPT_XFERINFOFUNCTION, transfer_progress);
    setopt(CURLOPT_XFERINFODATA, &transfer);
    setopt(CURLOPT_NOPROGRESS, 0L);
    if (!ca_bundle.empty())
        setopt(CURLOPT_CAINFO, ca_bundle.c_str());
    const CURLcode result = curl_easy_perform(curl);
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);
    return result;
}

std::string expected_lower(const std::string &hash, const std::string &algorithm) {
    if (algorithm != "sha1" && algorithm != "sha256")
        throw std::runtime_error("Unsupported digest algorithm");
    const size_t expected = algorithm == "sha1" ? 40 : 64;
    if (hash.size() != expected ||
        !std::all_of(hash.begin(), hash.end(), [](unsigned char c) { return std::isxdigit(c); }))
        throw std::runtime_error("Invalid expected digest");
    return lower(hash);
}

void sync_parent(const std::string &target) {
    std::string parent = ".";
    const auto slash = target.find_last_of('/');
    if (slash != std::string::npos)
        parent = slash == 0 ? "/" : target.substr(0, slash);
    int fd = open(parent.c_str(), O_RDONLY);
    if (fd >= 0) {
        (void)fsync(fd);
        close(fd);
    }
}

std::string owner_contents(const std::string &algorithm, const std::string &hash, uint64_t size) {
    return "switchcraft-part-v1\n" + algorithm + "\n" + hash + "\n" + std::to_string(size) + "\n";
}

bool exists_no_follow(const std::string &path) {
    struct stat st{};
    if (lstat(path.c_str(), &st) == 0)
        return true;
    if (errno == ENOENT)
        return false;
    throw std::runtime_error("Cannot inspect partial download state");
}

bool matching_owner(const std::string &path, const std::string &expected) {
    struct stat st{};
    if (lstat(path.c_str(), &st) != 0) {
        if (errno == ENOENT)
            return false;
        throw std::runtime_error("Cannot inspect partial download journal");
    }
    if (!S_ISREG(st.st_mode) || S_ISLNK(st.st_mode) || st.st_size < 0 || st.st_size > 256)
        throw std::runtime_error("Refusing unsafe partial download journal");
    std::ifstream in(path, std::ios::binary);
    if (!in)
        throw std::runtime_error("Cannot read partial download journal");
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    if (in.bad())
        throw std::runtime_error("Cannot read partial download journal");
    if (content != expected)
        throw std::runtime_error("Partial download journal does not match this artifact");
    return true;
}

void create_owner(const std::string &path, const std::string &data) {
    const int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0)
        throw std::runtime_error("Partial download journal already exists");
    size_t written = 0;
    while (written < data.size()) {
        const ssize_t n = write(fd, data.data() + written, data.size() - written);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0) {
            close(fd);
            std::remove(path.c_str());
            throw std::runtime_error("Cannot write partial download journal");
        }
        written += static_cast<size_t>(n);
    }
    const bool sync_ok = fsync(fd) == 0;
    const bool close_ok = close(fd) == 0;
    if (!sync_ok || !close_ok) {
        std::remove(path.c_str());
        throw std::runtime_error("Cannot flush partial download journal");
    }
}
} // namespace

std::string fetch_text(const std::string &url, uint64_t max_bytes, const DownloadCallbacks &callbacks,
                       const std::string &ca_bundle, bool allow_http_for_tests) {
    validate_url(url, allow_http_for_tests);
    if (!max_bytes || max_bytes > static_cast<uint64_t>(SIZE_MAX))
        throw std::runtime_error("Invalid response size limit");
    Transfer transfer;
    transfer.max_bytes = max_bytes;
    transfer.callbacks = callbacks;
    long status = 0;
    const CURLcode result = perform(url, allow_http_for_tests, ca_bundle, transfer, status);
    if (!transfer.error.empty())
        throw std::runtime_error(transfer.error);
    if (result != CURLE_OK)
        throw std::runtime_error(std::string("HTTPS request failed: ") + curl_easy_strerror(result));
    if (status < 200 || status >= 300)
        throw std::runtime_error("Metadata server returned HTTP " + std::to_string(status));
    return transfer.text;
}

DownloadStats download_verified(const DownloadRequest &r, const DownloadCallbacks &callbacks) {
    validate_url(r.url, r.allow_http_for_tests);
    validate_target(r.target);
    const std::string algorithm = lower(r.algorithm);
    const std::string expected = expected_lower(r.expected_hash, algorithm);
    if (!r.max_bytes || (r.expected_size && r.expected_size > r.max_bytes))
        throw std::runtime_error("Invalid download size limit");
    if (r.retries > 5)
        throw std::runtime_error("Retry count exceeds configured safety limit");

    const std::string part = r.target + ".part";
    const std::string owner = part + ".owner";
    const std::string journal = owner_contents(algorithm, expected, r.expected_size);
    const bool has_part = exists_no_follow(part);
    const bool has_owner = exists_no_follow(owner);
    if (has_owner)
        matching_owner(owner, journal); // Reject symlink, malformed, or foreign ownership.
    else if (has_part)
        throw std::runtime_error("Refusing unowned partial download");

    struct stat existing{};
    if (lstat(r.target.c_str(), &existing) == 0) {
        if (!S_ISREG(existing.st_mode) || S_ISLNK(existing.st_mode))
            throw std::runtime_error("Refusing unexpected destination file");
        uint64_t old_size = 0;
        const std::string old_hash = hash_file(r.target, algorithm, old_size);
        if (old_hash == expected && (!r.expected_size || old_size == r.expected_size))
            return {old_size, algorithm == "sha256" ? old_hash : hash_file(r.target, "sha256", old_size), 0,
                    true};
        if (!r.repair_corrupt)
            throw std::runtime_error("Existing destination failed integrity check; refusing replacement");
    } else if (errno != ENOENT)
        throw std::runtime_error("Cannot inspect download destination");

    bool owns_journal = false;
    if (has_owner) {
        matching_owner(owner, journal); // Reject symlink, malformed, or foreign ownership.
        owns_journal = true;
        if (has_part) {
            if (!r.repair_corrupt)
                throw std::runtime_error("Owned partial download requires explicit clean-restart repair");
            if (std::remove(part.c_str()) != 0)
                throw std::runtime_error("Cannot clean owned partial download");
        }
    } else {
        if (has_part)
            throw std::runtime_error("Refusing unowned partial download");
        create_owner(owner, journal);
        owns_journal = true;
    }
    std::string last_error;
    for (unsigned attempt = 1; attempt <= r.retries + 1; ++attempt) {
        std::unique_ptr<Digest> digest;
        try {
            digest = std::make_unique<Digest>(algorithm);
        } catch (...) {
            if (owns_journal)
                std::remove(owner.c_str());
            throw;
        }
        const int part_fd = open(part.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0644);
        if (part_fd < 0) {
            if (owns_journal)
                std::remove(owner.c_str());
            throw std::runtime_error("Cannot create exclusive download temporary file");
        }
        Transfer transfer;
        transfer.fd = part_fd;
        transfer.digest = digest.get();
        transfer.max_bytes = r.max_bytes;
        transfer.callbacks = callbacks;
        long status = 0;
        CURLcode result = CURLE_FAILED_INIT;
        try {
            result = perform(r.url, r.allow_http_for_tests, r.ca_bundle, transfer, status);
        } catch (...) {
            close(part_fd);
            std::remove(part.c_str());
            if (owns_journal)
                std::remove(owner.c_str());
            throw;
        }
        const bool flush_ok = fsync(part_fd) == 0;
        const bool close_ok = close(part_fd) == 0;
        if (!flush_ok || !close_ok)
            transfer.error = "Cannot flush download temporary file";
        std::string actual;
        if (transfer.error.empty() && result == CURLE_OK && status >= 200 && status < 300) {
            try {
                actual = digest->finish();
            } catch (const std::exception &e) {
                transfer.error = e.what();
            }
            if (transfer.error.empty() && r.expected_size && transfer.bytes != r.expected_size)
                transfer.error = "Downloaded size does not match metadata";
            if (transfer.error.empty() && actual != expected)
                transfer.error = "Downloaded digest does not match metadata";
        } else if (transfer.error.empty()) {
            transfer.error = result != CURLE_OK
                                 ? std::string("HTTPS transfer failed: ") + curl_easy_strerror(result)
                                 : "Metadata server returned HTTP " + std::to_string(status);
        }
        if (transfer.error.empty()) {
            if (r.repair_corrupt && lstat(r.target.c_str(), &existing) == 0) {
                const std::string backup = r.target + ".corrupt";
                if (lstat(backup.c_str(), &existing) == 0 || errno != ENOENT) {
                    std::remove(part.c_str());
                    if (owns_journal)
                        std::remove(owner.c_str());
                    throw std::runtime_error("Repair backup path already exists");
                }
                if (std::rename(r.target.c_str(), backup.c_str()) != 0) {
                    std::remove(part.c_str());
                    if (owns_journal)
                        std::remove(owner.c_str());
                    throw std::runtime_error("Cannot preserve corrupt destination for repair");
                }
                if (std::rename(part.c_str(), r.target.c_str()) != 0) {
                    (void)std::rename(backup.c_str(), r.target.c_str());
                    std::remove(part.c_str());
                    if (owns_journal)
                        std::remove(owner.c_str());
                    throw std::runtime_error("Cannot publish verified replacement");
                }
                std::remove(backup.c_str());
            } else if (std::rename(part.c_str(), r.target.c_str()) != 0) {
                std::remove(part.c_str());
                if (owns_journal)
                    std::remove(owner.c_str());
                throw std::runtime_error("Cannot publish verified download");
            }
            if (owns_journal)
                std::remove(owner.c_str());
            sync_parent(r.target);
            uint64_t verified_size = transfer.bytes;
            const auto sha256 = algorithm == "sha256" ? actual : hash_file(r.target, "sha256", verified_size);
            return {transfer.bytes, sha256, attempt, false};
        }
        last_error = transfer.error;
        std::remove(part.c_str());
        if (last_error == "Download cancelled") {
            if (owns_journal)
                std::remove(owner.c_str());
            throw std::runtime_error(last_error);
        }
        if (attempt <= r.retries && callbacks.progress) {
            try {
                if (!callbacks.progress({0, 0, "Retrying download from the beginning"}))
                    throw std::runtime_error("Download cancelled");
            } catch (const std::runtime_error &e) {
                if (std::string(e.what()) == "Download cancelled") {
                    if (owns_journal)
                        std::remove(owner.c_str());
                    throw;
                }
                if (owns_journal)
                    std::remove(owner.c_str());
                throw std::runtime_error("Download callback failed");
            } catch (...) {
                if (owns_journal)
                    std::remove(owner.c_str());
                throw std::runtime_error("Download callback failed");
            }
        }
    }
    if (owns_journal)
        std::remove(owner.c_str());
    throw std::runtime_error(last_error.empty() ? "Download failed" : last_error);
}

bool verify_file(const std::string &path, const std::string &algorithm, const std::string &expected_hash,
                 uint64_t expected_size) {
    const std::string normalized = lower(algorithm);
    const std::string expected = expected_lower(expected_hash, normalized);
    struct stat st{};
    if (lstat(path.c_str(), &st) != 0 || !S_ISREG(st.st_mode) || S_ISLNK(st.st_mode))
        return false;
    uint64_t size = 0;
    const std::string actual = hash_file(path, normalized, size);
    return actual == expected && (!expected_size || size == expected_size);
}

void shutdown_download_transport() {
    auto &registry = curl_registry();
    std::lock_guard<std::mutex> lock(registry.mutex);
    for (CURL **handle : registry.handles) {
        if (handle && *handle) {
            curl_easy_cleanup(*handle);
            *handle = nullptr;
        }
    }
    registry.handles.clear();
    if (registry.initialized) {
        curl_global_cleanup();
        registry.initialized = false;
    }
}
} // namespace sc
