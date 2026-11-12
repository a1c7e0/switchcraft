#include "switchcraft/minecraft_launch.h"

#include "install.hpp"
#include "instances.hpp"
#include "metadata.hpp"
#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

namespace {
constexpr const char *kVersion = "26.4-snapshot-6";
constexpr const char *kMetadataMainClass = "net.minecraft.client.main.Main";
/* JsLaunchRequest expects the binary name in slash-separated JNI form. */
constexpr const char *kMainClass = "net/minecraft/client/main/Main";

std::string request_path(const std::string &root) {
    return root + "/tmp/minecraft-launch-request.json";
}
void set_error(char *out, size_t capacity, const std::string &message) {
    if (!out || !capacity)
        return;
    std::snprintf(out, capacity, "%s", message.c_str());
}
bool regular_file(const std::string &path) {
    struct stat st{};
    return lstat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}
void require_plain_directory(const std::string &path, bool create) {
    struct stat st{};
    if (lstat(path.c_str(), &st) == 0) {
        if (!S_ISDIR(st.st_mode))
            throw std::runtime_error("Launch request directory is not a real directory");
        return;
    }
    if (errno != ENOENT || !create || mkdir(path.c_str(), 0700) != 0)
        throw std::runtime_error("Cannot access launch request directory");
}
void copy_text(char *dest, size_t capacity, const std::string &value,
               const char *field) {
    if (value.empty() || value.size() >= capacity ||
        value.find_first_of("\r\n\t") != std::string::npos)
        throw std::runtime_error(std::string("Invalid ") + field + " in launch plan");
    std::memcpy(dest, value.c_str(), value.size() + 1);
}
std::string config_root(const std::string &runtime_root) {
    sc::Config config = sc::load_config(runtime_root + "/config/launcher.json");
    return config.root;
}
void fill_request(const std::string &runtime_root, const std::string &shared_root,
                  const std::string &instance_id, ScMinecraftLaunchRequest &out,
                  ScMinecraftLaunchProgress progress = nullptr,
                  void *progress_context = nullptr) {
    if (!sc::safe_id(instance_id))
        throw std::runtime_error("Invalid instance ID");
    sc::Config saved = sc::load_config(runtime_root + "/config/launcher.json");
    if (saved.root != shared_root)
        throw std::runtime_error("Save the shared installation preference before launching");
    sc::Instance instance = sc::load_instance(runtime_root, instance_id);
    if (instance.version != kVersion)
        throw std::runtime_error("Play Demo is available only for 26.4-snapshot-6");
    sc::DownloadCallbacks callbacks;
    if (progress) {
        callbacks.progress = [progress, progress_context](const sc::DownloadProgress &p) {
            return progress(progress_context, static_cast<unsigned long long>(p.bytes),
                            static_cast<unsigned long long>(p.total), p.message.c_str()) != 0;
        };
        callbacks.cancelled = [progress, progress_context] {
            return progress(progress_context, 0, 0, "Checking cancellation") == 0;
        };
    }
    sc::InstallReport verified = sc::verify_install(shared_root, kVersion, {}, callbacks);
    if (!verified.ok) {
        std::string reason = verified.details.value("error", std::string{});
        if (reason.empty()) {
            sc::Json missing = verified.details.value("missing_files", sc::Json::array());
            sc::Json corrupt = verified.details.value("corrupt_files", sc::Json::array());
            reason = !missing.empty() ? "Installed snapshot files are missing; install or repair them first: " + missing.front().get<std::string>()
                                      : (!corrupt.empty() ? "Installed snapshot files failed verification; repair them first: " + corrupt.front().get<std::string>()
                                                          : "Installed snapshot verification failed");
        }
        throw std::runtime_error(reason);
    }

    sc::Json plan = sc::make_instance_plan(instance, shared_root, runtime_root);
    if (plan.value("version", std::string{}) != kVersion ||
        plan.value("java_major", 0) != 25 ||
        plan.value("graphics", std::string{}) != "nvk" ||
        plan.value("main_class", std::string{}) != kMetadataMainClass)
        throw std::runtime_error("Installed metadata does not match the fixed Java 25 Vulkan Demo target");
    sc::Json missing = plan.value("missing_files", sc::Json::array());
    if (!missing.empty())
        throw std::runtime_error("Launch plan has missing files; install or repair the snapshot first");
    sc::Json cp = plan.value("classpath", sc::Json::array());
    if (!cp.is_array() || cp.empty())
        throw std::runtime_error("Launch plan has no classpath");
    std::string classpath;
    for (const auto &entry : cp) {
        if (!entry.is_string())
            throw std::runtime_error("Invalid classpath entry in launch plan");
        const std::string path = entry.get<std::string>();
        if (path.empty() || path.find(';') != std::string::npos || !regular_file(path))
            throw std::runtime_error("Classpath file is missing or unsafe");
        if (!classpath.empty()) classpath.push_back(';');
        classpath += path;
    }
    if (classpath.size() >= sizeof(out.classpath))
        throw std::runtime_error("Launch classpath exceeds the runtime request limit");
    copy_text(out.classpath, sizeof(out.classpath), classpath, "classpath");
    copy_text(out.main_class, sizeof(out.main_class), kMainClass, "main class");
    copy_text(out.game_directory, sizeof(out.game_directory),
              plan.at("game_directory").get<std::string>(), "game directory");
    out.heap_mib = std::max(64u, std::min(1024u, instance.heap_mib));

    const std::string expected_asset_prefix = shared_root + "/assets/indexes/";
    const std::string asset_index_path = plan.value("asset_index", std::string{});
    if (asset_index_path.rfind(expected_asset_prefix, 0) != 0 ||
        asset_index_path.size() <= expected_asset_prefix.size() + 5 ||
        asset_index_path.substr(asset_index_path.size() - 5) != ".json")
        throw std::runtime_error("Installed snapshot has no valid asset index path");
    std::string asset_index = asset_index_path.substr(expected_asset_prefix.size(),
        asset_index_path.size() - expected_asset_prefix.size() - 5);
    if (!sc::safe_id(asset_index))
        throw std::runtime_error("Installed snapshot has no valid asset index ID");
    const std::string assets_root = shared_root + "/assets";
    struct Arg { const char *key; std::string value; } args[] = {
        {"--demo", ""}, {"--graphicsBackend", "VULKAN"},
        {"--version", kVersion}, {"--accessToken", ""},
        {"--gameDir", plan.at("game_directory").get<std::string>()},
        {"--assetsDir", assets_root}, {"--assetIndex", asset_index}};
    for (size_t i = 0; i < sizeof(args) / sizeof(args[0]); ++i) {
        const auto &arg = args[i];
        const bool has_value = i != 0;
        if (out.argument_count + (has_value ? 2u : 1u) >= SC_MC_LAUNCH_MAX_ARGS)
            throw std::runtime_error("Demo argument limit exceeded");
        copy_text(out.arguments[out.argument_count++], SC_MC_LAUNCH_STRING_CAP,
                  arg.key, "Demo argument");
        if (has_value) {
            if (arg.value.size() >= SC_MC_LAUNCH_STRING_CAP ||
                arg.value.find_first_of("\r\n\t") != std::string::npos)
                throw std::runtime_error("Invalid Demo argument value");
            std::memcpy(out.arguments[out.argument_count], arg.value.c_str(),
                        arg.value.size() + 1);
            ++out.argument_count;
        }
    }
    std::string agent = "-javaagent:" + runtime_root + "/launchers/switchcraft-launcher-bridge.jar";
    std::string heap = "-Xmx" + std::to_string(out.heap_mib) + "M";
    const std::string options[] = {"-Xms64M", heap,
        "--enable-native-access=ALL-UNNAMED",
        "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED",
        agent, "-Dorg.lwjgl.util.Debug=true",
        /* The Switch runtime is headless; avoid AWT display initialization.
           Use LWJGL's upstream allocator rather than its desktop jemalloc
           provider, which is not implemented on Horizon. */
        "-Djava.awt.headless=true", "-Dorg.lwjgl.system.allocator=system"};
    for (const auto &option : options) {
        if (out.option_count >= SC_MC_LAUNCH_MAX_OPTIONS)
            throw std::runtime_error("Java option limit exceeded");
        copy_text(out.options[out.option_count++], SC_MC_LAUNCH_STRING_CAP,
                  option, "Java option");
    }
}
}

