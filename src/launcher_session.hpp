#pragma once
#include "install.hpp"
#include "launcher_controller.hpp"
#include "launcher_jobs.hpp"
#include <functional>
namespace sc::ui {
struct LauncherServices {
    std::function<std::string(const std::string &, const std::string &, unsigned)> keyboard;
    std::function<void(const std::string &)> log;
    std::function<void()> network_begin, network_end;
    bool system_dark = false;
};
class LauncherSession {
  public:
    LauncherSession(std::string runtime_root, LauncherServices services);
    ~LauncherSession();
    LauncherSession(const LauncherSession &) = delete;
    LauncherSession &operator=(const LauncherSession &) = delete;
    LauncherView view;
    ControllerState controller;
    Config config;
    bool config_valid = true, network_ready = false, close_requested = false, exit_when_idle = false;
    std::string chain, ca_bundle;
    LauncherJob job;
    void initialize();
    void input(Input, int row = -1);
    bool poll();
    void finish();

  private:
    std::string root_, logs_;
    LauncherServices services_;
    bool task_seen_ = true;
    std::string last_progress_;
    void refresh();
    void load_preferences();
    void save_preferences();
    void start_task(const std::string &, LauncherJob::Work, bool);
    InstallOptions options() const;
    void check_instance(const std::string &);
    void handle(const Effect &);
    void log(const std::string &);
};
} // namespace sc::ui
