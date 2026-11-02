#include "platform.h"
#include "metadata.hpp"
#include <algorithm>
#include <fstream>
#include <cstdio>

int main() {
    sc_init("minecraft-launcher");
    sc_mkdirs(SC_ROOT "/config");
    sc::Config config;std::string message;bool config_valid=true;
    try {config=sc::load_config(SC_ROOT "/config/launcher.json");}
    catch(const std::exception &e){message=e.what();config_valid=false;}
    auto versions=sc::scan_versions(config.root);
    unsigned selected=0;
    auto it=std::find(versions.begin(),versions.end(),config.version);
    if(it!=versions.end())selected=it-versions.begin();
    const char *runtimes[]={"diagnostic","minijvm","openjdk8","openjdk21","openjdk25","aot"};
    const char *backends[]={"nvc0","nvk","zink"};
    bool redraw=true;u64 keys;
    while(sc_frame(&keys)) {
        if(!versions.empty()) {
            if(keys&HidNpadButton_Down){selected=(selected+1)%versions.size();redraw=true;}
            if(keys&HidNpadButton_Up){selected=(selected+versions.size()-1)%versions.size();redraw=true;}
            config.version=versions[selected];
        }
        if(keys&HidNpadButton_L){for(unsigned i=0;i<6;i++)if(config.runtime==runtimes[i]){config.runtime=runtimes[(i+1)%6];break;}redraw=true;}
        if(keys&HidNpadButton_R){for(unsigned i=0;i<3;i++)if(config.graphics==backends[i]){config.graphics=backends[(i+1)%3];break;}redraw=true;}
        if(redraw) {
            consoleClear();
            printf("SWITCHCRAFT INSTALLATION INSPECTOR 0.1.0\n\nRoot: %s\n",config.root.c_str());
            printf("Installed version JSONs: %u\n",(unsigned)versions.size());
            if(versions.empty())printf("No versions found. Import your legitimate PC installation.\n");
            else {unsigned start=selected>3?selected-3:0;for(unsigned i=start;i<versions.size()&&i<start+7;i++)printf("%s %s\n",i==selected?">":" ",versions[i].c_str());}
            printf("\nRuntime: %s [%s]\nGraphics: %s [%s]\nHeap setting: %u MiB [planning only]\n",
                config.runtime.c_str(),config.runtime=="minijvm"?"separate diagnostic; no Minecraft integration":"no game runtime linked",
                config.graphics.c_str(),config.graphics=="zink"?"not implemented":"experimental / hardware untested",config.heap_mib);
            printf("\nD-pad: version | L: runtime | R: graphics\nA: inspect/export launch plan | X: save settings\nY: diagnostics | -: show recent launcher log | +: exit\n\n");
            printf("%s\n",message.c_str());redraw=false;
        }
        try {
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
        if((keys&HidNpadButton_Y)&&sc_chain("switch-diagnostics"))break;
    }
    sc_exit();return 0;
}
