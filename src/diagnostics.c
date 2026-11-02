#include "platform.h"
#include <stdio.h>

int main(void) {
    sc_init("switch-diagnostics");
    const char *items[]={"Memory report and bounded allocation", "SD filesystem roundtrip",
        "Thread create/join", "OpenGL context and triangle (separate NRO)",
        "Experimental Vulkan GPU tests (separate NRO)", "Minecraft installation inspector"};
    int selected=0; bool redraw=true; u64 keys;
    while(sc_frame(&keys)) {
        if(keys&HidNpadButton_Down){selected=(selected+1)%6;redraw=true;}
        if(keys&HidNpadButton_Up){selected=(selected+5)%6;redraw=true;}
        if(redraw){
            consoleClear();
            printf("SWITCHCRAFT DIAGNOSTICS 0.1.0\n\n");
            printf("Use application-mode hbmenu for full memory.\nHardware verification: NOT TESTED\n\n");
            for(int i=0;i<6;i++)printf("%s %s\n",selected==i?">":" ",items[i]);
            printf("\nD-pad: select | A: run | +: exit\nLogs: " SC_LOGS "/switch-diagnostics.log\n\n");
            redraw=false;
        }
        if(keys&HidNpadButton_A) {
            if(selected==0)sc_memory();
            if(selected==1)sc_fs_test();
            if(selected==2)sc_thread_test();
            if(selected>=3&&sc_chain(selected==3?"opengl-test":selected==4?"vulkan-test":"minecraft-launcher"))break;
        }
    }
    sc_exit(); return 0;
}
