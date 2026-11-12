#include "launcher_session.hpp"
#include "switchcraft/minecraft_launch.h"
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <thread>
using namespace sc;
using namespace sc::ui;
extern "C" int sc_minecraft_launch_prepare(const char *, const char *, const char *,
                                             ScMinecraftLaunchProgress, void *,
                                             char *error, size_t capacity) {
    if (error && capacity) std::snprintf(error, capacity, "snapshot target unavailable in this 1.20 fixture");
    return 0;
}
static void write(const std::string &p, const std::string &s) {
    std::filesystem::create_directories(std::filesystem::path(p).parent_path());
    std::ofstream f(p);
    f << s;
}
static void wait(LauncherSession &s) {
    for (int i = 0; i < 500 && s.view.transfer.active; i++) {
        s.poll();
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    s.poll();
    assert(!s.view.transfer.active);
}
int main(int argc, char **argv) {
    assert(argc == 2);
    std::string base = argv[1], runtime = base + "/runtime", shared = base + "/shared";
    std::filesystem::create_directories(runtime + "/config");
    std::filesystem::create_directories(runtime + "/logs");
    std::filesystem::create_directories(shared + "/versions/1.20");
    write(shared + "/versions/1.20/1.20.json",
          R"({"id":"1.20","type":"release","mainClass":"x","libraries":[]})");
    save_json_atomic(runtime + "/config/launcher.json", Json{{"minecraft_root", shared},
                                                             {"heap_mib", 512},
                                                             {"unknown_setting", "preserved"},
                                                             {"network_ca_file", "test-ca"}});
    save_json_atomic(runtime + "/config/launcher-ui.json", Json{{"unknown_ui", 7}});
    std::vector<std::string> logs;
    std::string next_name = "World";
    LauncherServices svc;
    svc.system_dark = true;
    svc.keyboard = [&](const std::string &, const std::string &initial, unsigned) {
        return next_name.empty() ? initial : next_name;
    };
    svc.log = [&](const auto &s) { logs.push_back(s); };
    LauncherSession s(runtime, svc);
    s.initialize();
    assert(s.view.dark && s.ca_bundle == "test-ca");
    s.view.selected_version = 1;
    s.input(Input::NewInstance);
    assert(s.view.page == Page::Create);
    s.input(Input::FocusRow, 0);
    s.input(Input::Confirm);
    s.input(Input::FocusRow, 3);
    s.input(Input::Confirm);
    assert(s.view.transfer.active);
    wait(s);
    assert(s.view.instances.size() == 1);
    auto id = s.view.instances[0].id;
    s.view.selected_instance = 0;
    s.view.page = Page::Details;
    s.view.cursor = 3;
    s.input(Input::Confirm);
    wait(s);
    assert(s.view.transfer.failed &&
           s.view.transfer.error == "snapshot target unavailable in this 1.20 fixture");
    assert(s.chain.empty());
    s.view.page = Page::Instances;
    s.input(Input::Confirm);
    s.input(Input::EditInstance);
    next_name = "discarded";
    s.input(Input::FocusRow, 0);
    s.input(Input::Confirm);
    s.input(Input::Back);
    assert(load_instance(runtime, id).name == "World");
    s.input(Input::EditInstance);
    next_name = "Renamed";
    s.input(Input::FocusRow, 0);
    s.input(Input::Confirm);
    s.input(Input::FocusRow, 3);
    s.input(Input::Confirm);
    wait(s);
    assert(load_instance(runtime, id).name == "Renamed");
    s.input(Input::Back);
    s.input(Input::Duplicate);
    assert(s.view.instances.size() == 2);
    s.view.selected_instance = 0;
    s.view.page = Page::Details;
    s.input(Input::Archive);
    s.input(Input::Confirm);
    assert(load_instance(runtime, id).id == id);
    s.input(Input::Archive);
    s.input(Input::Right);
    s.input(Input::Confirm);
    assert(!std::filesystem::exists(runtime + "/instances/" + id));
    s.view.page = Page::Settings;
    s.view.cursor = 7;
    s.input(Input::Confirm);
    assert(!s.view.archived_ids.empty());
    s.view.cursor = 0;
    s.input(Input::Confirm);
    assert(std::filesystem::exists(runtime + "/instances/" + id));
    std::string source = base + "/external/prism";
    write(source + "/instance.cfg",
          "ConfigVersion=1.3\nInstanceType=OneSix\nname=Imported\nMaxMemAlloc=512\n");
    write(source + "/mmc-pack.json",
          R"({"formatVersion":1,"components":[{"uid":"net.minecraft","version":"1.20"}]})");
    std::filesystem::create_directories(source + "/.minecraft/saves/world");
    write(source + "/.minecraft/saves/world/level.dat", "safe");
    s.view.page = Page::Import;
    s.view.cursor = 0;
    s.view.import_path = source;
    s.input(Input::FocusRow, 1);
    s.input(Input::Confirm);
    wait(s);
    assert(!s.view.transfer.failed);
    assert(s.view.instances.size() >= 2);
    s.view.plan = Json{{"ok", true}};
    s.view.page = Page::Plan;
    s.input(Input::Confirm);
    assert(std::filesystem::exists(runtime + "/logs/launch-plan.json"));
    s.view.page = Page::Settings;
    s.view.cursor = 3;
    s.input(Input::Confirm);
    auto cfg = read_json(runtime + "/config/launcher.json");
    assert(cfg["unknown_setting"] == "preserved" && cfg["network_ca_file"] == "test-ca");
    assert(read_json(runtime + "/config/launcher-ui.json")["unknown_ui"] == 7);
    s.view.page = Page::Import;
    s.view.import_path = source;
    s.view.cursor = 1;
    s.input(Input::Confirm);
    assert(s.view.transfer.active);
    s.input(Input::Close);
    assert(s.exit_when_idle);
    wait(s);
    assert(s.close_requested);
    s.finish();
    return 0;
}
