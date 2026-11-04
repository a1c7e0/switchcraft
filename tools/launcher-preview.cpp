// Host rendering of the same UI code as the NRO. This is not a device capture.
#include "launcher_ui.hpp"
#include <fstream>
#include <iostream>
#include <iterator>
int main(int argc,char **argv){
    if(argc<3){std::cerr<<"Usage: launcher-preview FONT.ttf OUTPUT.ppm [instances|details|settings|empty|versions] [dark]\n";return 2;}
    std::ifstream font(argv[1],std::ios::binary);std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(font)),{});
    std::vector<uint32_t> pixels(1280*720);sc::ui::Canvas c(1280,720,1280,pixels.data());
    if(!c.set_font(bytes.data(),bytes.size())){std::cerr<<"Cannot read preview font\n";return 1;}
    sc::ui::LauncherView v;v.preview=true;v.shared_root="sdmc:/minecraft/.minecraft";v.dark=argc>4&&std::string(argv[4])=="dark";
    // Original display fixtures, not actual instances or evidence of game execution.
    v.instances={{"vanilla","Vanilla","26.4-snapshot-6",512},{"creative","Creative","26.4-snapshot-6",768},{"testing","Testing","26.4-snapshot-6",256}};
    v.versions={{"26.4-snapshot-6","snapshot",true},{"1.21.1","release",false}};
    std::string page=argc>3?argv[3]:"instances";
    if(page=="details")v.page=sc::ui::Page::Details;
    if(page=="settings"){v.page=sc::ui::Page::Settings;v.cursor=2;}
    if(page=="empty")v.instances.clear();
    if(page=="versions")v.page=sc::ui::Page::Versions;
    sc::ui::draw_launcher(c,v);
    std::ofstream out(argv[2],std::ios::binary);out<<"P6\n1280 720\n255\n";
    for(auto p:pixels){char rgb[]={char(p&255),char((p>>8)&255),char((p>>16)&255)};out.write(rgb,3);}return out?0:1;
}
