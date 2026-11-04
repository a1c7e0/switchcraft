#pragma once
#include "instances.hpp"
#include "ui_canvas.hpp"
namespace sc::ui {
enum class Page { Instances, Versions, Settings, Diagnostics, Details, Edit, Create, Plan, Log,
                  VersionDetails, Transfers, Archived, Import, ArchiveConfirm };
struct VersionRow { std::string id, type; bool installed=false, cached=false; };
struct TransferView {
    std::string title, message, error;
    uint64_t bytes=0,total=0;
    bool active=false,failed=false,completed=false,cancelled=false;
};
struct LauncherView {
    Page page=Page::Instances;
    std::vector<Instance> instances;
    std::vector<VersionRow> versions;
    unsigned cursor=0, selected_instance=0, selected_version=0;
    std::string shared_root, notice, clock;
    unsigned default_heap=512;
    bool dark=false, preview=false;
    Instance draft;
    Json plan;
    std::vector<std::string> log;
    std::vector<std::string> archived_names, archived_ids;
    std::string import_path;
    TransferView transfer;
};
void draw_launcher(Canvas &canvas,const LauncherView &view);
// Pointer interaction uses the same rows/cards as controller focus. -1 is no hit.
int launcher_hit(const LauncherView &view,int x,int y);
unsigned launcher_row_count(const LauncherView &view);
}
