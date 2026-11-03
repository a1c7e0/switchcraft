#!/usr/bin/env python3
import pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
dot="""digraph Switchcraft {
 graph [rankdir=LR,label="Snapshot 6: cross-linked Horizon VM / device execution untested",labelloc=t,bgcolor=white];
 node [shape=box,style="rounded,filled",fillcolor="#e1f1ec",fontname=Helvetica];
 hb [label="Application-mode hbmenu"]; diag [label="Native platform diagnostics"];
 sdl [label="SDL3 + VI swapchain / gamepad\nExact Vulkan base-profile test"];
 vk [label="NVK transfer / offscreen triangle"];
 launch [label="Read-only snapshot planner\nRuntime gate"];
 sdk [label="Pinned java-switch SDK\nJNI adapter + native FFI prerequisites"];
 mini [label="Java 8 diagnostic NRO"];
 vm [label="Horizon Java 25 / instrument VM\nCross-linked; startup NOT TESTED"];
 probe [label="Java25 standalone + combined\nJDK / SDL / Vulkan resolver"];
 lw [label="Future static LWJGL / FFM\nVMA / shaderc / SPVC / audio",style="rounded,dashed,filled",fillcolor="#ffe9ce"];
 mc [label="Horizon Minecraft title\nNOT ACHIEVED",style="rounded,dashed,filled",fillcolor="#ffe9ce"];
 hb->diag;diag->sdl;diag->vk;diag->launch;diag->mini;hb->probe;launch->sdk;probe->vm;sdk->vm [style=dashed];vm->lw [style=dashed];lw->mc [style=dashed];
 host [shape=note,label="HOST ONLY: Java25 / llvmpipe Vulkan\nstrict Demo title PASS\nAll physical Switch execution NOT TESTED",fillcolor="#e4e8fa"];
}"""
subprocess.run(['dot','-Tsvg','-o',str(root/'docs/architecture.svg')],input=dot,text=True,check=True)
