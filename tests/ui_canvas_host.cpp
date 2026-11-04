#include "launcher_ui.hpp"
#include <cassert>
int main(){
 constexpr unsigned guard=0x12345678;std::vector<uint32_t> pixels(10*8+32,guard);
 sc::ui::Canvas canvas(8,8,10,pixels.data()+16);canvas.clear({10,20,30});
 canvas.fill_rect(-5,-5,10,10,{255,0,0,128});canvas.circle(7,7,5,{1,2,3});
 canvas.line(-20,-20,30,30,{255,255,255});canvas.outline_rect(-3,-3,15,15,{0,255,0},2);
 for(unsigned i=0;i<16;i++){assert(pixels[i]==guard);assert(pixels[pixels.size()-1-i]==guard);}
 for(unsigned y=0;y<8;y++)assert(pixels[16+y*10+8]==guard&&pixels[16+y*10+9]==guard);
 assert(!canvas.set_font(nullptr,0));
 sc::ui::LauncherView view;view.instances={{"a","A","v",512},{"b","B","v",512}};
 assert(sc::ui::launcher_hit(view,300,200)==0);assert(sc::ui::launcher_hit(view,610,200)==1);
 assert(sc::ui::launcher_hit(view,590,200)==-1);assert(sc::ui::launcher_hit(view,280,355)==-1);
 assert(sc::ui::launcher_hit(view,50,150)==-10);assert(sc::ui::launcher_hit(view,50,690)==-20);
 assert(sc::ui::launcher_hit(view,1020,690)==-23);
 view.instances.clear();assert(sc::ui::launcher_hit(view,650,480)==-22);
}
