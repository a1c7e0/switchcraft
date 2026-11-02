#!/usr/bin/env python3
"""Generate an exportable diagram with Graphviz (optional documentation tool)."""
import pathlib
import subprocess

root=pathlib.Path(__file__).resolve().parents[1]
dot='''digraph Switchcraft {
  graph [rankdir=LR, bgcolor="white", label="Switchcraft: implemented native diagnostics / planned game integration", labelloc=t];
  node [shape=box, style="rounded,filled", fillcolor="#e2f2ed", fontname="Helvetica"];
  edge [fontname="Helvetica", color="#365b56"];
  hb [label="Application-mode hbmenu"];
  diag [label="Platform diagnostic NRO\\nSD / memory / input / threads"];
  launcher [label="Installation inspector NRO\\nJSON / rules / classpath plan"];
  gl [label="OpenGL NRO\\nEGL + Mesa NVC0\\nvisible triangle / readback"];
  vk [label="Vulkan NRO\\nMesa NVK\\nfill + offscreen triangle"];
  java [label="Java test NRO\\nminiJVM interpreter\\nJAR / I/O / reflection / native bridge"];
  sd [label="Read-only .minecraft\\nSeparate runtime config/logs"];
  hb -> diag; hb -> launcher;
  diag -> gl [label="next-load"];
  diag -> vk [label="next-load"];
  diag -> java [label="next-load"];
  diag -> launcher [label="next-load"];
  launcher -> sd;
  jni [label="Future OpenJDK / JNI", style="rounded,dashed,filled", fillcolor="#fff1d8"];
  lwjgl [label="Future LWJGL / GLFW / OpenAL", style="rounded,dashed,filled", fillcolor="#fff1d8"];
  mc [label="Future Minecraft / Fabric", style="rounded,dashed,filled", fillcolor="#fff1d8"];
  wsi [label="Future Vulkan WSI / presentation", style="rounded,dashed,filled", fillcolor="#fff1d8"];
  launcher -> jni [style=dashed]; jni -> lwjgl [style=dashed]; lwjgl -> mc [style=dashed];
  vk -> wsi [style=dashed];
  status [shape=note, label="All Horizon execution: NOT TESTED\\nHost Java/metadata tests pass\\nMinecraft is not playable", fillcolor="#fce3df"];
}'''
subprocess.run(["dot","-Tsvg","-o",str(root/"docs/architecture.svg")],input=dot,text=True,check=True)
