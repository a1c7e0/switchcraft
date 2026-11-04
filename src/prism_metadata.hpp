#pragma once
#include "metadata.hpp"
#include <string>
#include <vector>

namespace sc {
struct PrismVersion {
    std::string version;
    std::string type;
    std::string release_time;
    bool recommended = false;
};

// Read Prism's cached package-version index; entries are ordered newest first
// by raw releaseTime, matching Meta::VersionList::setVersions.
std::vector<PrismVersion> load_prism_versions(const std::string &sharedroot, const std::string &uid);

// Build the minimal vanilla + required/suggested component set for a pinned Minecraft version.
Json prism_components_for_version(const std::string &sharedroot, const std::string &version);

// Resolve the local Prism component profile against cached metadata. No network
// access or installation is performed. Throws on unsupported component features.
Json resolve_prism_pack(const std::string &sharedroot, const std::string &runtime_root,
                        const std::string &instance_dir);
}
