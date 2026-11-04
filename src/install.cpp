// SPDX-License-Identifier: GPL-3.0-only
#include "install.hpp"
#include "prism_metadata.hpp"
#include <algorithm>
#include <atomic>
#include <cctype>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <unistd.h>

namespace sc {
namespace {
struct Cancelled final : std::runtime_error {
    Cancelled() : std::runtime_error("Installation cancelled") {}
};
struct Artifact {
    std::string path, url, algorithm, hash;
    uint64_t size = 0, max_bytes = 0;
    std::string kind;
};
std::string lower(std::string s) {
    for (auto &c : s)
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}
bool hex_hash(const std::string &s, size_t n) {
    return s.size() == n && std::all_of(s.begin(), s.end(), [](unsigned char c) { return std::isxdigit(c); });
}
void ensure_safe_id(const std::string &s) {
    if (!safe_id(s))
        throw std::runtime_error("Unsafe Minecraft version identifier");
}
void check_cancel(const DownloadCallbacks &cb) {
    if (cb.cancelled && cb.cancelled())
        throw Cancelled();
}
std::string path_maven(const std::string &name) {
    std::vector<std::string> p;
    size_t at = 0;
    while (true) {
        auto end = name.find(':', at);
        p.push_back(name.substr(at, end == name.npos ? end : end - at));
        if (end == name.npos)
            break;
        at = end + 1;
    }
    if (p.size() < 3 || p.size() > 5 || p[0].empty() || p[1].empty() || p[2].empty())
        throw std::runtime_error("Invalid Maven coordinate: " + name);
    std::string group = p[0];
    std::replace(group.begin(), group.end(), '.', '/');
    std::string file = p[1] + "-" + p[2];
    if (p.size() >= 4 && !p[3].empty())
        file += "-" + p[3];
    return group + "/" + p[1] + "/" + p[2] + "/" + file + ".jar";
}
bool safe_relative(const std::string &p) {
    if (p.empty() || p.front() == '/' || p.find('\\') != p.npos || p.find(':') != p.npos)
        return false;
    size_t at = 0;
    while (at <= p.size()) {
        auto e = p.find('/', at);
        auto part = p.substr(at, e == p.npos ? e : e - at);
        if (part.empty() || part == "." || part == "..")
            return false;
        if (e == p.npos)
            break;
        at = e + 1;
    }
    return true;
}
void mkdirs(const std::string &path) {
    std::string cur;
    size_t i = 0;
    if (path.rfind("sdmc:/", 0) == 0) {
        cur = "sdmc:/";
        i = 6;
    } else if (!path.empty() && path[0] == '/') {
        cur = "/";
        i = 1;
    }
    for (; i < path.size();) {
        auto e = path.find('/', i);
        auto part = path.substr(i, e == path.npos ? e : e - i);
        if (!part.empty()) {
            if (!cur.empty() && cur.back() != '/')
                cur += '/';
            cur += part;
            if (::mkdir(cur.c_str(), 0755) != 0 && errno != EEXIST)
                throw std::runtime_error("Cannot create managed directory: " + cur);
            struct stat st{};
            if (::lstat(cur.c_str(), &st) != 0 || !S_ISDIR(st.st_mode))
                throw std::runtime_error("Managed path is not a real directory: " + cur);
        }
        if (e == path.npos)
            break;
        i = e + 1;
    }
}
std::string parent(const std::string &p) {
    auto i = p.rfind('/');
    return i == p.npos ? "." : p.substr(0, i);
}
void atomic_text(const std::string &path, const std::string &data) {
    const std::string dir = parent(path);
    mkdirs(dir);
    struct stat target{};
    int target_rc = ::lstat(path.c_str(), &target);
    if (target_rc == 0 && !S_ISREG(target.st_mode))
        throw std::runtime_error("Refusing non-regular managed metadata target: " + path);
    if (target_rc != 0 && errno != ENOENT)
        throw std::runtime_error("Cannot inspect managed metadata target: " + path);
    static std::atomic<unsigned long> sequence{0};
    std::string owned_temp;
    int fd = -1;
    for (unsigned attempt = 0; attempt < 128 && fd < 0; ++attempt) {
        owned_temp = path + ".tmp." + std::to_string(static_cast<unsigned long>(::getpid())) + "." +
                     std::to_string(sequence.fetch_add(1));
        fd = ::open(owned_temp.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (fd < 0 && errno != EEXIST)
            throw std::runtime_error("Cannot exclusively stage managed metadata");
    }
    if (fd < 0)
        throw std::runtime_error("Cannot find unique managed metadata staging name");
    bool published = false;
    auto cleanup = [&]() {
        if (fd >= 0) {
            ::close(fd);
            fd = -1;
        }
        if (!published)
            ::unlink(owned_temp.c_str());
    };
    try {
        size_t offset = 0;
        while (offset < data.size()) {
            ssize_t n = ::write(fd, data.data() + offset, data.size() - offset);
            if (n < 0 && errno == EINTR)
                continue;
            if (n <= 0)
                throw std::runtime_error("Cannot write managed metadata stage");
            offset += static_cast<size_t>(n);
        }
        if (::fsync(fd) != 0)
            throw std::runtime_error("Cannot sync managed metadata stage");
        if (::close(fd) != 0) {
            fd = -1;
            throw std::runtime_error("Cannot close managed metadata stage");
        }
        fd = -1;
        target_rc = ::lstat(path.c_str(), &target);
        if (target_rc == 0 && !S_ISREG(target.st_mode))
            throw std::runtime_error("Refusing non-regular managed metadata target: " + path);
        if (target_rc != 0 && errno != ENOENT)
            throw std::runtime_error("Cannot inspect managed metadata target: " + path);
        if (::rename(owned_temp.c_str(), path.c_str()) != 0)
            throw std::runtime_error("Cannot publish managed metadata");
        published = true;
    } catch (...) {
        cleanup();
        throw;
    }
}
Json parse_json_text(const std::string &s, const char *what) {
    if (s.size() > 16 * 1024 * 1024)
        throw std::runtime_error(std::string(what) + " size limit");
    Json j = Json::parse(s);
    if (!j.is_object())
        throw std::runtime_error(std::string(what) + " must be object");
    return j;
}
Json read_json_limited(const std::string &path, uint64_t limit) {
    std::ifstream in(path, std::ios::binary | std::ios::ate);
    if (!in)
        throw std::runtime_error("Cannot read managed JSON: " + path);
    auto size = in.tellg();
    if (size < 0 || static_cast<uint64_t>(size) > limit)
        throw std::runtime_error("Managed JSON size limit: " + path);
    in.seekg(0);
    Json j;
    in >> j;
    if (!j.is_object())
        throw std::runtime_error("Managed JSON must be object: " + path);
    return j;
}
std::string trim_slash(std::string s) {
    while (!s.empty() && s.back() == '/')
        s.pop_back();
    return s;
}
void check_options(const InstallOptions &o) {
    const auto base = trim_slash(o.prism_base_url);
    if (base != kPrismMetadataBase && !o.allow_test_mirror)
        throw std::runtime_error("Custom Prism metadata mirror is restricted to explicit tests");
    bool https = base.rfind("https://", 0) == 0, bool_http = base.rfind("http://", 0) == 0;
    if (!https && !(bool_http && o.allow_test_mirror && o.allow_http_for_tests))
        throw std::runtime_error("Prism endpoint must use HTTPS");
    if (base.find('@') != std::string::npos || base.find('\n') != std::string::npos)
        throw std::runtime_error("Invalid Prism endpoint");
    const auto asset = trim_slash(o.asset_base_url);
    bool asset_https = asset.rfind("https://", 0) == 0, asset_http = asset.rfind("http://", 0) == 0;
    if (!asset_https && !(asset_http && o.allow_test_mirror && o.allow_http_for_tests))
        throw std::runtime_error("Asset endpoint must use HTTPS");
    if (asset != "https://resources.download.minecraft.net" && !o.allow_test_mirror)
        throw std::runtime_error("Custom asset mirror is restricted to explicit tests");
}
std::string endpoint(const InstallOptions &o, const std::string &uid, const std::string &file) {
    return trim_slash(o.prism_base_url) + "/" + uid + "/" + file;
}
DownloadRequest request(const InstallOptions &o, const std::string &url, const std::string &target,
                        const std::string &alg, const std::string &hash, uint64_t size, uint64_t max) {
    DownloadRequest r;
    r.url = url;
    r.target = target;
    r.algorithm = alg;
    r.expected_hash = lower(hash);
    r.expected_size = size;
    r.max_bytes = max;
    r.retries = 2;
    r.repair_corrupt = o.repair_corrupt_managed_cache;
    r.allow_http_for_tests = o.allow_http_for_tests && o.allow_test_mirror;
    r.ca_bundle = o.ca_bundle;
    return r;
}
Json read_index(const std::string &root, const std::string &uid) {
    return read_json(root + "/meta/" + uid + "/index.json");
}
const Json &find_version(const Json &index, const std::string &version, const std::string &uid) {
    if (index.value("formatVersion", 0) != 1 || index.value("uid", std::string{}) != uid ||
        !index.contains("versions") || !index["versions"].is_array())
        throw std::runtime_error("Invalid Prism component index: " + uid);
    for (const auto &v : index["versions"])
        if (v.is_object() && v.value("version", std::string{}) == version)
            return v;
    throw std::runtime_error("Version is absent from Prism catalog: " + uid + " " + version);
}
Json fetch_index(const std::string &root, const std::string &uid, const InstallOptions &o,
                 const DownloadCallbacks &cb) {
    check_cancel(cb);
    auto body = fetch_text(endpoint(o, uid, "index.json"), 16 * 1024 * 1024, cb, o.ca_bundle,
                           o.allow_http_for_tests && o.allow_test_mirror);
    Json j = parse_json_text(body, "Prism index");
    if (j.value("uid", std::string{}) != uid || j.value("formatVersion", 0) != 1)
        throw std::runtime_error("Prism returned wrong index identity/format for " + uid);
    if (!j.contains("versions") || !j["versions"].is_array() || j["versions"].size() > 100000)
        throw std::runtime_error("Invalid Prism versions list");
    atomic_text(root + "/meta/" + uid + "/index.json", body);
    return j;
}
Json ensure_metadata(const std::string &root, const std::string &uid, const std::string &version,
                     const Json &entry, const InstallOptions &o, const DownloadCallbacks &cb) {
    ensure_safe_id(version);
    if (!entry.contains("sha256") || !entry["sha256"].is_string() ||
        !hex_hash(entry["sha256"].get<std::string>(), 64))
        throw std::runtime_error("Prism index lacks valid SHA-256 for " + uid + " " + version);
    std::string target = root + "/meta/" + uid + "/" + version + ".json";
    auto req = request(o, endpoint(o, uid, version + ".json"), target, "sha256",
                       entry["sha256"].get<std::string>(), 0, 8 * 1024 * 1024);
    download_verified(req, cb);
    Json j = read_json(target);
    if (j.value("uid", std::string{}) != uid || j.value("version", std::string{}) != version)
        throw std::runtime_error("Prism cached metadata identity mismatch");
    return j;
}
void add_artifact(std::map<std::string, Artifact> &queue, Artifact a) {
    if (!safe_relative(a.path))
        throw std::runtime_error("Unsafe install path: " + a.path);
    if (a.algorithm == "sha1" ? !hex_hash(a.hash, 40) : !hex_hash(a.hash, 64))
        throw std::runtime_error("Missing/invalid artifact digest: " + a.path);
    if (!a.size || a.size > a.max_bytes)
        throw std::runtime_error("Invalid artifact size: " + a.path);
    a.hash = lower(a.hash);
    auto it = queue.find(a.path);
    if (it != queue.end()) {
        if (it->second.hash != a.hash || it->second.size != a.size)
            throw std::runtime_error("Conflicting artifact metadata for " + a.path);
        return;
    }
    queue.emplace(a.path, std::move(a));
}
bool horizon_rule_allowed(const Json &lib) {
    if (!lib.contains("rules"))
        return true;
    if (!lib["rules"].is_array())
        throw std::runtime_error("Library rules must be array");
    bool allowed = false;
    for (const auto &r : lib["rules"]) {
        if (!r.is_object())
            throw std::runtime_error("Library rule must be object");
        std::string action = r.value("action", "");
        if (action != "allow" && action != "disallow")
            throw std::runtime_error("Unsupported library rule action");
        bool match = true;
        if (r.contains("features") && !r["features"].empty())
            throw std::runtime_error("Unsupported feature-conditioned library rule");
        if (r.contains("os")) {
            if (!r["os"].is_object())
                throw std::runtime_error("Library OS rule must be object");
            auto os = r["os"];
            if (os.contains("name")) {
                if (!os["name"].is_string())
                    throw std::runtime_error("Library OS name must be string");
                match = os["name"] == "horizon";
            }
            if (os.contains("arch") || os.contains("version"))
                match = false;
        }
        if (match)
            allowed = action == "allow";
    }
    return allowed;
}
std::string library_path(const Json &lib) {
    if (lib.contains("downloads") && lib["downloads"].is_object() && lib["downloads"].contains("artifact") &&
        lib["downloads"]["artifact"].is_object() && lib["downloads"]["artifact"].contains("path"))
        return lib["downloads"]["artifact"]["path"].get<std::string>();
    return path_maven(lib.at("name").get<std::string>());
}
std::string library_url(const Json &lib, const std::string &path) {
    if (lib.contains("downloads") && lib["downloads"].is_object() && lib["downloads"].contains("artifact")) {
        const auto &a = lib["downloads"]["artifact"];
        if (a.is_object() && a.contains("url") && a["url"].is_string())
            return a["url"].get<std::string>();
    }
    return "https://libraries.minecraft.net/" + path;
}
Json verified_metadata(const std::string &root, const std::string &uid, const std::string &version) {
    ensure_safe_id(version);
    Json index = read_index(root, uid);
    const Json &entry = find_version(index, version, uid);
    if (!entry.contains("sha256") || !entry["sha256"].is_string() ||
        !hex_hash(entry["sha256"].get<std::string>(), 64))
        throw std::runtime_error("Invalid cached metadata SHA-256");
    std::string p = root + "/meta/" + uid + "/" + version + ".json";
    if (!verify_file(p, "sha256", entry["sha256"].get<std::string>()))
        throw std::runtime_error("Cached Prism metadata failed SHA-256 verification: " + uid + " " + version);
    Json m = read_json(p);
    if (m.value("uid", std::string{}) != uid || m.value("version", std::string{}) != version)
        throw std::runtime_error("Cached Prism metadata identity mismatch");
    return m;
}
std::map<std::string, Artifact> build_artifacts(const std::string &root, const std::string &version,
                                                Json &asset_meta, const std::string &asset_base) {
    Json comps = prism_components_for_version(root, version);
    std::map<std::string, Json> metadata;
    for (const auto &c : comps) {
        std::string uid = c.at("uid").get<std::string>(), v = c.at("version").get<std::string>();
        metadata[uid] = verified_metadata(root, uid, v);
    }
    Json mc = metadata.at("net.minecraft");
    std::map<std::string, Artifact> queue;
    const auto &main = mc.at("mainJar");
    const auto &ma = main.at("downloads").at("artifact");
    Artifact client;
    client.path = "libraries/" + path_maven(main.at("name").get<std::string>());
    client.url = ma.at("url").get<std::string>();
    client.algorithm = "sha1";
    client.hash = ma.at("sha1").get<std::string>();
    client.size = ma.at("size").get<uint64_t>();
    client.max_bytes = 128ULL * 1024 * 1024;
    client.kind = "client";
    add_artifact(queue, client);
    for (const auto &pair : metadata) {
        const Json &m = pair.second;
        if (!m.contains("libraries") || !m["libraries"].is_array())
            continue;
        for (const auto &lib : m["libraries"]) {
            if (!horizon_rule_allowed(lib))
                continue;
            std::string name = lib.at("name").get<std::string>();
            if (name.find(":natives-") != name.npos || lib.contains("natives"))
                continue;
            if (!lib.contains("downloads") || !lib["downloads"].contains("artifact"))
                throw std::runtime_error("Missing Prism library artifact metadata: " + name);
            std::string path = library_path(lib);
            const auto &a = lib.at("downloads").at("artifact");
            Artifact art;
            art.path = "libraries/" + path;
            art.url = library_url(lib, path);
            art.algorithm = "sha1";
            art.hash = a.at("sha1").get<std::string>();
            art.size = a.at("size").get<uint64_t>();
            art.max_bytes = 256ULL * 1024 * 1024;
            art.kind = "library";
            add_artifact(queue, std::move(art));
        }
    }
    const auto &asset = mc.at("assetIndex");
    const std::string aid = asset.at("id").get<std::string>();
    ensure_safe_id(aid);
    Artifact ai;
    ai.path = "assets/indexes/" + aid + ".json";
    ai.url = asset.at("url").get<std::string>();
    ai.algorithm = "sha1";
    ai.hash = asset.at("sha1").get<std::string>();
    ai.size = asset.at("size").get<uint64_t>();
    ai.max_bytes = 64ULL * 1024 * 1024;
    ai.kind = "asset_index";
    if (!safe_relative(ai.path) || !hex_hash(ai.hash, 40) || !ai.size || ai.size > ai.max_bytes)
        throw std::runtime_error("Invalid asset index metadata");
    asset_meta = {{"artifact", ai.path},
                  {"url", ai.url},
                  {"sha1", lower(ai.hash)},
                  {"size", ai.size},
                  {"max_bytes", ai.max_bytes}};
    Json objects = read_json_limited(root + "/" + ai.path, 64ULL * 1024 * 1024);
    if (!objects.contains("objects") || !objects["objects"].is_object())
        throw std::runtime_error("Asset index has no objects map");
    for (auto it = objects["objects"].begin(); it != objects["objects"].end(); ++it) {
        if (!it.value().is_object())
            throw std::runtime_error("Invalid asset object record");
        std::string hash = it.value().at("hash").get<std::string>();
        uint64_t size = it.value().at("size").get<uint64_t>();
        if (!hex_hash(hash, 40) || !size || size > 64ULL * 1024 * 1024)
            throw std::runtime_error("Invalid asset object hash/size");
        std::string h = lower(hash);
        Artifact a;
        a.path = "assets/objects/" + h.substr(0, 2) + "/" + h;
        a.url = trim_slash(asset_base) + "/" + h.substr(0, 2) + "/" + h;
        a.algorithm = "sha1";
        a.hash = h;
        a.size = size;
        a.max_bytes = 64ULL * 1024 * 1024;
        a.kind = "asset";
        add_artifact(queue, std::move(a));
    }
    add_artifact(queue, ai);
    return queue;
}
void check_disk(const std::string &root, uint64_t bytes, uint64_t limit) {
    if (bytes > limit)
        throw std::runtime_error("Install exceeds configured download budget");
    if (bytes == 0)
        return;
    std::string p = root;
    struct statvfs st{};
    while (::statvfs(p.c_str(), &st) != 0) {
        auto i = p.rfind('/');
        if (i == p.npos)
            throw std::runtime_error("Cannot check free space");
        p = p.substr(0, i);
        if (p.empty())
            p = "/";
    }
    uint64_t free = static_cast<uint64_t>(st.f_bavail) * static_cast<uint64_t>(st.f_frsize);
    if (free < bytes + 32ULL * 1024 * 1024)
        throw std::runtime_error("Insufficient free space for verified install");
}
InstallReport report_error(const std::exception &e) {
    InstallReport r;
    r.status = "failed";
    r.details = {{"error", e.what()}};
    return r;
}
} // namespace
Json InstallReport::to_json() const {
    return Json{{"ok", ok}, {"cancelled", cancelled}, {"status", status}, {"details", details}};
}

InstallReport refresh_catalog(const std::string &root, const std::string &version, const InstallOptions &o,
                              const DownloadCallbacks &cb) {
    InstallReport report;
    report.details = Json::object();
    try {
        check_options(o);
        ensure_safe_id(version);
        const std::string mc_uid = "net.minecraft";
        Json mc_index = fetch_index(root, mc_uid, o, cb);
        const Json &mc_entry = find_version(mc_index, version, mc_uid);
        Json mc = ensure_metadata(root, mc_uid, version, mc_entry, o, cb);
        report.details["version"] = version;
        report.details["minecraft_metadata_sha256"] = lower(mc_entry.at("sha256").get<std::string>());
        Json dependencies = Json::array();
        if (mc.contains("requires")) {
            if (!mc["requires"].is_array())
                throw std::runtime_error("Minecraft metadata requires must be array");
            for (const auto &req : mc["requires"]) {
                std::string uid = req.at("uid").get<std::string>();
                if (uid != "org.lwjgl3")
                    throw std::runtime_error("Unsupported Prism dependency UID: " + uid);
                std::string dep = req.value("equals", std::string{});
                if (dep.empty())
                    dep = req.value("suggests", std::string{});
                if (dep.empty())
                    throw std::runtime_error("Prism dependency lacks exact/suggested version");
                ensure_safe_id(dep);
                Json idx = fetch_index(root, uid, o, cb);
                const Json &e = find_version(idx, dep, uid);
                ensure_metadata(root, uid, dep, e, o, cb);
                dependencies.push_back(
                    {{"uid", uid}, {"version", dep}, {"sha256", lower(e.at("sha256").get<std::string>())}});
            }
        }
        report.ok = true;
        report.status = "metadata_verified";
        report.details["dependencies"] = dependencies;
        report.details["catalog_version_count"] = mc_index["versions"].size();
    } catch (const Cancelled &e) {
        report.cancelled = true;
        report.status = "cancelled";
        report.details["error"] = e.what();
    } catch (const std::exception &e) {
        report = report_error(e);
    }
    return report;
}

InstallReport prepare_install(const std::string &root, const std::string &version, const InstallOptions &o,
                              const DownloadCallbacks &cb) {
    InstallReport report;
    try {
        auto refreshed = refresh_catalog(root, version, o, cb);
        if (!refreshed.ok)
            return refreshed;
        Json comps = prism_components_for_version(root, version);
        auto mc_comp = std::find_if(comps.begin(), comps.end(), [](const Json &c) {
            return c.value("uid", std::string{}) == "net.minecraft";
        });
        if (mc_comp == comps.end())
            throw std::runtime_error("Prism vanilla component missing");
        Json mc = verified_metadata(root, "net.minecraft", version);
        const auto &asset = mc.at("assetIndex");
        std::string aid = asset.at("id").get<std::string>();
        ensure_safe_id(aid);
        std::string ai_path = "assets/indexes/" + aid + ".json";
        if (!safe_relative(ai_path))
            throw std::runtime_error("Unsafe asset index path");
        Artifact ai;
        ai.path = ai_path;
        ai.url = asset.at("url").get<std::string>();
        ai.algorithm = "sha1";
        ai.hash = asset.at("sha1").get<std::string>();
        ai.size = asset.at("size").get<uint64_t>();
        ai.max_bytes = 64ULL * 1024 * 1024;
        ai.kind = "asset_index";
        if (!hex_hash(ai.hash, 40) || !ai.size || ai.size > ai.max_bytes)
            throw std::runtime_error("Invalid asset index metadata");
        check_disk(root, verify_file(root + "/" + ai.path, ai.algorithm, ai.hash, ai.size) ? 0 : ai.size,
                   o.max_install_bytes);
        mkdirs(parent(root + "/" + ai.path));
        DownloadCallbacks index_cb = cb;
        if (cb.progress)
            index_cb.progress = [orig = cb.progress](const DownloadProgress &p) {
                DownloadProgress x = p;
                x.message = "Asset index";
                return orig(x);
            };
        auto ai_stats = download_verified(
            request(o, ai.url, root + "/" + ai.path, ai.algorithm, ai.hash, ai.size, ai.max_bytes), index_cb);
        Json asset_meta;
        auto queue = build_artifacts(root, version, asset_meta, o.asset_base_url);
        uint64_t total = 0, needed = 0, asset_bytes = 0;
        for (const auto &p : queue) {
            if (UINT64_MAX - total < p.second.size)
                throw std::runtime_error("Install size overflow");
            total += p.second.size;
            if (p.second.kind == "asset")
                asset_bytes += p.second.size;
            if (!verify_file(root + "/" + p.second.path, p.second.algorithm, p.second.hash, p.second.size))
                needed += p.second.size;
        }
        if (total > o.max_install_bytes)
            throw std::runtime_error("Install exceeds configured download budget");
        check_disk(root, needed, o.max_install_bytes);
        report.details = {{"version", version},
                          {"asset_index", aid},
                          {"files_total", queue.size()},
                          {"bytes_total", total},
                          {"asset_bytes_declared", asset_bytes},
                          {"files", Json::array()}};
        uint64_t done = 0;
        size_t number = 0;
        for (const auto &p : queue) {
            check_cancel(cb);
            ++number;
            const Artifact &a = p.second;
            mkdirs(parent(root + "/" + a.path));
            DownloadRequest req =
                request(o, a.url, root + "/" + a.path, a.algorithm, a.hash, a.size, a.max_bytes);
            DownloadCallbacks wrapped = cb;
            if (cb.progress)
                wrapped.progress = [&, orig = cb.progress](const DownloadProgress &cur) {
                    DownloadProgress all = cur;
                    all.bytes = done + cur.bytes;
                    all.total = total;
                    all.message = std::to_string(number) + "/" + std::to_string(queue.size()) + " " + a.kind +
                                  " " + a.path;
                    return orig(all);
                };
            auto stats = (a.kind == "asset_index") ? ai_stats : download_verified(req, wrapped);
            done += a.size;
            report.details["files"].push_back({{"path", a.path},
                                               {"kind", a.kind},
                                               {"sha1", a.hash},
                                               {"size", a.size},
                                               {"from_cache", stats.from_cache}});
        }
        auto verification = verify_install(root, version, o, cb);
        if (!verification.ok)
            return verification;
        report.ok = true;
        report.status = "verified";
        report.details["installed"] = true;
        report.details["verification"] = verification.details;
        const std::string receipt = install_receipt_path(root, version);
        Json receipt_data = {{"version", version},
                             {"installed", true},
                             {"status", "verified"},
                             {"files_total", report.details["files_total"]},
                             {"bytes_total", total}};
        atomic_text(receipt, receipt_data.dump(2) + "\n");
        report.details["receipt_path"] = receipt;
    } catch (const Cancelled &e) {
        report.cancelled = true;
        report.status = "cancelled";
        report.details["error"] = e.what();
    } catch (const std::exception &e) {
        report = report_error(e);
    }
    return report;
}

std::string install_receipt_path(const std::string &root, const std::string &version) {
    ensure_safe_id(version);
    return root + "/meta/net.minecraft/" + version + ".installed.json";
}
InstallReport verify_install(const std::string &root, const std::string &version, const InstallOptions &o,
                             const DownloadCallbacks &cb) {
    InstallReport r;
    try {
        check_options(o);
        ensure_safe_id(version);
        Json asset_meta;
        auto queue = build_artifacts(root, version, asset_meta, o.asset_base_url);
        Json missing = Json::array(), corrupt = Json::array();
        uint64_t checked = 0, bytes = 0, total = 0;
        for (const auto &p : queue)
            total += p.second.size;
        size_t n = 0;
        for (const auto &p : queue) {
            check_cancel(cb);
            ++n;
            const Artifact &a = p.second;
            std::string full = root + "/" + a.path;
            if (!file_exists(full)) {
                if (missing.size() < 128)
                    missing.push_back(a.path);
                continue;
            }
            if (!verify_file(full, a.algorithm, a.hash, a.size)) {
                if (corrupt.size() < 128)
                    corrupt.push_back(a.path);
                continue;
            }
            ++checked;
            bytes += a.size;
            if (cb.progress) {
                DownloadProgress prog;
                prog.bytes = bytes;
                prog.total = total;
                prog.message =
                    "Verifying " + std::to_string(n) + "/" + std::to_string(queue.size()) + " " + a.path;
                if (!cb.progress(prog))
                    throw Cancelled();
            }
        }
        bool ok = missing.empty() && corrupt.empty();
        r.ok = ok;
        r.status = ok ? "verified" : "incomplete";
        r.details = {{"version", version},
                     {"installed", ok},
                     {"files_total", queue.size()},
                     {"files_verified", checked},
                     {"bytes_verified", bytes},
                     {"missing_files", missing},
                     {"corrupt_files", corrupt},
                     {"truncated_issue_lists", missing.size() == 128 || corrupt.size() == 128}};
    } catch (const Cancelled &e) {
        r.cancelled = true;
        r.status = "cancelled";
        r.details["error"] = e.what();
    } catch (const std::exception &e) {
        r = report_error(e);
    }
    return r;
}
} // namespace sc
