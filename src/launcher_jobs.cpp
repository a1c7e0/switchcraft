#include "launcher_jobs.hpp"
#include <stdexcept>
namespace sc {
LauncherJob::LauncherJob() {
#ifdef __SWITCH__
    mutexInit(&mutex_);
#endif
}
void LauncherJob::lock() {
#ifdef __SWITCH__
    mutexLock(&mutex_);
#else
    mutex_.lock();
#endif
}
void LauncherJob::unlock() {
#ifdef __SWITCH__
    mutexUnlock(&mutex_);
#else
    mutex_.unlock();
#endif
}
LauncherJob::~LauncherJob() {
    cancel();
    if (joinable_) {
#ifdef __SWITCH__
        // Retain the mapping rather than returning to hbloader with a worker alive.
        if (R_FAILED(threadWaitForExit(&thread_)) || R_FAILED(threadClose(&thread_)))
            svcExitProcess();
#else
        thread_.join();
#endif
    }
}
void LauncherJob::start(const std::string &title, Work work) {
    reap();
    if (joinable_)
        throw std::runtime_error("Another transfer is still running");
    cancel_ = false;
    done_ = false;
    work_ = std::move(work);
    lock();
    state_ = JobSnapshot{};
    state_.title = title;
    state_.running = true;
    unlock();
    try {
#ifdef __SWITCH__
        Result rc = threadCreate(&thread_, entry, this, nullptr, 512 * 1024, 0x2c, -2);
        if (R_FAILED(rc))
            throw std::runtime_error("Cannot create transfer worker: " + std::to_string(rc));
        rc = threadStart(&thread_);
        if (R_FAILED(rc)) {
            threadClose(&thread_);
            throw std::runtime_error("Cannot start transfer worker: " + std::to_string(rc));
        }
#else
        thread_ = std::thread([this] { execute(); });
#endif
        joinable_ = true;
    } catch (const std::exception &e) {
        lock();
        state_.running = false;
        state_.complete = true;
        state_.error = e.what();
        unlock();
        done_ = true;
        throw;
    }
}
void LauncherJob::cancel() { cancel_ = true; }
JobSnapshot LauncherJob::snapshot() {
    lock();
    auto copy = state_;
    unlock();
    return copy;
}
void LauncherJob::reap() {
    if (!joinable_ || !done_)
        return;
    wait();
}
void LauncherJob::wait() {
    if (!joinable_)
        return;
#ifdef __SWITCH__
    Result rc = threadWaitForExit(&thread_);
    if (R_FAILED(rc))
        throw std::runtime_error("Cannot join transfer worker: " + std::to_string(rc));
    rc = threadClose(&thread_);
    if (R_FAILED(rc))
        throw std::runtime_error("Cannot close transfer worker: " + std::to_string(rc));
#else
    thread_.join();
#endif
    joinable_ = false;
    work_ = {};
}
#ifdef __SWITCH__
void LauncherJob::entry(void *context) { static_cast<LauncherJob *>(context)->execute(); }
#endif
void LauncherJob::execute() {
    DownloadCallbacks callbacks;
    callbacks.cancelled = [this] { return cancel_.load(); };
    callbacks.progress = [this](const DownloadProgress &p) {
        if (cancel_)
            return false;
        lock();
        state_.bytes = p.bytes;
        state_.total = p.total;
        state_.message = p.message;
        unlock();
        return !cancel_;
    };
    Json result;
    std::string error;
    try {
        result = work_(callbacks);
    } catch (const std::exception &e) {
        error = e.what();
    } catch (...) {
        error = "Unexpected worker error";
    }
    lock();
    state_.result = std::move(result);
    state_.error = error;
    state_.cancelled = cancel_;
    state_.running = false;
    state_.complete = true;
    unlock();
    done_ = true;
}
} // namespace sc
