#pragma once
#include "download.hpp"
#include "metadata.hpp"
#include <atomic>
#include <functional>
#ifdef __SWITCH__
#include <switch.h>
#else
#include <mutex>
#include <thread>
#endif
namespace sc {
struct JobSnapshot {
    std::string title, message, error;
    uint64_t bytes = 0, total = 0;
    bool running = false, complete = false, cancelled = false;
    Json result;
};
// Owns the worker until it has been joined. NRO code must never unload early.
class LauncherJob {
  public:
    using Work = std::function<Json(const DownloadCallbacks &)>;
    LauncherJob();
    ~LauncherJob();
    LauncherJob(const LauncherJob &) = delete;
    LauncherJob &operator=(const LauncherJob &) = delete;
    void start(const std::string &title, Work work);
    void cancel();
    JobSnapshot snapshot();
    void reap();
    void wait();

  private:
    void execute();
    void lock();
    void unlock();
    std::atomic<bool> cancel_{false}, done_{false};
    bool joinable_ = false;
    JobSnapshot state_;
    Work work_;
#ifdef __SWITCH__
    Mutex mutex_{};
    Thread thread_{};
    static void entry(void *context);
#else
    std::mutex mutex_;
    std::thread thread_;
#endif
};
} // namespace sc