extern "C" int sc_minecraft_launch_prepare(const char *runtime_root,
                                           const char *shared_root,
                                           const char *instance_id,
                                           ScMinecraftLaunchProgress progress,
                                           void *progress_context,
                                           char *error, size_t error_capacity) {
    try {
        if (!runtime_root || !shared_root || !instance_id)
            throw std::runtime_error("Missing launch request input");
        const std::string root(runtime_root), path = request_path(root);
        require_plain_directory(root + "/tmp", true);
        struct stat st{};
        if (lstat(path.c_str(), &st) == 0)
            throw std::runtime_error("A previous launch request is still pending; reopen the launcher to clear it");
        if (errno != ENOENT)
            throw std::runtime_error("Cannot inspect pending launch request");
        ScMinecraftLaunchRequest checked{};
        fill_request(root, shared_root, instance_id, checked, progress,
                     progress_context);
        if (progress &&
            !progress(progress_context, 0, 0, "Finalizing Demo launch request"))
            throw std::runtime_error("Demo launch preparation was cancelled");
        sc::save_json_atomic(path, sc::Json{{"schema_version", 1},
                                            {"instance_id", instance_id},
                                            {"mode", "official-demo"},
                                            {"shared_root", shared_root},
                                            {"version", kVersion},
                                            {"game_directory", checked.game_directory}});
        set_error(error, error_capacity, "");
        return 1;
    } catch (const std::exception &e) {
        set_error(error, error_capacity, e.what());
        return 0;
    }
}

