#include "platform.h"
#include "metadata.hpp"
#include <algorithm>
#include <fstream>
#include <cstdio>
#include <javaswitch/runtime.h>

int sc_launcher_console() {
    sc_init("minecraft-launcher");
    sc_mkdirs(SC_ROOT "/config");
    sc::Config config;std::string message;bool config_valid=true;
    try {config=sc::load_config(SC_ROOT "/config/launcher.json");}
    catch(const std::exception &e){message=e.what();config_valid=false;}
    if(config.graphics!="nvk")message+=" Legacy graphics setting migrated in memory to Vulkan; X saves.";
    config.graphics="nvk";config.runtime="openjdk25";
    JsRuntimeInfo runtime_info{};js_runtime_query("openjdk25",&runtime_info);
    auto versions=sc::scan_versions(config.root);
    unsigned selected=0;
    auto it=std::find(versions.begin(),versions.end(),config.version);
    if(it!=versions.end())selected=it-versions.begin();
    bool redraw=true;u64 keys;
    while(sc_frame(&keys)) {
        if(!versions.empty()) {
            if(keys&HidNpadButton_Down){selected=(selected+1)%versions.size();redraw=true;}
            if(keys&HidNpadButton_Up){selected=(selected+versions.size()-1)%versions.size();redraw=true;}
            config.version=versions[selected];
        }
        if(redraw) {
            consoleClear();
            printf("SWITCHCRAFT VULKAN / 26.4-SNAPSHOT-6\n\nRoot: %s\n",config.root.c_str());
            printf("Installed version JSONs: %u\n",(unsigned)versions.size());
            if(versions.empty())printf("No versions found. Import your legitimate PC installation.\n");
            else {unsigned start=selected>3?selected-3:0;for(unsigned i=start;i<versions.size()&&i<start+7;i++)printf("%s %s\n",i==selected?">":" ",versions[i].c_str());}
            printf("\nRuntime: %s [%s]\nGraphics: %s [%s]\nHeap setting: %u MiB [planning only]\n",
                config.runtime.c_str(),runtime_info.available?"VM symbol linked; integration still experimental":"Java 25 VM not linked",
                config.graphics.c_str(),"SDL3 / NVK; hardware untested",config.heap_mib);
            printf("\nD-pad: inspect version | A: export Vulkan launch plan\nL: check Java 25 backend | R: Vulkan profile/presentation\nX: save settings | Y: diagnostics | -: recent log | +: exit\n\n");
            printf("%s\n",message.c_str());redraw=false;
        }
        try {
            if(keys&HidNpadButton_L){
                JsLaunchRequest request{};request.abi_version=JS_ABI_VERSION;request.required_java_major=25;
                request.backend="openjdk25";request.classpath="";request.main_class="net/minecraft/client/main/Main";request.heap_mib=config.heap_mib;
                if(!runtime_info.available){JsLaunchResult result{};int rc=js_runtime_launch(&request,&result);sc_log("Java 25 launch gate: code=%d stage=%s; no game code invoked\n",rc,result.stage);}
                else sc_log("Java 25 VM symbol linked. Complete native/installation validation before enabling game launch.\n");
            }
            if(keys&HidNpadButton_A) {
                if(versions.empty())sc_log("No installed version to inspect\n");
                else {
                    auto plan=sc::make_plan(config,SC_ROOT);
                    std::ofstream out(SC_LOGS "/launch-plan.json");out<<plan.dump(2)<<'\n';out.close();
                    sc_log("Version=%s Java=%d CP entries=%u missing=%u native replacements=%u\n",config.version.c_str(),plan["java_major"].get<int>(),
                        (unsigned)plan["classpath"].size(),(unsigned)plan["missing_files"].size(),(unsigned)plan["native_substitutions"].size());
                    for(const auto &reason:plan["blockers"])sc_log("BLOCKED: %s\n",reason.get<std::string>().c_str());
                    sc_log("Plan export: %s\n",out?SC_LOGS "/launch-plan.json":"FAILED writing SD");
                }
            }
            if(keys&HidNpadButton_X) {
                if(!config_valid)sc_log("Existing malformed config preserved; repair it on the SD card first\n");
                else {sc::save_config(SC_ROOT "/config/launcher.json",config);sc_log("Settings saved\n");}
            }
            if(keys&HidNpadButton_Minus) {
                std::ifstream in(SC_LOGS "/minecraft-launcher.log");std::string line;std::vector<std::string> tail;
                while(std::getline(in,line)){tail.push_back(line);if(tail.size()>16)tail.erase(tail.begin());}
                consoleClear();for(const auto &s:tail)printf("%s\n",s.c_str());
                printf("\nUse D-pad/L/R to restore menu; + exits\n");
            }
        }catch(const std::exception &e){sc_log("Metadata/config error: %s\n",e.what());}
        if((keys&HidNpadButton_R)&&sc_chain("vulkan-present"))break;
        if((keys&HidNpadButton_Y)&&sc_chain("switch-diagnostics"))break;
    }
    sc_exit();return 0;
}
