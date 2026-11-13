#include <switchcraft/java25_menu.h>

#include <assert.h>
#include <string.h>

int main(void) {
    char text[768];
    int size = sc_java25_menu_format(text, sizeof(text), "e2b9a77");
    assert(size > 0 && (size_t)size < sizeof(text));
    assert(strstr(text, "SWITCHCRAFT JAVA25 DIAGNOSTICS\n"));
    assert(strstr(text, "Source: e2b9a77 | Hardware: NOT TESTED"));
    assert(strstr(text, "A: Hello"));
    assert(strstr(text, "X: JNI/FFM SDL"));
    assert(strstr(text, "Y: LWJGL JNI/SDL/Vulkan"));
    assert(strstr(text, "B: SDL/Vulkan + VMA"));
    assert(strstr(text, "R: FreeType/OpenAL loopback"));
    assert(strstr(text, "L: STB + shader tools"));
    assert(strstr(text, "+: exit without starting a VM"));
    assert(strstr(text, "separate fresh processes"));
    assert(sc_java25_menu_format(NULL, sizeof(text), "rev") < 0);
    assert(sc_java25_menu_format(text, 0, "rev") < 0);
    struct { char prefix; char text[12]; char suffix; } small = { 'L', {0}, 'R' };
    size = sc_java25_menu_format(small.text, sizeof(small.text), "long revision");
    assert(size >= (int)sizeof(small.text));
    assert(small.text[sizeof(small.text)-1] == '\0');
    assert(small.prefix == 'L' && small.suffix == 'R');
    return 0;
}
