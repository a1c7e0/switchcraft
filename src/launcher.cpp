#include "platform.h"
#include "launcher_ui.hpp"
#include "prism_metadata.hpp"
#include <javaswitch/runtime.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <fstream>
#include <set>
int sc_launcher_console();
namespace {
using namespace sc;
using namespace sc::ui;
constexpr int W=1280,H=720;
bool primary(Page p){return p<=Page::Diagnostics;}
std::string keyboard(const std::string &heading,const std::string &initial,unsigned limit){
    SwkbdConfig k{};Result rc=swkbdCreate(&k,0);
    if(R_FAILED(rc))throw std::runtime_error("System keyboard unavailable: "+std::to_string(rc));
    swkbdConfigMakePresetDefault(&k);swkbdConfigSetHeaderText(&k,heading.c_str());
    swkbdConfigSetInitialText(&k,initial.c_str());swkbdConfigSetStringLenMax(&k,limit);
    char value[1024]{};rc=swkbdShow(&k,value,sizeof(value));swkbdClose(&k);
    return R_SUCCEEDED(rc)?std::string(value):initial;
}
void refresh(LauncherView &v){
    std::vector<std::string> errors;v.instances=scan_instances(SC_ROOT,&errors);
    v.versions.clear();std::set<std::string> installed;
    for(const auto &id:scan_versions(v.shared_root)){installed.insert(id);v.versions.push_back({id,"local",true});}
    if(file_exists(v.shared_root+"/meta/net.minecraft/index.json")){
        try{for(const auto &entry:load_prism_versions(v.shared_root,"net.minecraft"))
            if(!installed.count(entry.version))v.versions.push_back({entry.version,entry.type,false,file_exists(v.shared_root+"/meta/net.minecraft/"+entry.version+".json")});}
        catch(const std::exception &e){errors.push_back(e.what());}
    }
    if(!errors.empty()){v.notice="Some profiles could not be read. See the launcher log.";for(const auto &e:errors)sc_log("Library scan: %s\n",e.c_str());}
    v.cursor=0;if(v.selected_instance>=v.instances.size())v.selected_instance=0;
}
void load_preferences(LauncherView &v,Config &config,bool &valid){
    try{config=load_config(SC_ROOT "/config/launcher.json");}
    catch(const std::exception &e){valid=false;v.notice="Existing configuration could not be read; it will be preserved.";sc_log("Configuration: %s\n",e.what());}
    v.shared_root=config.root;v.default_heap=std::max(128u,config.heap_mib);config.graphics="nvk";config.runtime="openjdk25";
    if(R_SUCCEEDED(setsysInitialize())){ColorSetId theme{};if(R_SUCCEEDED(setsysGetColorSetId(&theme)))v.dark=theme==ColorSetId_Dark;setsysExit();}
    if(file_exists(SC_ROOT "/config/launcher-ui.json")){
        try{v.dark=read_json(SC_ROOT "/config/launcher-ui.json").value("dark",v.dark);}
        catch(const std::exception &e){valid=false;sc_log("UI configuration preserved: %s\n",e.what());}
    }
}
void save_preferences(LauncherView &v,Config &config,bool valid){
    if(!valid)throw std::runtime_error("Repair the existing configuration on SD before saving.");
    config.root=v.shared_root;config.heap_mib=v.default_heap;save_config(SC_ROOT "/config/launcher.json",config);
    std::string path=SC_ROOT "/config/launcher-ui.json",tmp=path+".tmp";
    std::ofstream out(tmp);if(!out)throw std::runtime_error("Cannot write UI preferences");
    out<<Json{{"schema_version",1},{"dark",v.dark}}.dump(2)<<'\n';out.close();
    if(!out||std::rename(tmp.c_str(),path.c_str())!=0)throw std::runtime_error("Cannot commit UI preferences");
    v.notice="Preferences saved.";sc_log("Launcher preferences saved\n");
}
void begin_create(LauncherView &v){
    if(v.versions.empty()){v.notice="Add an installed version or import Prism metadata first.";return;}
    size_t n=v.page==Page::Versions?std::min<size_t>(v.cursor,v.versions.size()-1):0;
    if(v.page!=Page::Versions){
        auto it=std::find_if(v.versions.begin(),v.versions.end(),[](const auto &r){return r.id=="26.4-snapshot-6"&&(r.installed||r.cached);});
        if(it!=v.versions.end())n=it-v.versions.begin();
    }
    if(!v.versions[n].installed&&!v.versions[n].cached){v.notice="Download this version's Prism metadata with the PC helper first.";return;}
    v.draft={"","New instance",v.versions[n].id,v.default_heap};v.page=Page::Create;v.cursor=0;
}
void step_setting(LauncherView &v,int direction){
    if(v.page==Page::Settings&&v.cursor==1)v.default_heap=std::clamp(int(v.default_heap)+direction*128,128,1024);
    if(v.page==Page::Settings&&v.cursor==2)v.dark=!v.dark;
    if((v.page==Page::Edit||v.page==Page::Create)&&v.cursor==2)v.draft.heap_mib=std::clamp(int(v.draft.heap_mib)+direction*128,128,1024);
    if((v.page==Page::Edit||v.page==Page::Create)&&v.cursor==1&&!v.versions.empty()){
        auto it=std::find_if(v.versions.begin(),v.versions.end(),[&](const auto &r){return r.id==v.draft.version;});
        int n=it==v.versions.end()?0:int(it-v.versions.begin());
        for(size_t attempt=0;attempt<v.versions.size();attempt++){
            n=(n+int(v.versions.size())+direction)%v.versions.size();
            if(v.versions[n].installed||v.versions[n].cached){v.draft.version=v.versions[n].id;break;}
        }
    }
}
void select(LauncherView &v,Config &config,bool valid,std::string &chain){
    switch(v.page){
    case Page::Instances:
        if(v.instances.empty()){begin_create(v);break;}
        v.selected_instance=std::min<size_t>(v.cursor,v.instances.size()-1);v.page=Page::Details;v.cursor=0;break;
    case Page::Versions:begin_create(v);break;
    case Page::Details:{
        if(v.selected_instance>=v.instances.size())break;
        Instance instance=v.instances[v.selected_instance];
        if(v.cursor==0||v.cursor==3){
            v.plan=make_instance_plan(instance,v.shared_root,SC_ROOT);v.page=Page::Plan;v.cursor=0;
            JsRuntimeInfo info{};js_runtime_query("openjdk25",&info);
            sc_log("Instance readiness id=%s version=%s missing=%zu runtime-linked=%d; game invocation disabled\n",instance.id.c_str(),instance.version.c_str(),v.plan["missing_files"].size(),info.available);
        }else if(v.cursor==1){v.draft=instance;v.page=Page::Edit;v.cursor=0;}
        else if(v.cursor==2){auto copy=duplicate_instance(SC_ROOT,v.shared_root,instance.id,instance.name+" copy");refresh(v);v.page=Page::Instances;v.notice="Duplicated settings. Saves and game files were not copied.";sc_log("Created settings-only duplicate %s\n",copy.id.c_str());}
        break;}
    case Page::Create:case Page::Edit:
        if(v.cursor==0)v.draft.name=keyboard("Instance name",v.draft.name,48);
        else if(v.cursor==1||v.cursor==2)step_setting(v,1);
        else{if(v.page==Page::Create){auto i=create_instance(SC_ROOT,v.shared_root,v.draft.name,v.draft.version,v.draft.heap_mib);sc_log("Created instance %s from %s\n",i.id.c_str(),i.version.c_str());}
            else{save_instance(SC_ROOT,v.draft);sc_log("Saved instance %s\n",v.draft.id.c_str());}
            refresh(v);v.page=Page::Instances;v.notice="Instance saved.";}break;
    case Page::Settings:
        if(v.cursor==0){std::string path=keyboard("Shared Minecraft installation",v.shared_root,240);
            if(path.empty()||path.find("..")!=path.npos||path.find_first_of("\r\n\t")!=path.npos)throw std::runtime_error("Invalid installation folder");
            v.shared_root=path;refresh(v);v.notice="Folder changed in memory. Select Save preferences to keep it.";}
        else if(v.cursor==1||v.cursor==2)step_setting(v,1);
        else if(v.cursor==3)save_preferences(v,config,valid);
        else{refresh(v);v.notice="Library refreshed.";}break;
    case Page::Diagnostics:{const char *names[]={"switch-diagnostics","vulkan-present","java25-test","switchcraft-java25","ffi-test","zero-services-test","java-test"};
        if(v.cursor<7)chain=names[v.cursor];else{v.log.clear();std::ifstream in(SC_LOGS "/minecraft-launcher.log");std::string line;
            while(std::getline(in,line)){v.log.push_back(line);if(v.log.size()>30)v.log.erase(v.log.begin());}v.page=Page::Log;v.cursor=0;}break;}
    case Page::Plan:{std::ofstream out(SC_LOGS "/launch-plan.json");out<<v.plan.dump(2)<<'\n';out.close();if(!out)throw std::runtime_error("Cannot export installation report");v.notice="Report saved to launch-plan.json.";sc_log("Instance launch plan exported; game not invoked\n");break;}
    case Page::Log:break;
    }
}
}
int main(){
    sc_init("minecraft-launcher");sc_mkdirs(SC_ROOT "/config");
    Result rc=plInitialize(PlServiceType_User);PlFontData font{};bool pl_ready=R_SUCCEEDED(rc);
    if(pl_ready)rc=plGetSharedFontByType(&font,PlSharedFontType_Standard);
    if(R_FAILED(rc)){sc_log("Shared font unavailable Result=0x%x; using console\n",rc);if(pl_ready)plExit();sc_exit();return sc_launcher_console();}
    std::vector<uint32_t> pixels(W*H);sc::ui::Canvas canvas(W,H,W,pixels.data());
    if(!canvas.set_font(static_cast<const uint8_t*>(font.address),font.size)){plExit();sc_exit();return sc_launcher_console();}
    sc_console(false);Framebuffer fb{};rc=framebufferCreate(&fb,nwindowGetDefault(),W,H,PIXEL_FORMAT_RGBA_8888,2);
    bool fb_ready=R_SUCCEEDED(rc);if(fb_ready)rc=framebufferMakeLinear(&fb);
    if(R_FAILED(rc)){if(fb_ready)framebufferClose(&fb);canvas.clear_font();plExit();sc_console(true);sc_log("Launcher framebuffer Result=0x%x; using console\n",rc);sc_exit();return sc_launcher_console();}
    hidInitializeTouchScreen();LauncherView view;Config config;bool valid=true;std::string chain;
    try{load_preferences(view,config,valid);refresh(view);}catch(const std::exception &e){view.notice=e.what();sc_log("Launcher startup: %s\n",e.what());}
    bool dirty=true,touched=false,close_requested=false;u64 keys=0,last_dir=0;uint64_t repeat_at=0;int minute=-1;
    while(sc_frame(&keys)){
        auto now=std::time(nullptr);std::tm *clock=std::localtime(&now);
        if(clock&&clock->tm_min!=minute){char text[16];std::strftime(text,sizeof(text),"%H:%M",clock);view.clock=text;minute=clock->tm_min;dirty=true;}
        uint64_t ms=armTicksToNs(armGetSystemTick())/1000000;
        u64 direction=sc_buttons_held()&(HidNpadButton_AnyUp|HidNpadButton_AnyDown|HidNpadButton_AnyLeft|HidNpadButton_AnyRight);
        if(direction!=last_dir){repeat_at=ms+400;last_dir=direction;}else if(direction&&ms>=repeat_at){keys|=direction;repeat_at=ms+110;}
        try{
            if(keys)dirty=true;
            if(primary(view.page)&&(keys&(HidNpadButton_L|HidNpadButton_R))){int n=int(view.page)+((keys&HidNpadButton_R)?1:-1);view.page=Page((n+4)%4);view.cursor=0;view.notice.clear();}
            if(keys&HidNpadButton_B){view.page=primary(view.page)?Page::Instances:(view.page==Page::Log?Page::Diagnostics:Page::Instances);view.cursor=0;view.notice.clear();}
            unsigned count=launcher_row_count(view);
            if(count){
                if(view.page==Page::Instances){
                    if((keys&HidNpadButton_AnyDown)&&view.cursor+3<count)view.cursor+=3;
                    if((keys&HidNpadButton_AnyUp)&&view.cursor>=3)view.cursor-=3;
                    if((keys&HidNpadButton_AnyRight)&&view.cursor%3<2&&view.cursor+1<count)view.cursor++;
                    if((keys&HidNpadButton_AnyLeft)&&view.cursor%3>0)view.cursor--;
                }else{
                    if(keys&HidNpadButton_AnyDown)view.cursor=(view.cursor+1)%count;
                    if(keys&HidNpadButton_AnyUp)view.cursor=(view.cursor+count-1)%count;
                    if(keys&HidNpadButton_AnyRight)step_setting(view,1);
                    if(keys&HidNpadButton_AnyLeft)step_setting(view,-1);
                }
            }
            if((keys&HidNpadButton_X)&&(view.page==Page::Instances||view.page==Page::Versions))begin_create(view);
            if(keys&HidNpadButton_A)select(view,config,valid,chain);
            HidTouchScreenState touch{};hidGetTouchScreenStates(&touch,1);
            if(touch.count&&!touched){int hit=launcher_hit(view,touch.touches[0].x,touch.touches[0].y);if(hit<=-10&&hit>=-13){view.page=Page(-10-hit);view.cursor=0;}
                else if(hit==-20){view.page=Page::Instances;view.cursor=0;view.notice.clear();}
                else if(hit==-21)select(view,config,valid,chain);
                else if(hit==-22)begin_create(view);
                else if(hit==-23)close_requested=true;
                else if(hit>=0){if(view.cursor==unsigned(hit))select(view,config,valid,chain);else view.cursor=hit;}
                dirty=true;}
            touched=touch.count!=0;
        }catch(const std::exception &e){view.notice=e.what();sc_log("Launcher action: %s\n",e.what());dirty=true;}
        if(close_requested)break;
        if(!chain.empty()){
            if(sc_chain(chain.c_str()))break;
            chain.clear();view.notice="Diagnostic could not be opened. See the launcher log.";dirty=true;
        }
        if(dirty){draw_launcher(canvas,view);dirty=false;}
        u32 stride=0;void *out=framebufferBegin(&fb,&stride);
        if(out){for(int y=0;y<H;y++)std::memcpy(static_cast<uint8_t*>(out)+y*stride,pixels.data()+y*W,W*sizeof(uint32_t));}
        framebufferEnd(&fb);
    }
    framebufferClose(&fb);canvas.clear_font();plExit();
    sc_exit();return 0;
}
