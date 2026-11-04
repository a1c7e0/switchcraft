#include "launcher_session.hpp"
#include "prism_metadata.hpp"
#include <algorithm>
#include <fstream>
#include <set>
namespace sc::ui {
namespace {
bool exists(const std::string &p) {
  std::ifstream f(p, std::ios::binary);
  return bool(f);
}
} // namespace
LauncherSession::LauncherSession(std::string root, LauncherServices s)
    : root_(std::move(root)), logs_(root_ + "/logs"), services_(std::move(s)) {
  if (!services_.keyboard)
    services_.keyboard = [](const auto &, const auto &i, unsigned) {
      return i;
    };
  if (!services_.log)
    services_.log = [](const auto &) {};
}
LauncherSession::~LauncherSession() { job.cancel(); }
void LauncherSession::log(const std::string &s) { services_.log(s); }
void LauncherSession::initialize() {
  load_preferences();
  if (exists(root_ + "/config/launcher.json"))
    try {
      ca_bundle = read_json(root_ + "/config/launcher.json")
                      .value("network_ca_file", std::string{});
    } catch (...) {
    }
  refresh();
}
void LauncherSession::load_preferences() {
  try {
    config = load_config(root_ + "/config/launcher.json");
  } catch (const std::exception &e) {
    config_valid = false;
    view.notice =
        "Existing configuration could not be read; it will be preserved.";
    log(std::string("Configuration: ") + e.what());
  }
  view.shared_root = config.root;
  view.default_heap = std::max(128u, config.heap_mib);
  config.graphics = "nvk";
  config.runtime = "openjdk25";
  view.dark = services_.system_dark;
  if (exists(root_ + "/config/launcher-ui.json"))
    try {
      view.dark = read_json(root_ + "/config/launcher-ui.json")
                      .value("dark", view.dark);
    } catch (const std::exception &e) {
      config_valid = false;
      log(std::string("UI configuration preserved: ") + e.what());
    }
}
void LauncherSession::refresh() {
  std::vector<std::string> errors;
  view.instances = scan_instances(root_, &errors);
  std::string selected = view.selected_version < view.versions.size()
                             ? view.versions[view.selected_version].id
                             : kPinnedMinecraftVersion;
  auto installed = [&](const std::string &id) {
    try {
      auto p = install_receipt_path(view.shared_root, id);
      if (exists(p)) {
        auto j = read_json(p);
        return j.value("installed", false) &&
               j.value("version", std::string{}) == id;
      }
    } catch (...) {
    }
    return false;
  };
  view.versions.clear();
  std::set<std::string> seen;
  for (const auto &id : scan_versions(view.shared_root)) {
    seen.insert(id);
    view.versions.push_back({id, "local", installed(id), true});
  }
  if (exists(view.shared_root + "/meta/net.minecraft/index.json"))
    try {
      for (const auto &e :
           load_prism_versions(view.shared_root, "net.minecraft"))
        if (!seen.count(e.version)) {
          seen.insert(e.version);
          view.versions.push_back(
              {e.version, e.type, installed(e.version),
               exists(view.shared_root + "/meta/net.minecraft/" + e.version +
                      ".json")});
        }
    } catch (const std::exception &e) {
      errors.push_back(e.what());
    }
  if (!seen.count(kPinnedMinecraftVersion))
    view.versions.insert(view.versions.begin(),
                         {kPinnedMinecraftVersion, "snapshot",
                          installed(kPinnedMinecraftVersion), false});
  view.selected_version = 0;
  for (unsigned i = 0; i < view.versions.size(); i++)
    if (view.versions[i].id == selected)
      view.selected_version = i;
  view.archived_ids.clear();
  view.archived_names.clear();
  try {
    for (const auto &a : list_archived_instances(root_)) {
      view.archived_ids.push_back(a.archive_id);
      view.archived_names.push_back(a.name + " / " + a.version);
    }
  } catch (const std::exception &e) {
    errors.push_back(e.what());
  }
  if (!errors.empty()) {
    view.notice = "Some profiles could not be read. See the launcher log.";
    for (const auto &e : errors)
      log("Library scan: " + e);
  }
  view.cursor = 0;
  if (view.selected_instance >= view.instances.size())
    view.selected_instance = 0;
}
void LauncherSession::save_preferences() {
  if (!config_valid)
    throw std::runtime_error(
        "Repair the existing configuration on SD before saving.");
  config.root = view.shared_root;
  config.heap_mib = view.default_heap;
  save_config(root_ + "/config/launcher.json", config);
  Json ui = Json::object();
  if (exists(root_ + "/config/launcher-ui.json"))
    try {
      ui = read_json(root_ + "/config/launcher-ui.json");
    } catch (...) {
    }
  ui["schema_version"] = 1;
  ui["dark"] = view.dark;
  save_json_atomic(root_ + "/config/launcher-ui.json", ui);
  view.notice = "Preferences saved.";
  log("Launcher preferences saved");
}
void LauncherSession::start_task(const std::string &t, LauncherJob::Work w,
                                 bool network) {
  if (network && !network_ready) {
    if (services_.network_begin)
      services_.network_begin();
    network_ready = true;
  }
  job.start(t, std::move(w));
  task_seen_ = false;
  last_progress_.clear();
  view.transfer = TransferView{};
  view.transfer.title = t;
  view.transfer.active = true;
  view.page = Page::Transfers;
  view.cursor = 0;
  transition(view, controller, Input::TaskStarted);
  log("Task started: " + t);
}
InstallOptions LauncherSession::options() const {
  InstallOptions o;
  o.ca_bundle = ca_bundle;
  o.repair_corrupt_managed_cache = true;
  return o;
}
void LauncherSession::check_instance(const std::string &id) {
  auto i = load_instance(root_, id);
  view.plan = make_instance_plan(i, view.shared_root, root_);
  view.page = Page::Plan;
  view.cursor = 0;
}
void LauncherSession::handle(const Effect &e) {
  std::string root = view.shared_root;
  switch (e.kind) {
  case EffectKind::BeginCreate:
  case EffectKind::BeginEdit:
    break;
  case EffectKind::OpenNameKeyboard:
    view.draft.name = services_.keyboard("Instance name", view.draft.name, 24);
    break;
  case EffectKind::OpenRootKeyboard:
    if (view.page == Page::Import)
      view.import_path =
          services_.keyboard("Prism instance folder", view.import_path, 240);
    else {
      auto p = services_.keyboard("Shared Minecraft installation",
                                  view.shared_root, 240);
      if (p.empty() || p.find("..") != p.npos ||
          p.find_first_of("\r\n\t") != p.npos)
        throw std::runtime_error("Invalid installation folder");
      view.shared_root = p;
      refresh();
      view.notice = "Folder changed. Save preferences to keep it.";
    }
    break;
  case EffectKind::SavePreferences:
    save_preferences();
    break;
  case EffectKind::RefreshLibrary:
    refresh();
    view.notice = "Local library refreshed.";
    break;
  case EffectKind::RefreshCatalog: {
    auto o = options();
    start_task(
        "Refresh versions",
        [root, o](const auto &c) {
          return refresh_catalog(root, kPinnedMinecraftVersion, o, c).to_json();
        },
        true);
    break;
  }
  case EffectKind::InstallVersion: {
    auto o = options();
    auto v = e.version;
    start_task(
        "Install / repair " + v,
        [root, v, o](const auto &c) {
          return prepare_install(root, v, o, c).to_json();
        },
        true);
    break;
  }
  case EffectKind::VerifyVersion: {
    auto o = options();
    auto v = e.version;
    start_task(
        "Verify " + v,
        [root, v, o](const auto &c) {
          return verify_install(root, v, o, c).to_json();
        },
        false);
    break;
  }
  case EffectKind::CreateInstance:
  case EffectKind::SaveInstance: {
    auto d = e.draft;
    auto o = options();
    bool create = e.kind == EffectKind::CreateInstance;
    auto runtime = root_;
    bool prism =
        exists(root + "/meta/net.minecraft/" + d.version + ".json") ||
        !exists(root + "/versions/" + d.version + "/" + d.version + ".json");
    start_task(
        create ? "Create instance" : "Update instance",
        [root, runtime, d, o, create, prism](const auto &c) {
          bool need =
              create || load_instance(runtime, d.id).version != d.version;
          if (prism && need) {
            auto r = verify_install(root, d.version, o, c);
            if (r.cancelled)
              return r.to_json();
            if (!r.ok) {
              r = prepare_install(root, d.version, o, c);
              if (!r.ok)
                return r.to_json();
            }
          }
          if (c.cancelled && c.cancelled())
            throw std::runtime_error("Cancelled before updating profile");
          Instance i = d;
          if (create)
            i = create_instance(runtime, root, d.name, d.version, d.heap_mib);
          else {
            auto old = load_instance(runtime, d.id);
            if (old.version != d.version)
              update_instance_version(runtime, root, d.id, d.version);
            save_instance(runtime, d);
          }
          return Json{
              {"ok", true}, {"status", "profile_saved"}, {"instance_id", i.id}};
        },
        prism);
    break;
  }
  case EffectKind::CheckInstance:
    check_instance(e.instance_id);
    break;
  case EffectKind::DuplicateInstance: {
    auto i = load_instance(root_, e.instance_id);
    auto c = duplicate_instance(root_, root, i.id, i.name + " copy");
    refresh();
    view.page = Page::Instances;
    view.notice = "Duplicated settings; saves were not copied.";
    break;
  }
  case EffectKind::ArchiveInstance:
    archive_instance(root_, e.instance_id);
    refresh();
    view.page = Page::Instances;
    view.notice = "Instance archived. Restore it from Settings.";
    break;
  case EffectKind::RestoreInstance: {
    auto i = restore_instance(root_, e.value);
    refresh();
    view.page = Page::Instances;
    view.notice = "Instance restored as " + i.name;
    break;
  }
  case EffectKind::ImportInstance: {
    auto src = view.import_path;
    if (src.empty())
      throw std::runtime_error("Choose a Prism instance folder first");
    auto runtime = root_;
    start_task(
        "Import instance",
        [root, runtime, src](const auto &c) {
          ImportOptions o;
          o.should_cancel = [&](size_t n, size_t b) {
            if (c.progress &&
                !c.progress({b, 0, "Copying " + std::to_string(n) + " files"}))
              return true;
            return c.cancelled && c.cancelled();
          };
          auto i = import_instance(runtime, root, src, o);
          return Json{{"ok", true},
                      {"status", "profile_imported"},
                      {"instance_id", i.id}};
        },
        false);
    break;
  }
  case EffectKind::OpenDiagnostic: {
    const char *n[] = {"switch-diagnostics", "vulkan-present",
                       "java25-test",        "switchcraft-java25",
                       "ffi-test",           "zero-services-test",
                       "java-test"};
    if (e.row < 7)
      chain = n[e.row];
    break;
  }
  case EffectKind::OpenLog: {
    view.log.clear();
    std::ifstream i(logs_ + "/minecraft-launcher.log");
    std::string l;
    while (std::getline(i, l)) {
      view.log.push_back(l);
      if (view.log.size() > 30)
        view.log.erase(view.log.begin());
    }
    break;
  }
  case EffectKind::ExportPlan:
    save_json_atomic(logs_ + "/launch-plan.json", view.plan);
    view.notice = "Report exported to launch-plan.json.";
    break;
  case EffectKind::CancelTask:
    job.cancel();
    view.notice = "Cancelling safely...";
    break;
  case EffectKind::Close:
    if (view.transfer.active) {
      job.cancel();
      exit_when_idle = true;
    } else
      close_requested = true;
    break;
  }
}
void LauncherSession::input(Input i, int row) {
  if (i == Input::Close && view.transfer.active)
    exit_when_idle = true;
  try {
    for (const auto &e : transition(view, controller, i, row))
      handle(e);
  } catch (const std::exception &e) {
    view.notice = e.what();
    log(std::string("Launcher action: ") + e.what());
  }
}
bool LauncherSession::poll() {
  job.reap();
  auto s = job.snapshot();
  if (!s.running && (!s.complete || task_seen_))
    return false;
  bool changed = s.running || (s.complete && !task_seen_);
  if (s.running && !s.message.empty() && s.message != last_progress_) {
    last_progress_ = s.message;
    log("Task progress: " + s.message + " bytes=" + std::to_string(s.bytes) +
        "/" + std::to_string(s.total));
  }
  view.transfer = {s.title,   s.message,        s.error,    s.bytes,    s.total,
                   s.running, !s.error.empty(), s.complete, s.cancelled};
  if (s.complete && !task_seen_) {
    task_seen_ = true;
    transition(view, controller, Input::TaskFinished);
    bool ok =
        s.error.empty() && s.result.is_object() && s.result.value("ok", false);
    view.transfer.failed = !ok && !s.cancelled;
    if (!ok && view.transfer.error.empty())
      view.transfer.error =
          s.result.is_object()
              ? s.result.value("status", std::string("Task failed"))
              : std::string("Task failed");
    if (s.result.is_object() && s.result.contains("details") &&
        s.result["details"].contains("error"))
      view.transfer.error = s.result["details"]["error"].get<std::string>();
    Json report = {{"title", s.title},
                   {"cancelled", s.cancelled},
                   {"error", s.error},
                   {"result", s.result}};
    save_json_atomic(logs_ + "/launcher-task-report.json", report);
    log("Task finished: " + s.title + " ok=" + std::to_string(ok) +
        " cancelled=" + std::to_string(s.cancelled) +
        " error=" + view.transfer.error);
    refresh();
    if (s.result.contains("instance_id") && ok) {
      auto id = s.result["instance_id"].get<std::string>();
      for (unsigned n = 0; n < view.instances.size(); n++)
        if (view.instances[n].id == id) {
          view.selected_instance = n;
          break;
        }
    }
  }
  if (exit_when_idle && !view.transfer.active)
    close_requested = true;
  return changed;
}
void LauncherSession::finish() {
  job.cancel();
  job.wait();
  shutdown_download_transport();
  if (network_ready) {
    if (services_.network_end)
      services_.network_end();
    network_ready = false;
  }
}
} // namespace sc::ui
