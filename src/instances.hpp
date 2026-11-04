#pragma once

#include "metadata.hpp"
#include <string>
#include <cstddef>
#include <functional>
#include <vector>

namespace sc {
// User-facing launcher profile. The directory name is a stable, traversal-safe ID.
struct Instance {
    std::string id;
    std::string name;
    std::string version;
    unsigned heap_mib = 512;
};
struct ArchivedInstance {
    std::string archive_id;
    std::string original_id;
    std::string name;
    std::string version;
    unsigned heap_mib = 512;
};
struct ImportOptions {
    size_t max_files = 20000;
    size_t max_bytes = 2ULL * 1024 * 1024 * 1024;
    std::function<bool(size_t files_copied, size_t bytes_copied)> should_cancel;
};

// All persisted profiles live under <runtime_root>/instances/<id>.
std::vector<Instance> scan_instances(const std::string &runtime_root,
                                     std::vector<std::string> *errors = nullptr);
Instance load_instance(const std::string &runtime_root, const std::string &id);
std::string archive_instance(const std::string &runtime_root, const std::string &id);
std::vector<ArchivedInstance> list_archived_instances(const std::string &runtime_root);
Instance restore_instance(const std::string &runtime_root, const std::string &archive_id);
Instance import_instance(const std::string &runtime_root, const std::string &shared_root,
                        const std::string &source_directory, const ImportOptions &options = {});
void update_instance_version(const std::string &runtime_root, const std::string &shared_root,
                             const std::string &id, const std::string &version);
Instance create_instance(const std::string &runtime_root, const std::string &shared_root,
                         const std::string &name, const std::string &version,
                         unsigned heap_mib = 512);
void rename_instance(const std::string &runtime_root, const std::string &id,
                     const std::string &new_name);
void save_instance(const std::string &runtime_root, const Instance &instance);
// Clones profile settings/components and bounded local patches into an empty game directory.
Instance duplicate_instance(const std::string &runtime_root, const std::string &shared_root,
                            const std::string &id,
                            const std::string &new_name);
std::string instance_game_directory(const std::string &runtime_root,
                                    const std::string &id);
Config instance_config(const Instance &instance, const std::string &shared_root);
// Uses the shared installation for versions/libraries/assets and the instance's game directory.
Json make_instance_plan(const Instance &instance, const std::string &shared_root,
                        const std::string &runtime_root);
}