extern "C" int sc_minecraft_launch_consume(const char *runtime_root,
                                           ScMinecraftLaunchRequest *request,
                                           char *error, size_t error_capacity) {
    std::string path;
    try {
        if (!runtime_root || !request)
            throw std::runtime_error("Missing launch request destination");
        const std::string root(runtime_root);
        path = request_path(root);
        struct stat queued_stat{};
        if (lstat(path.c_str(), &queued_stat) != 0 && errno == ENOENT) {
            set_error(error, error_capacity, "No pending Minecraft launch request");
            return 0;
        }
        if (!S_ISREG(queued_stat.st_mode))
            throw std::runtime_error("Pending launch request is not a regular file");
        sc::Json queued;
        {
            std::ifstream input(path, std::ios::binary);
            if (!input) throw std::runtime_error("Cannot read pending launch request");
            input >> queued;
        }
        /* Consume before validating or starting the VM: a failed attempt is never retried. */
        if (unlink(path.c_str()) != 0)
            throw std::runtime_error("Cannot consume pending launch request");
        if (!queued.is_object() || queued.value("schema_version", 0) != 1 ||
            queued.value("mode", std::string{}) != "official-demo" ||
            !queued.contains("instance_id") || !queued["instance_id"].is_string() ||
            !queued.contains("shared_root") || !queued["shared_root"].is_string() ||
            !queued.contains("version") || !queued["version"].is_string() ||
            !queued.contains("game_directory") || !queued["game_directory"].is_string())
            throw std::runtime_error("Pending launch request is malformed or unsupported");
        ScMinecraftLaunchRequest fresh{};
        const std::string shared = config_root(root);
        if (queued["shared_root"].get<std::string>() != shared ||
            queued["version"].get<std::string>() != kVersion)
            throw std::runtime_error("Pending launch request no longer matches current launcher settings");
        fill_request(root, shared, queued["instance_id"].get<std::string>(), fresh);
        if (queued["game_directory"].get<std::string>() != fresh.game_directory)
            throw std::runtime_error("Pending launch request game directory has changed");
        *request = fresh;
        set_error(error, error_capacity, "");
        return 1;
    } catch (const std::exception &e) {
        if (!path.empty()) unlink(path.c_str());
        set_error(error, error_capacity, e.what());
        return 0;
    }
}

extern "C" void sc_minecraft_launch_discard(const char *runtime_root) {
    if (runtime_root) (void)unlink(request_path(runtime_root).c_str());
}
