#include "launcher_controller.hpp"
#include <cassert>
#include <string>
#include <vector>
using namespace sc::ui;
static bool has(const std::vector<Effect>& effects, EffectKind kind) {
    for (const auto& e : effects) if (e.kind == kind) return true;
    return false;
}
int main() {
    LauncherView v; ControllerState state;
    v.instances={{"a","Alpha","v1",512},{"b","Beta","v2",768}};
    v.versions={{"v1","release",true,true}};

    // Select a card, edit its draft, and cancel without producing a write.
    v.cursor=1;
    auto effects=transition(v,state,Input::Confirm);
    assert(effects.empty() && v.page==Page::Details && v.selected_instance==1);
    LauncherView empty; ControllerState empty_state;
    effects=transition(empty,empty_state,Input::NewInstance);
    assert(effects.empty() && empty.page==Page::Instances && !empty.notice.empty());
    effects=transition(v,state,Input::EditInstance);
    assert(has(effects,EffectKind::BeginEdit) && v.page==Page::Edit);
    v.draft.name="Unsaved change";
    effects=transition(v,state,Input::Back);
    assert(effects.empty() && v.page==Page::Details && v.cursor==1 && v.draft.id.empty());
    effects=transition(v,state,Input::Back);
    assert(effects.empty() && v.page==Page::Instances && v.cursor==1);

    // Creating a profile only opens a draft; Back cancels it. Persistence is
    // emitted only after the form's explicit Save row is confirmed.
    effects=transition(v,state,Input::NewInstance);
    assert(v.page==Page::Create && has(effects,EffectKind::BeginCreate));
    effects=transition(v,state,Input::Back);
    assert(effects.empty() && v.page==Page::Instances);
    effects=transition(v,state,Input::NewInstance);
    v.cursor=3;
    effects=transition(v,state,Input::Confirm);
    assert(has(effects,EffectKind::CreateInstance));

    // Archive has a cancellable confirmation state and only emits the archive
    // action after explicit confirmation.
    v.page=Page::Details; v.cursor=0; v.selected_instance=1;
    effects=transition(v,state,Input::Archive);
    assert(effects.empty() && state.modal==Modal::ArchiveConfirm);
    effects=transition(v,state,Input::Back);
    assert(effects.empty() && state.modal==Modal::None);
    effects=transition(v,state,Input::Archive);
    effects=transition(v,state,Input::Confirm);
    assert(effects.empty() && state.modal==Modal::None);
    effects=transition(v,state,Input::Archive);
    transition(v,state,Input::Right);
    effects=transition(v,state,Input::Confirm);
    assert(has(effects,EffectKind::ArchiveInstance) && state.modal==Modal::None);

    // Task cancellation changes reducer state once and emits one request.
    transition(v,state,Input::TaskStarted);
    effects=transition(v,state,Input::CancelTask);
    assert(has(effects,EffectKind::CancelTask));
    assert(state.task_status==TaskStatus::CancellationRequested);
    effects=transition(v,state,Input::CancelTask);
    assert(effects.empty());
    transition(v,state,Input::TaskFinished);
    assert(state.task_status==TaskStatus::Idle);

    // Version details return to the catalog, and create keeps the chosen
    // version even when metadata still needs to be downloaded by the platform.
    v.page=Page::Versions; v.versions={{"v-new","release",false,false},{"v-old","release",true,true}}; v.cursor=0;
    effects=transition(v,state,Input::Confirm);
    assert(effects.empty() && v.page==Page::VersionDetails && v.selected_version==0);
    v.cursor=0; effects=transition(v,state,Input::Confirm);
    assert(has(effects,EffectKind::InstallVersion) && effects[0].version=="v-new");
    v.cursor=1; effects=transition(v,state,Input::Confirm);
    assert(has(effects,EffectKind::BeginCreate) && v.page==Page::Create && v.draft.version=="v-new");
    transition(v,state,Input::Back);
    assert(v.page==Page::VersionDetails);
    transition(v,state,Input::Back);
    assert(v.page==Page::Versions && v.cursor==0);

    // Settings expose effects for preferences, catalog refresh, import and
    // archive browsing; the reducer itself never performs those operations.
    v.page=Page::Settings; v.cursor=3;
    effects=transition(v,state,Input::Confirm); assert(has(effects,EffectKind::SavePreferences));
    effects=transition(v,state,Input::Refresh); assert(has(effects,EffectKind::RefreshLibrary));
    v.page=Page::Versions;
    effects=transition(v,state,Input::Refresh); assert(has(effects,EffectKind::RefreshCatalog));
    v.page=Page::Settings;
    v.cursor=5; effects=transition(v,state,Input::Confirm); assert(has(effects,EffectKind::RefreshCatalog));
    v.cursor=6; effects=transition(v,state,Input::Confirm); assert(v.page==Page::Import && effects.empty());
    v.import_path="/sdmc/source"; v.cursor=0;
    effects=transition(v,state,Input::Confirm); assert(has(effects,EffectKind::OpenRootKeyboard));
    v.cursor=1; effects=transition(v,state,Input::Confirm);
    assert(has(effects,EffectKind::ImportInstance) && effects[0].value=="/sdmc/source");
    transition(v,state,Input::Back); assert(v.page==Page::Settings);
    v.cursor=7; effects=transition(v,state,Input::Confirm); assert(v.page==Page::Archived);
    v.archived_ids={"arch-1"}; v.cursor=0;
    effects=transition(v,state,Input::Confirm);
    assert(has(effects,EffectKind::RestoreInstance) && effects[0].value=="arch-1");

    // Back on a running transfer requests cancellation and stays on its page
    // until the UI reports that the worker has joined.
    v.page=Page::Transfers; v.transfer.active=true;
    transition(v,state,Input::TaskStarted);
    effects=transition(v,state,Input::Back);
    assert(has(effects,EffectKind::CancelTask) && v.page==Page::Transfers);
    effects=transition(v,state,Input::Close);
    assert(effects.empty()); // the prior Back already requested cancellation
    v.transfer.active=false; transition(v,state,Input::TaskFinished);
    transition(v,state,Input::Back); assert(v.page==Page::Versions);
    effects=transition(v,state,Input::Close);
    assert(has(effects,EffectKind::Close));

    // Grid navigation keeps a global cursor while moving by row and page.
    v.page=Page::Instances; v.instances.resize(8); v.cursor=0;
    transition(v,state,Input::Down);
    assert(v.cursor==3);
    transition(v,state,Input::Down);
    assert(v.cursor==6);
    transition(v,state,Input::Right);
    assert(v.cursor==7);
    transition(v,state,Input::Right);
    assert(v.cursor==7);
    return 0;
}
