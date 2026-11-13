#pragma once

#include <stddef.h>
#include <stdio.h>

/* Console-only startup menu text. This deliberately has no libnx dependency so
 * the visible labels and fresh-process instructions can be host-checked. */
static inline int sc_java25_menu_format(char *buffer, size_t capacity,
                                        const char *revision) {
    if (!buffer || capacity == 0) return -1;
    if (!revision || !*revision) revision = "unknown";
    return snprintf(buffer, capacity,
        "SWITCHCRAFT JAVA25 DIAGNOSTICS\n"
        "Source: %s | Hardware: NOT TESTED\n"
        "A: Hello | X: JNI/FFM SDL | Y: LWJGL JNI/SDL/Vulkan\n"
        "B: SDL/Vulkan + VMA | R: FreeType/OpenAL loopback\n"
        "L: STB + shader tools | +: exit without starting a VM\n"
        "Use application-mode hbmenu. Each choice starts at most one VM.\n"
        "Run A, then X, then Y in separate fresh processes.\n"
        "Close with + and reopen hbmenu before another VM attempt.\n",
        revision);
}
