#pragma once
#include "download.hpp"
#include "metadata.hpp"
#include <cstdint>
#include <string>

namespace sc {
constexpr const char *kPrismMetadataBase = "https://meta.prismlauncher.org/v1";
constexpr const char *kPinnedMinecraftVersion = "26.4-snapshot-6";

struct InstallOptions {
    std::string prism_base_url = kPrismMetadataBase;
    std::string ca_bundle;
    std::string asset_base_url = "https://resources.download.minecraft.net";
    uint64_t max_install_bytes = 2ULL * 1024 * 1024 * 1024;
    bool allow_test_mirror = false;
    bool allow_http_for_tests = false;
    bool repair_corrupt_managed_cache = false;
};

struct InstallReport {
    bool ok = false;
    bool cancelled = false;
    std::string status;
    Json details = Json::object();
    Json to_json() const;
};

// Refreshes the official component index and hash-pinned metadata needed for the
// requested snapshot. This changes only shared meta cache files.
InstallReport refresh_catalog(const std::string &sharedroot,
                              const std::string &version = kPinnedMinecraftVersion,
                              const InstallOptions &options = {}, const DownloadCallbacks &callbacks = {});

// Fetch and verify the client, Horizon-applicable Java libraries, asset index,
// and SHA-1-addressed asset objects. Only managed shared cache directories are written.
InstallReport prepare_install(const std::string &sharedroot, const std::string &version,
                              const InstallOptions &options = {}, const DownloadCallbacks &callbacks = {});

// Read-only report for the artifacts declared by the cached component metadata.
InstallReport verify_install(const std::string &sharedroot, const std::string &version,
                             const InstallOptions &options = {}, const DownloadCallbacks &callbacks = {});
std::string install_receipt_path(const std::string &sharedroot, const std::string &version);
} // namespace sc
