#pragma once

#include <cstdint>
#include <functional>
#include <string>

namespace sc {

struct DownloadRequest {
    std::string url;
    std::string target;
    std::string algorithm;      // "sha1" or "sha256"
    std::string expected_hash;  // lowercase or uppercase hexadecimal
    uint64_t expected_size = 0; // zero means not declared
    uint64_t max_bytes = 1024ULL * 1024 * 1024;
    unsigned retries = 2;
    bool repair_corrupt = false;
    bool allow_http_for_tests = false; // production callers must leave false
    std::string ca_bundle;             // empty uses libcurl's configured trust store
};

struct DownloadProgress {
    uint64_t bytes = 0;
    uint64_t total = 0;
    std::string message;
};

struct DownloadCallbacks {
    // Return false to cancel. Invoked synchronously from the transfer thread.
    std::function<bool(const DownloadProgress &)> progress;
    std::function<bool()> cancelled; // true means cancellation requested
};

struct DownloadStats {
    uint64_t bytes = 0;
    std::string sha256;
    unsigned attempts = 0;
    bool from_cache = false;
};

// Bounded UTF-8/JSON-sized HTTPS GET. The response is held in memory up to max_bytes.
std::string fetch_text(const std::string &url, uint64_t max_bytes, const DownloadCallbacks &callbacks = {},
                       const std::string &ca_bundle = {}, bool allow_http_for_tests = false);

// Stream to target.part, verify size and SHA-1/SHA-256, then publish the file.
// Existing valid content is reused; corrupt existing content is preserved unless
// repair_corrupt is explicitly true. A stale/unowned .part is never overwritten.
DownloadStats download_verified(const DownloadRequest &request, const DownloadCallbacks &callbacks = {});

// Read-only local integrity check. Returns false for missing/non-regular files
// and for digest or declared-size mismatches; malformed hash parameters throw.
bool verify_file(const std::string &path, const std::string &algorithm, const std::string &expected_hash,
                 uint64_t expected_size = 0);

// Call after all worker threads that used this module have joined and before
// unloading the NRO. Closes easy handles and libcurl's process-global state.
// A later call can initialize a fresh transport generation if needed.
void shutdown_download_transport();

} // namespace sc
