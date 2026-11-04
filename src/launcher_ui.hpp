#pragma once
#include "instances.hpp"
#include "ui_canvas.hpp"
namespace sc::ui {
enum class Page { Instances, Versions, Settings, Diagnostics, Details, Edit, Create, Plan, Log };
struct VersionRow { std::string id, type; bool installed=false, cached=false; };
struct LauncherView {
    Page page=Page::Instances;
    std::vector<Instance> instances;
    std::vector<VersionRow> versions;
    unsigned cursor=0, selected_instance=0;
    std::string shared_root, notice, clock;
    unsigned default_heap=512;
    bool dark=false, preview=false;
    Instance draft;
    Json plan;
    std::vector<std::string> log;
};
void draw_launcher(Canvas &canvas,const LauncherView &view);
// Pointer interaction uses the same rows/cards as controller focus. -1 is no hit.
int launcher_hit(const LauncherView &view,int x,int y);
unsigned launcher_row_count(const LauncherView &view);
}
