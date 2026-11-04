#include "launcher_ui.hpp"
#include <algorithm>
namespace sc::ui {
namespace {
struct Theme { Color bg, surface, ink, muted, line, accent, selected; };
Theme theme(bool dark) {
    return dark?Theme{{35,36,39},{49,51,55},{245,246,247},{173,178,186},{75,78,83},{54,222,211},{36,76,78}}:
                Theme{{238,239,241},{255,255,255},{39,44,50},{104,111,121},{207,211,217},{0,155,151},{221,246,244}};
}
std::string title(Page p) {
    switch(p){case Page::Instances:return "Instances";case Page::Versions:return "Versions";case Page::Settings:return "Settings";
    case Page::Diagnostics:return "Diagnostics";case Page::Details:return "Instance";case Page::Edit:return "Edit instance";
    case Page::Create:return "New instance";case Page::Plan:return "Installation check";case Page::Log:return "Launcher log";}
    return {};
}
void block_icon(Canvas &c,int x,int y,int size,Color accent) {
    c.rounded_rect(x,y,size,size,16,accent);
    int u=size/5;
    c.fill_rect(x+u,y+u*2,u*3,u*2,{255,255,255,225});
    c.fill_rect(x+u,y+u,u*3,u,{255,255,255,115});
    c.line(x+u*2,y+u*2,x+u*2,y+u*4,accent,2);
    c.line(x+u*3,y+u*2,x+u*3,y+u*4,accent,2);
}
void button(Canvas &c,int x,int y,const std::string &key,const std::string &label,Theme t) {
    c.circle(x+13,y+13,13,t.ink);
    c.text(x+6,y+3,key,18,t.bg,18);
    c.text(x+34,y,label,23,t.ink);
}
bool home(Page p){return p==Page::Instances||p==Page::Versions||p==Page::Settings||p==Page::Diagnostics;}
void row(Canvas &c,int y,const std::string &name,const std::string &value,bool selected,Theme t,int x=280,int width=950) {
    if(selected){c.rounded_rect(x-10,y-4,width+10,65,8,t.selected);c.rounded_rect(x-10,y-4,width+10,65,8,t.accent,false,3);}
    c.text(x+14,y+9,name,25,t.ink,width/2);
    int w=c.measure_text(value,22);c.text(std::max(x+width/2,x+width-w-26),y+11,value,22,t.muted,width/2-16,true);
    c.line(x+14,y+62,x+width-10,y+62,t.line);
}
}
unsigned launcher_row_count(const LauncherView &v){
    switch(v.page){case Page::Instances:return v.instances.size();case Page::Versions:return v.versions.size();
    case Page::Settings:return 5;case Page::Diagnostics:return 8;case Page::Details:return 4;
    case Page::Edit:case Page::Create:return 4;default:return 0;}
}
void draw_launcher(Canvas &c,const LauncherView &v) {
    Theme t=theme(v.dark);c.clear(t.bg);
    c.circle(61,49,20,t.accent);c.text(49,35,"S",29,{255,255,255});
    c.text(98,26,"Switchcraft",34,t.ink);c.text(318,37,"Minecraft launcher",20,t.muted);
    c.text(1000,34,v.preview?"HOST UI PREVIEW":v.clock,22,t.muted,230,true);
    c.line(40,94,1240,94,t.line);
    if(home(v.page)){
        const char *tabs[]={"Instances","Versions","Settings","Diagnostics"};
        for(unsigned i=0;i<4;i++){
            int y=146+int(i)*76;bool on=unsigned(v.page)==i;
            if(on){c.rounded_rect(28,y-8,206,63,10,t.selected);c.fill_rect(28,y+3,4,40,t.accent);}
            c.text(53,y+6,tabs[i],26,on?t.accent:t.muted);
        }
        c.text(48,516,"L / R",20,t.muted);c.text(48,544,"Change section",18,t.muted);
        c.text(280,117,title(v.page),33,t.ink);
    }else{c.text(48,119,title(v.page),33,t.ink);}
    if(v.page==Page::Instances){
        c.text(1080,127,std::to_string(v.instances.size())+" profiles",20,t.muted);
        if(v.instances.empty()){
            block_icon(c,654,223,100,t.accent);c.text(512,359,"Your next world starts here",30,t.ink);
            c.text(486,408,"Create an instance from an installed or cached version.",21,t.muted);
            c.rounded_rect(617,466,185,52,8,t.accent);c.text(642,477,"X  New instance",22,{255,255,255});
        }else{
            unsigned start=(v.cursor/6)*6;
            for(unsigned n=start;n<v.instances.size()&&n<start+6;n++){
                unsigned local=n-start;int x=280+int(local%3)*320,y=179+int(local/3)*193;
                c.rounded_rect(x,y,300,173,10,t.surface);
                if(n==v.cursor)c.rounded_rect(x-4,y-4,308,181,12,t.accent,false,4);
                Color colors[]={{43,137,128},{91,118,173},{167,110,71},{132,105,172}};
                block_icon(c,x+18,y+17,54,colors[n%4]);
                c.text(x+18,y+88,v.instances[n].name,26,t.ink,264,true);
                c.text(x+18,y+124,v.instances[n].version,20,t.muted,264,true);
            }
        }
    }else if(v.page==Page::Versions){
        if(v.versions.empty()){c.text(300,219,"No versions found",30,t.ink);c.text(300,272,"Choose the shared installation folder in Settings.",22,t.muted);c.text(300,310,"Prism metadata can be imported using the PC helper.",22,t.muted);}
        unsigned start=v.cursor>2?v.cursor-2:0;
        for(unsigned n=start;n<v.versions.size()&&n<start+6;n++)row(c,178+int(n-start)*68,v.versions[n].id,v.versions[n].installed?"Installed metadata":(v.versions[n].cached?"Prism metadata cached":"Metadata not downloaded"),n==v.cursor,t);
    }else if(v.page==Page::Settings){
        row(c,178,"Shared installation",v.shared_root,v.cursor==0,t);
        row(c,246,"Default Java memory",std::to_string(v.default_heap)+" MiB",v.cursor==1,t);
        row(c,314,"Appearance",v.dark?"Basic dark":"Basic light",v.cursor==2,t);
        row(c,382,"Save preferences","A  Save",v.cursor==3,t);
        row(c,450,"Refresh library","A  Scan",v.cursor==4,t);
        c.text(295,553,"Game files stay shared. Each instance has its own saves and settings.",20,t.muted,900,true);
    }else if(v.page==Page::Diagnostics){
        const char *names[]={"System, SD and memory","Vulkan graphics","Java 25 diagnostic","Java and SDL diagnostic","Native FFI and memory","VM native services","Java 8 baseline","View launcher log"};
        unsigned start=v.cursor>3?v.cursor-3:0;
        for(unsigned n=start;n<8&&n<start+6;n++)row(c,178+int(n-start)*68,names[n],n==7?"Open log":"Open diagnostic",v.cursor==n,t);
    }else if(v.page==Page::Details&&v.selected_instance<v.instances.size()){
        const auto &i=v.instances[v.selected_instance];block_icon(c,48,185,114,t.accent);
        c.text(48,328,i.name,30,t.ink,380,true);c.text(48,376,i.version,22,t.muted,380,true);
        c.text(48,414,std::to_string(i.heap_mib)+" MiB Java memory",22,t.muted);
        c.text(48,475,"Separate saves and configuration",19,t.muted,380,true);
        row(c,190,"Check installation","Files and components",v.cursor==0,t,467,755);
        row(c,266,"Edit instance","Name, version, memory",v.cursor==1,t,467,755);
        row(c,342,"Duplicate settings","Creates an empty game folder",v.cursor==2,t,467,755);
        row(c,418,"Launch status","Runtime not ready",v.cursor==3,t,467,755);
        c.text(481,531,"Minecraft cannot launch on Horizon yet.",22,t.muted,720,true);
    }else if(v.page==Page::Edit||v.page==Page::Create){
        row(c,192,"Name",v.draft.name,v.cursor==0,t,60,1160);
        row(c,274,"Minecraft version",v.draft.version.empty()?"No version available":v.draft.version,v.cursor==1,t,60,1160);
        row(c,356,"Java memory",std::to_string(v.draft.heap_mib)+" MiB",v.cursor==2,t,60,1160);
        row(c,438,v.page==Page::Create?"Create instance":"Save changes","A  Confirm",v.cursor==3,t,60,1160);
        c.text(76,552,"Left / Right changes version or memory. A opens the system keyboard for a name.",21,t.muted,1120,true);
    }else if(v.page==Page::Plan){
        if(v.plan.is_object()){
            c.text(55,181,"Installation checked",29,t.ink);
            std::string counts=std::to_string(v.plan.value("missing_files",Json::array()).size())+" missing files  /  "+std::to_string(v.plan.value("blockers",Json::array()).size())+" launch requirements";
            c.text(55,226,counts,23,t.muted);
            auto reasons=v.plan.value("blockers",Json::array());int y=291;
            for(size_t n=0;n<reasons.size()&&n<6;n++,y+=43){c.circle(65,y+13,4,t.accent);c.text(84,y,reasons[n].get<std::string>(),21,t.ink,1110,true);}
            c.text(55,572,"A  Export complete report to the SD log folder",21,t.muted);
        }else c.text(55,198,"No installation report is available.",26,t.ink);
    }else if(v.page==Page::Log){
        size_t start=v.log.size()>13?v.log.size()-13:0;
        for(size_t n=start;n<v.log.size();n++)c.text(52,180+int(n-start)*30,v.log[n],18,t.ink,1170,true);
    }
    if(!v.notice.empty()){c.rounded_rect(40,603,1200,36,6,t.selected);c.text(53,610,v.notice,19,t.ink,1170,true);}
    c.line(40,654,1240,654,t.line);
    button(c,48,679,"B","Back",t);button(c,215,679,"A",v.page==Page::Plan?"Export report":"Select",t);
    if(v.page==Page::Instances||v.page==Page::Versions)button(c,466,679,"X","New instance",t);
    button(c,1014,679,"+","Close",t);
}
int launcher_hit(const LauncherView &v,int x,int y){
    if(y>=669&&y<717){if(x>=40&&x<185)return -20;if(x>=205&&x<440)return -21;if(x>=456&&x<730&&(v.page==Page::Instances||v.page==Page::Versions))return -22;if(x>=1000&&x<1230)return -23;}
    if(v.page==Page::Instances&&v.instances.empty()&&x>=617&&x<802&&y>=466&&y<518)return -22;
    if(home(v.page)&&x>=28&&x<235&&y>=138&&y<442){int tab=(y-138)/76;if(tab<4)return -10-tab;}
    if(v.page==Page::Instances){if(x<280||x>=1220||y<179||y>=545)return -1;if((x-280)%320>=300||(y-179)%193>=173)return -1;int col=(x-280)/320,row_=(y-179)/193;if(col>2||row_>1)return -1;int i=int(v.cursor/6)*6+row_*3+col;return i<int(v.instances.size())?i:-1;}
    if(v.page==Page::Versions||v.page==Page::Diagnostics){if(x<270||y<174||y>584)return -1;int start=v.page==Page::Versions?(v.cursor>2?int(v.cursor)-2:0):(v.cursor>3?int(v.cursor)-3:0);int i=start+(y-174)/68;return i<int(launcher_row_count(v))?i:-1;}
    if(v.page==Page::Settings&&x>270&&y>=174&&y<514)return (y-174)/68;
    if(v.page==Page::Details&&x>457&&y>=186&&y<494)return (y-186)/76;
    if((v.page==Page::Edit||v.page==Page::Create)&&x>50&&y>=188&&y<504)return (y-188)/82;
    return -1;
}
}
