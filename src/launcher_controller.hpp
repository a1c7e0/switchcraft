#pragma once
#include "launcher_ui.hpp"
#include <string>
#include <vector>

namespace sc::ui {
enum class Input {
    Up,
    Down,
    Left,
    Right,
    Confirm,
    Back,
    NextTab,
    PreviousTab,
    NewInstance,
    EditInstance,
    Archive,
    Restore,
    Refresh,
    ImportMetadata,
    Duplicate,
    CancelTask,
    FocusRow,
    TaskStarted,
    TaskFinished,
    Close
};
enum class EffectKind {
    OpenNameKeyboard,
    OpenRootKeyboard,
    SavePreferences,
    RefreshLibrary,
    RefreshCatalog,
    InstallVersion,
    VerifyVersion,
    CheckInstance,
    OpenDiagnostic,
    OpenLog,
    ExportPlan,
    Close,
    BeginCreate,
    BeginEdit,
    CreateInstance,
    SaveInstance,
    ImportInstance,
    ArchiveInstance,
    RestoreInstance,
    DuplicateInstance,
    CancelTask
};
enum class Modal { None, ArchiveConfirm };
enum class TaskStatus { Idle, Running, CancellationRequested };
struct Effect {
    EffectKind kind;
    std::string instance_id;
    Instance draft;
    std::string value;
    std::string version;
    unsigned row = 0;
};
struct ControllerState {
    Modal modal = Modal::None;
    TaskStatus task_status = TaskStatus::Idle;
    Page return_page = Page::Instances;
};
// Applies an input to navigation state and returns platform work to perform.
// No filesystem, network, keyboard, or console calls occur here.
std::vector<Effect> transition(LauncherView &view, ControllerState &state, Input input, int row = -1);
} // namespace sc::ui
