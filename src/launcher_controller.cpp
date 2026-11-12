#include "launcher_controller.hpp"
#include <algorithm>
#include <array>

namespace sc::ui {
namespace {
const std::array<Page, 4> kTabs{Page::Instances, Page::Versions, Page::Settings, Page::Diagnostics};
const Instance *selected(const LauncherView &v) {
    return v.selected_instance < v.instances.size() ? &v.instances[v.selected_instance] : nullptr;
}
std::string selected_id(const LauncherView &v) {
    auto p = selected(v);
    return p ? p->id : std::string{};
}
void emit(std::vector<Effect> &out, EffectKind k, const LauncherView &v, unsigned row = 0,
          std::string value = {}) {
    Effect e{k, selected_id(v), v.draft, std::move(value), v.draft.version, row};
    if ((v.page == Page::Versions || v.page == Page::VersionDetails) &&
        v.selected_version < v.versions.size())
        e.version = v.versions[v.selected_version].id;
    out.push_back(std::move(e));
}
void go_home(LauncherView &v) {
    v.page = Page::Instances;
    v.cursor =
        std::min<unsigned>(v.selected_instance, v.instances.empty() ? 0 : unsigned(v.instances.size() - 1));
}
void begin_create(LauncherView &v, ControllerState &s, std::vector<Effect> &out) {
    if (v.versions.empty()) {
        v.notice = "Refresh the version catalog before creating an instance.";
        return;
    }
    s.return_page = v.page;
    v.page = Page::Create;
    v.cursor = 0;
    std::string version;
    if (v.selected_version < v.versions.size())
        version = v.versions[v.selected_version].id;
    v.draft = Instance{"", "New instance", version, v.default_heap};
    emit(out, EffectKind::BeginCreate, v);
}
void begin_edit(LauncherView &v, std::vector<Effect> &out) {
    if (auto p = selected(v)) {
        v.draft = *p;
        v.page = Page::Edit;
        v.cursor = 0;
        emit(out, EffectKind::BeginEdit, v);
    }
}
void switch_tab(LauncherView &v, int d) {
    auto it = std::find(kTabs.begin(), kTabs.end(), v.page);
    if (it == kTabs.end())
        return;
    int i = int(it - kTabs.begin());
    i = (i + d + int(kTabs.size())) % int(kTabs.size());
    v.page = kTabs[size_t(i)];
    v.cursor = 0;
    v.notice.clear();
}
unsigned count(const LauncherView &v) { return launcher_row_count(v); }
void adjust(LauncherView &v, int d) {
    if (v.page == Page::Settings) {
        if (v.cursor == 1)
            v.default_heap = std::clamp(int(v.default_heap) + d * 128, 128, 1024);
        else if (v.cursor == 2)
            v.dark = !v.dark;
        return;
    }
    if (v.page != Page::Edit && v.page != Page::Create)
        return;
    if (v.cursor == 2)
        v.draft.heap_mib = std::clamp(int(v.draft.heap_mib) + d * 128, 128, 1024);
    if (v.cursor == 1 && !v.versions.empty()) {
        std::vector<unsigned> usable;
        for (unsigned i = 0; i < v.versions.size(); ++i)
            if (v.versions[i].installed || v.versions[i].cached)
                usable.push_back(i);
        if (usable.empty())
            return;
        auto it = std::find_if(usable.begin(), usable.end(),
                               [&](unsigned i) { return v.versions[i].id == v.draft.version; });
        int n = it == usable.end() ? 0 : int(it - usable.begin());
        n = (n + d + int(usable.size())) % int(usable.size());
        v.draft.version = v.versions[usable[size_t(n)]].id;
    }
}
void archive_confirm(LauncherView &v, ControllerState &s, std::vector<Effect> &out, bool yes) {
    s.modal = Modal::None;
    v.page = Page::Details;
    v.cursor = 4;
    if (yes)
        emit(out, EffectKind::ArchiveInstance, v);
}
void confirm(LauncherView &v, ControllerState &s, std::vector<Effect> &out) {
    if (s.modal == Modal::ArchiveConfirm) {
        archive_confirm(v, s, out, v.cursor == 1);
        return;
    }
    switch (v.page) {
    case Page::Instances:
        if (v.instances.empty()) {
            begin_create(v, s, out);
            break;
        }
        v.cursor = std::min<unsigned>(v.cursor, unsigned(v.instances.size() - 1));
        v.selected_instance = v.cursor;
        v.page = Page::Details;
        v.cursor = 0;
        s.return_page = Page::Instances;
        break;
    case Page::Versions:
        if (v.cursor >= v.versions.size())
            break;
        v.selected_version = v.cursor;
        v.page = Page::VersionDetails;
        v.cursor = 0;
        break;
    case Page::VersionDetails:
        if (v.cursor == 0)
            emit(out, EffectKind::InstallVersion, v, v.cursor);
        else if (v.cursor == 1)
            begin_create(v, s, out);
        else if (v.cursor == 2)
            emit(out, EffectKind::VerifyVersion, v, v.cursor);
        break;
    case Page::Details:
        if (!selected(v))
            break;
        if (v.cursor == 0)
            emit(out, EffectKind::CheckInstance, v, v.cursor);
        else if (v.cursor == 1)
            begin_edit(v, out);
        else if (v.cursor == 2)
            emit(out, EffectKind::DuplicateInstance, v, v.cursor);
        else if (v.cursor == 3)
            emit(out, EffectKind::PlayDemo, v, v.cursor);
        else if (v.cursor == 4) {
            s.modal = Modal::ArchiveConfirm;
            v.page = Page::ArchiveConfirm;
            v.cursor = 0;
        } else if (v.cursor == 5)
            go_home(v);
        break;
    case Page::Edit:
    case Page::Create: {
        if (v.cursor == 0) {
            emit(out, EffectKind::OpenNameKeyboard, v, v.cursor, v.draft.name);
            break;
        }
        if (v.cursor == 1 || v.cursor == 2) {
            adjust(v, 1);
            break;
        }
        if (count(v) && v.cursor + 1 >= count(v))
            emit(out, v.page == Page::Create ? EffectKind::CreateInstance : EffectKind::SaveInstance, v,
                 v.cursor);
        break;
    }
    case Page::Settings:
        if (v.cursor == 0)
            emit(out, EffectKind::OpenRootKeyboard, v, v.cursor, v.shared_root);
        else if (v.cursor == 1 || v.cursor == 2)
            adjust(v, 1);
        else if (v.cursor == 3)
            emit(out, EffectKind::SavePreferences, v);
        else if (v.cursor == 4)
            emit(out, EffectKind::RefreshLibrary, v);
        else if (v.cursor == 5)
            emit(out, EffectKind::RefreshCatalog, v);
        else if (v.cursor == 6) {
            s.return_page = Page::Settings;
            v.page = Page::Import;
            v.cursor = 0;
        } else if (v.cursor == 7) {
            s.return_page = Page::Settings;
            v.page = Page::Archived;
            v.cursor = 0;
        }
        break;
    case Page::Diagnostics:
        if (v.cursor < 7)
            emit(out, EffectKind::OpenDiagnostic, v, v.cursor);
        else {
            emit(out, EffectKind::OpenLog, v, v.cursor);
            v.page = Page::Log;
            v.cursor = 0;
        }
        break;
    case Page::Plan:
        emit(out, EffectKind::ExportPlan, v, v.cursor);
        break;
    case Page::Import:
        if (v.cursor == 0)
            emit(out, EffectKind::OpenRootKeyboard, v, v.cursor, v.shared_root);
        else if (v.cursor == 1)
            emit(out, EffectKind::ImportInstance, v, v.cursor, v.import_path);
        break;
    case Page::Archived:
        if (v.cursor < v.archived_ids.size())
            emit(out, EffectKind::RestoreInstance, v, v.cursor, v.archived_ids[v.cursor]);
        break;
    case Page::ArchiveConfirm:
        archive_confirm(v, s, out, v.cursor == 1);
        break;
    case Page::Transfers:
        if (v.transfer.active) {
            if (s.task_status != TaskStatus::CancellationRequested) {
                s.task_status = TaskStatus::CancellationRequested;
                emit(out, EffectKind::CancelTask, v);
            }
        } else {
            v.page = Page::Versions;
            v.cursor = std::min(v.selected_version, unsigned(v.versions.empty() ? 0 : v.versions.size() - 1));
        }
        break;
    case Page::Log:
        break;
    }
}
} // namespace

std::vector<Effect> transition(LauncherView &v, ControllerState &s, Input in, int row) {
    std::vector<Effect> out;
    if (in == Input::TaskStarted) {
        s.task_status = TaskStatus::Running;
        return out;
    }
    if (in == Input::TaskFinished) {
        s.task_status = TaskStatus::Idle;
        return out;
    }
    if (in == Input::Close) {
        if (v.transfer.active) {
            if (s.task_status != TaskStatus::CancellationRequested) {
                s.task_status = TaskStatus::CancellationRequested;
                emit(out, EffectKind::CancelTask, v);
            }
        } else
            emit(out, EffectKind::Close, v);
        return out;
    }
    if (in == Input::CancelTask) {
        if (s.task_status == TaskStatus::Running) {
            s.task_status = TaskStatus::CancellationRequested;
            emit(out, EffectKind::CancelTask, v);
        }
        return out;
    }
    if (s.modal == Modal::ArchiveConfirm || v.page == Page::ArchiveConfirm) {
        if (in == Input::Back)
            archive_confirm(v, s, out, false);
        else if (in == Input::Confirm)
            archive_confirm(v, s, out, v.cursor == 1);
        else if (in == Input::Left || in == Input::Right || in == Input::Up || in == Input::Down)
            v.cursor = v.cursor == 0 ? 1 : 0;
        else if (in == Input::FocusRow && row >= 0 && row < 2)
            v.cursor = unsigned(row);
        return out;
    }
    switch (in) {
    case Input::FocusRow:
        if (row >= 0 && unsigned(row) < count(v))
            v.cursor = unsigned(row);
        break;
    case Input::Up:
    case Input::Down: {
        unsigned n = count(v);
        if (!n)
            break;
        if (v.page == Page::Instances) {
            if (in == Input::Down) {
                if (v.cursor + 3 < n)
                    v.cursor += 3;
            } else if (v.cursor >= 3)
                v.cursor -= 3;
        } else if (v.page == Page::Versions || v.page == Page::Archived) {
            if (in == Input::Down)
                v.cursor = std::min<unsigned>(v.cursor + 1, n - 1);
            else if (v.cursor > 0)
                --v.cursor;
        } else if (in == Input::Down)
            v.cursor = (v.cursor + 1) % n;
        else
            v.cursor = (v.cursor + n - 1) % n;
        break;
    }
    case Input::Left:
    case Input::Right:
        if (v.page == Page::Instances) {
            if (in == Input::Right) {
                if (v.cursor % 3 < 2 && v.cursor + 1 < v.instances.size())
                    ++v.cursor;
            } else if (v.cursor % 3 > 0)
                --v.cursor;
        } else if (v.page == Page::Settings || v.page == Page::Edit || v.page == Page::Create)
            adjust(v, in == Input::Right ? 1 : -1);
        break;
    case Input::NextTab:
        switch_tab(v, 1);
        break;
    case Input::PreviousTab:
        switch_tab(v, -1);
        break;
    case Input::Back:
        if (v.page == Page::Details)
            go_home(v);
        else if (v.page == Page::Edit) {
            v.page = Page::Details;
            v.cursor = 1;
            v.draft = Instance{};
        } else if (v.page == Page::Create) {
            v.page = s.return_page;
            v.cursor = 0;
            v.draft = Instance{};
        } else if (v.page == Page::VersionDetails) {
            v.page = Page::Versions;
            v.cursor = v.selected_version;
        } else if (v.page == Page::Transfers) {
            if (v.transfer.active) {
                if (s.task_status != TaskStatus::CancellationRequested) {
                    s.task_status = TaskStatus::CancellationRequested;
                    emit(out, EffectKind::CancelTask, v);
                }
            } else {
                v.page = Page::Versions;
                v.cursor =
                    std::min(v.selected_version, unsigned(v.versions.empty() ? 0 : v.versions.size() - 1));
            }
        } else if (v.page == Page::Archived || v.page == Page::Import) {
            v.page = s.return_page;
            v.cursor = 0;
        } else if (v.page == Page::Plan) {
            v.page = Page::Details;
            v.cursor = 0;
        } else if (v.page == Page::Log) {
            v.page = Page::Diagnostics;
            v.cursor = 0;
        } else
            go_home(v);
        v.notice.clear();
        break;
    case Input::NewInstance:
        if (v.page == Page::Versions && v.cursor < v.versions.size())
            v.selected_version = v.cursor;
        begin_create(v, s, out);
        break;
    case Input::EditInstance:
        begin_edit(v, out);
        break;
    case Input::Archive:
        if (selected(v)) {
            s.modal = Modal::ArchiveConfirm;
            v.page = Page::ArchiveConfirm;
            v.cursor = 0;
        }
        break;
    case Input::Restore:
        if (v.cursor < v.archived_ids.size())
            emit(out, EffectKind::RestoreInstance, v, v.cursor, v.archived_ids[v.cursor]);
        break;
    case Input::Refresh:
        emit(out, v.page == Page::Versions ? EffectKind::RefreshCatalog : EffectKind::RefreshLibrary, v);
        break;
    case Input::ImportMetadata:
        emit(out, EffectKind::RefreshCatalog, v);
        break;
    case Input::Duplicate:
        emit(out, EffectKind::DuplicateInstance, v);
        break;
    case Input::Confirm:
        confirm(v, s, out);
        break;
    case Input::CancelTask:
    case Input::TaskStarted:
    case Input::TaskFinished:
    case Input::Close:
        break;
    }
    return out;
}
} // namespace sc::ui
