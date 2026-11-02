#pragma once
#include "json.hpp"
#include <string>
#include <vector>

namespace sc {
using Json=nlohmann::json;
struct Config {
    std::string root="sdmc:/minecraft/.minecraft";
    std::string version;
    std::string runtime="diagnostic";
    std::string graphics="nvc0";
    unsigned heap_mib=256;
};
Json read_json(const std::string &path);
bool file_exists(const std::string &path);
bool safe_id(const std::string &id);
Config load_config(const std::string &path);
void save_config(const std::string &path,const Config &config);
std::vector<std::string> scan_versions(const std::string &root);
Json resolve_version(const std::string &root,const std::string &id);
Json make_plan(const Config &config,const std::string &runtime_root);
std::vector<std::string> manifest_ids(const Json &manifest);
}
