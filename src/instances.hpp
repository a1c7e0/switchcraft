#pragma once

#include "metadata.hpp"
#include <string>
#include <vector>

namespace sc {
// User-facing launcher profile. The directory name is a stable, traversal-safe ID.
struct Instance {
    std::string id;
    std::string name;
    std::string version;
    unsigned heap_mib = 512;
};

// All persisted profiles live under <runtime_root>/instances/<id>.
std::vector<Instance> scan_instances(const std::string &runtime_root,
                                     std::vector<std::string> *errors = nullptr);
Instance load_instance(const std::string &runtime_root, const std::string &id);
Instance create_instance(const std::string &runtime_root, const std::string &shared_root,
                         const std::string &name, const std::string &version,
                         unsigned heap_mib = 512);
void rename_instance(const std::string &runtime_root, const std::string &id,
                     const std::string &new_name);
void save_instance(const std::string &runtime_root, const Instance &instance);
// Creates an empty isolated game directory and copies only recognized settings files.
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
