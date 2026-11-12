#include "install.hpp"
#include "launcher_controller.hpp"
#include "launcher_jobs.hpp"
#include "launcher_session.hpp"
#include "launcher_ui.hpp"
#include "platform.h"
#include "prism_metadata.hpp"
#include "switchcraft/minecraft_launch.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <fstream>
#include <javaswitch/runtime.h>
#include <set>
int sc_launcher_console();
namespace {
using namespace sc;
using namespace sc::ui;
constexpr int W = 1280, H = 720;
std::string keyboard(const std::string &heading, const std::string &initial, unsigned limit) {
    SwkbdConfig k{};
    Result rc = swkbdCreate(&k, 0);
    if (R_FAILED(rc))
        throw std::runtime_error("System keyboard unavailable: " + std::to_string(rc));
    swkbdConfigMakePresetDefault(&k);
    swkbdConfigSetHeaderText(&k, heading.c_str());
    swkbdConfigSetInitialText(&k, initial.c_str());
    swkbdConfigSetStringLenMax(&k, limit);
    char value[1024]{};
    rc = swkbdShow(&k, value, sizeof(value));
    swkbdClose(&k);
    return R_SUCCEEDED(rc) ? std::string(value) : initial;
}

} // namespace
int main() {
    sc_init("minecraft-launcher");
    sc_mkdirs(SC_ROOT "/config");
    Result rc = plInitialize(PlServiceType_User);
    PlFontData font{};
    bool pl_ready = R_SUCCEEDED(rc);
    if (pl_ready)
        rc = plGetSharedFontByType(&font, PlSharedFontType_Standard);
    if (R_FAILED(rc)) {
        sc_log("Shared font unavailable Result=0x%x; using console\n", rc);
        if (pl_ready)
            plExit();
        sc_exit();
        return sc_launcher_console();
    }
    std::vector<uint32_t> pixels(W * H);
    sc::ui::Canvas canvas(W, H, W, pixels.data());
    if (!canvas.set_font(static_cast<const uint8_t *>(font.address), font.size)) {
        plExit();
        sc_exit();
        return sc_launcher_console();
    }
    sc_console(false);
    Framebuffer fb{};
    rc = framebufferCreate(&fb, nwindowGetDefault(), W, H, PIXEL_FORMAT_RGBA_8888, 2);
    bool fb_ready = R_SUCCEEDED(rc);
    if (fb_ready)
        rc = framebufferMakeLinear(&fb);
    if (R_FAILED(rc)) {
        if (fb_ready)
            framebufferClose(&fb);
        canvas.clear_font();
        plExit();
        sc_console(true);
        sc_log("Launcher framebuffer Result=0x%x; using console\n", rc);
        sc_exit();
        return sc_launcher_console();
    }
    hidInitializeTouchScreen();
    LauncherServices services;
    services.keyboard = keyboard;
    services.log = [](const std::string &message) { sc_log("%s\n", message.c_str()); };
    services.network_begin = []() {
        Result result = socketInitializeDefault();
        sc_log("socketInitializeDefault Result=0x%x\n", result);
        if (R_FAILED(result))
            throw std::runtime_error("Network service unavailable: " + std::to_string(result));
    };
    services.network_end = []() { socketExit(); };
    if (R_SUCCEEDED(setsysInitialize())) {
        ColorSetId theme{};
        if (R_SUCCEEDED(setsysGetColorSetId(&theme)))
            services.system_dark = theme == ColorSetId_Dark;
        setsysExit();
    }
    LauncherSession app(SC_ROOT, std::move(services));
    auto &view = app.view;
    try {
        app.initialize();
    } catch (const std::exception &e) {
        view.notice = e.what();
        sc_log("Launcher startup: %s\n", e.what());
    }
    bool dirty = true, touched = false;
    u64 keys = 0, last_dir = 0;
    uint64_t repeat_at = 0;
    int minute = -1;
    while (!app.close_requested) {
        keys = 0;
        bool keep = sc_frame(&keys);
        if (!keep) {
            if (view.transfer.active) {
                app.exit_when_idle = true;
                app.input(Input::Close);
            } else
                break;
        }
        try {
            if (app.poll())
                dirty = true;
        } catch (const std::exception &e) {
            view.notice = e.what();
            sc_log("Task update: %s\n", e.what());
        }
        if (app.exit_when_idle && !view.transfer.active)
            break;
        auto now = std::time(nullptr);
        std::tm *clock = std::localtime(&now);
        if (clock && clock->tm_min != minute) {
            char text[16];
            std::strftime(text, sizeof(text), "%H:%M", clock);
            view.clock = text;
            minute = clock->tm_min;
            dirty = true;
        }
        uint64_t ms = armTicksToNs(armGetSystemTick()) / 1000000;
        u64 direction = sc_buttons_held() & (HidNpadButton_AnyUp | HidNpadButton_AnyDown |
                                             HidNpadButton_AnyLeft | HidNpadButton_AnyRight);
        if (direction != last_dir) {
            repeat_at = ms + 400;
            last_dir = direction;
        } else if (direction && ms >= repeat_at) {
            keys |= direction;
            repeat_at = ms + 110;
        }
        try {
            if (keys)
                dirty = true;
            if (keys & HidNpadButton_L)
                app.input(Input::PreviousTab);
            if (keys & HidNpadButton_R)
                app.input(Input::NextTab);
            if (keys & HidNpadButton_B)
                app.input(Input::Back);
            if (keys & HidNpadButton_AnyDown)
                app.input(Input::Down);
            if (keys & HidNpadButton_AnyUp)
                app.input(Input::Up);
            if (keys & HidNpadButton_AnyRight)
                app.input(Input::Right);
            if (keys & HidNpadButton_AnyLeft)
                app.input(Input::Left);
            if ((keys & HidNpadButton_X) && (view.page == Page::Instances || view.page == Page::Versions))
                app.input(Input::NewInstance);
            if ((keys & HidNpadButton_Y) && view.page == Page::Versions)
                app.input(Input::Refresh);
            if (keys & HidNpadButton_A)
                app.input(Input::Confirm);
            HidTouchScreenState touch{};
            hidGetTouchScreenStates(&touch, 1);
            if (touch.count && !touched) {
                int hit = launcher_hit(view, touch.touches[0].x, touch.touches[0].y);
                if (hit <= -10 && hit >= -13) {
                    view.page = Page(-10 - hit);
                    view.cursor = 0;
                } else if (hit == -20)
                    app.input(Input::Back);
                else if (hit == -21)
                    app.input(Input::Confirm);
                else if (hit == -22)
                    app.input(Input::NewInstance);
                else if (hit == -23) {
                    app.exit_when_idle = true;
                    app.input(Input::Close);
                } else if (hit == -24)
                    app.input(Input::Refresh);
                else if (hit >= 0) {
                    if (view.cursor == unsigned(hit))
                        app.input(Input::Confirm);
                    else
                        app.input(Input::FocusRow, hit);
                }
                dirty = true;
            }
            touched = touch.count != 0;
        } catch (const std::exception &e) {
            view.notice = e.what();
            sc_log("Launcher action: %s\n", e.what());
            dirty = true;
        }
        if (!app.chain.empty()) {
            const bool demo_launch = app.chain == "switchcraft-java25";
            if (sc_chain(app.chain.c_str()))
                break;
            if (demo_launch)
                sc_minecraft_launch_discard(SC_ROOT);
            app.chain.clear();
            view.notice = "Diagnostic could not be opened. See the log.";
            dirty = true;
        }
        if (dirty) {
            draw_launcher(canvas, view);
            dirty = false;
        }
        u32 stride = 0;
        void *out = framebufferBegin(&fb, &stride);
        if (out)
            for (int y = 0; y < H; y++)
                std::memcpy(static_cast<uint8_t *>(out) + y * stride, pixels.data() + y * W,
                            W * sizeof(uint32_t));
        framebufferEnd(&fb);
    }
    try {
        app.finish();
    } catch (const std::exception &e) {
        sc_log("Worker shutdown failed: %s\n", e.what());
        svcExitProcess();
    }
    framebufferClose(&fb);
    canvas.clear_font();
    plExit();
    sc_exit();
    return 0;
}
