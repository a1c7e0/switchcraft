"""Genuine LWJGL 3.4.3 STB/VMA JNI references and module resolver checks."""
import base64
import hashlib
import json
import pathlib
import re
import struct
import subprocess
import tempfile
import unittest
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
JDK = ROOT / ".deps/host-jdk25/jdk-25.0.5+8/bin"
MC = pathlib.Path("/tmp/r4-mc-reference")
VERSION = json.loads((MC / "version.json").read_text())
CORE_JAR = ROOT / ".deps/lwjgl_core.jar"
STB_JAR = MC / "libraries/org/lwjgl/lwjgl-stb/3.4.3/lwjgl-stb-3.4.3.jar"
VMA_JAR = MC / "libraries/org/lwjgl/lwjgl-vma/3.4.3/lwjgl-vma-3.4.3.jar"
VULKAN_JAR = MC / "libraries/org/lwjgl/lwjgl-vulkan/3.4.3/lwjgl-vulkan-3.4.3.jar"


def metadata_sha1(artifact: str) -> str:
    for library in VERSION["libraries"]:
        item = library.get("downloads", {}).get("artifact", {})
        if item.get("path", "").endswith(artifact):
            return item["sha1"]
    raise AssertionError(f"Minecraft metadata has no artifact: {artifact}")


def png_1x1_rgba() -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(b"\x00\x27\x63\x95\xff")) +
            chunk(b"IEND", b""))


def java_native_exports() -> tuple[dict[str, set[str]], int]:
    jars = (STB_JAR, VMA_JAR)
    classpath = ":".join(map(str, (*jars, CORE_JAR, VULKAN_JAR)))
    classes = []
    import zipfile
    for jar in jars:
        with zipfile.ZipFile(jar) as archive:
            classes.extend(name[:-6].replace("/", ".") for name in archive.namelist()
                           if name.endswith(".class") and not name.endswith("module-info.class"))
    output = subprocess.check_output([str(JDK / "javap"), "-p", "-s", "-classpath", classpath, *classes], text=True)
    declarations = []
    current_class = None
    lines = output.splitlines()
    for i, line in enumerate(lines):
        class_match = re.search(r"\b(?:class|interface|enum|record)\s+([\w.$]+)", line)
        if class_match:
            current_class = class_match.group(1)
        if " native " not in line and not line.strip().startswith("native "):
            continue
        method_match = re.search(r"\b([A-Za-z_$][\w$]*)\([^;]*\);", line)
        if method_match and i + 1 < len(lines) and "descriptor:" in lines[i + 1]:
            descriptor = lines[i + 1].split("descriptor:", 1)[1].strip()
            declarations.append((current_class, method_match.group(1), descriptor))
    overloads = {}
    for owner, method, _ in declarations:
        overloads[(owner, method)] = overloads.get((owner, method), 0) + 1

    def jni_escape(value: str) -> str:
        result = []
        for char in value:
            if char == "/": result.append("_")
            elif char == "_": result.append("_1")
            elif char == ";": result.append("_2")
            elif char == "[": result.append("_3")
            elif char.isalnum(): result.append(char)
            else: result.append("_0" + format(ord(char), "04x"))
        return "".join(result)

    expected = {"lwjgl_stb": set(), "lwjgl_vma": set()}
    for owner, method, descriptor in declarations:
        module = "lwjgl_stb" if owner.startswith("org.lwjgl.stb.") else "lwjgl_vma"
        symbol = "Java_" + jni_escape(owner.replace(".", "/")) + "_" + jni_escape(method)
        if overloads[(owner, method)] > 1:
            symbol += "__" + jni_escape(descriptor[1:descriptor.index(")")])
        expected[module].add(symbol)
    return expected, len(declarations)


class TestLWJGLUtilities(unittest.TestCase):
    def test_real_stb_vma_jar_calls_and_module_resolver(self):
        host = ROOT / "build/lwjgl-utilities/host"
        if not all((host / f"liblwjgl_{module}.so").is_file() for module in ("stb", "vma")):
            subprocess.run(["python3", str(ROOT / "scripts/build-lwjgl-utilities.py"), "--host"], cwd=ROOT, check=True)
        for jar, artifact in ((STB_JAR, "lwjgl-stb-3.4.3.jar"),
                              (VMA_JAR, "lwjgl-vma-3.4.3.jar"),
                              (VULKAN_JAR, "lwjgl-vulkan-3.4.3.jar")):
            self.assertEqual(hashlib.sha1(jar.read_bytes()).hexdigest(), metadata_sha1(artifact))
        expected, declaration_count = java_native_exports()
        inventory = json.loads((host / "jni-exports.json").read_text())
        actual = {module: {name for name in names if name.startswith("Java_")} for module, names in inventory.items()}
        windows_only = {"Java_org_lwjgl_util_vma_Vma_nvmaGetMemoryWin32Handle",
                        "Java_org_lwjgl_util_vma_Vma_nvmaGetMemoryWin32Handle2"}
        self.assertEqual(declaration_count, 299)
        self.assertEqual(actual["lwjgl_stb"], expected["lwjgl_stb"])
        self.assertEqual(actual["lwjgl_vma"] | windows_only, expected["lwjgl_vma"])
        self.assertTrue((ROOT / "build/lwjgl-core/host/liblwjgl.so").is_file(),
                        "run the genuine LWJGL core host provider build first")
        with tempfile.TemporaryDirectory(prefix="lwjgl-utilities-java-") as temp_name:
            temp = pathlib.Path(temp_name)
            (temp / "org/lwjgl/system").mkdir(parents=True)
            (temp / "org/lwjgl/system/Library.java").write_text("""package org.lwjgl.system;
import java.util.function.Consumer;
public final class Library {
    public static void initialize() {}
    public static void loadSystem(Consumer<String> first, Consumer<String> second,
                                  Class<?> caller, String module, String libName) {
        System.loadLibrary(libName);
    }
}
""")
            probe_c = temp / "lwjgl_utilities_probe.c"
            probe_c.write_text("""#include <jni.h>
#include <stdint.h>
#include <switchcraft/lwjgl_utilities.h>
typedef jint (JNICALL *OnLoad)(JavaVM *, void *);
JNIEXPORT jint JNICALL Java_LwjglUtilityReference_checkProvider(JNIEnv *env, jclass cls) {
    (void)cls;
    if (!sc_lwjgl_utilities_available("lwjgl_stb") ||
        !sc_lwjgl_utilities_available("lwjgl_vma") ||
        sc_lwjgl_utilities_available("lwjgl") ||
        sc_lwjgl_utilities_available("lwjgl_STB")) return 1;
    uintptr_t stb = sc_lwjgl_utilities_lookup("lwjgl_stb", "JNI_OnLoad_lwjgl_stb");
    uintptr_t vma = sc_lwjgl_utilities_lookup("lwjgl_vma", "JNI_OnLoad_lwjgl_vma");
    if (!stb || !vma || stb != sc_lwjgl_utilities_lookup(NULL, "JNI_OnLoad_lwjgl_stb") ||
        vma != sc_lwjgl_utilities_lookup(NULL, "JNI_OnLoad_lwjgl_vma")) return 2;
    if (!sc_lwjgl_utilities_lookup("lwjgl_stb", "Java_org_lwjgl_stb_STBImage_nstbi_1load_1from_1memory__JIJJJI") ||
        !sc_lwjgl_utilities_lookup("lwjgl_vma", "Java_org_lwjgl_util_vma_Vma_nvmaCreateAllocator") ||
        sc_lwjgl_utilities_lookup("lwjgl_vma", "Java_org_lwjgl_stb_STBImage_nstbi_1load_1from_1memory__JIJJJI") ||
        sc_lwjgl_utilities_lookup("lwjgl_stb", "JNI_OnLoad_missing") ||
        sc_lwjgl_utilities_lookup(NULL, "JNI_OnLoad_missing")) return 3;
    JavaVM *vm = NULL;
    if ((*env)->GetJavaVM(env, &vm) != JNI_OK || vm == NULL) return 4;
    if (((OnLoad)stb)(vm, NULL) != JNI_VERSION_1_8 || ((OnLoad)vma)(vm, NULL) != JNI_VERSION_1_8) return 5;
    return 0;
}
""")
            jni = ROOT / ".deps/host-jdk25/jdk-25.0.5+8/include"
            cc = "cc"
            subprocess.run([cc, "-std=c11", "-fPIC", "-shared",
                            "-I", str(jni), "-I", str(jni / "linux"),
                            "-I", str(ROOT / "include"), "-I", str(host),
                            str(probe_c), str(ROOT / "src/lwjgl_utilities_resolver.c"),
                            "-L", str(host), f"-Wl,-rpath,{host}",
                            "-llwjgl_stb", "-llwjgl_vma", "-o", str(host / "liblwjgl_utilities_probe.so")],
                           check=True)

            source = temp / "LwjglUtilityReference.java"
            source.write_text("""import java.lang.foreign.*;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Base64;
import org.lwjgl.BufferUtils;
import org.lwjgl.PointerBuffer;
import org.lwjgl.system.FunctionProvider;
import org.lwjgl.system.MemoryUtil;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.stb.STBImage;
import org.lwjgl.stb.STBEasyFont;
import org.lwjgl.vulkan.*;
import org.lwjgl.util.vma.*;

public final class LwjglUtilityReference {
    private static native int checkProvider();
    private static MethodHandle GIPA;
    private static long callGipa(long instance, long name) {
        try {
            MemorySegment result = (MemorySegment)GIPA.invokeExact(MemorySegment.ofAddress(instance), MemorySegment.ofAddress(name));
            return result.address();
        } catch (Throwable t) { throw new RuntimeException(t); }
    }
    private static long function(FunctionProvider p, String name) { return p.getFunctionAddress(name); }
    private static FunctionProvider vulkanProvider(Path loader, Arena arena) throws Exception {
        SymbolLookup symbols = SymbolLookup.libraryLookup(loader, arena);
        MemorySegment address = symbols.find("vkGetInstanceProcAddr").orElseThrow();
        GIPA = Linker.nativeLinker().downcallHandle(address,
            FunctionDescriptor.of(ValueLayout.ADDRESS, ValueLayout.ADDRESS, ValueLayout.ADDRESS));
        return new FunctionProvider() {
            public long getFunctionAddress(ByteBuffer name) {
                return callGipa(0L, MemoryUtil.memAddress(name));
            }
        };
    }
    private static void testVma(FunctionProvider provider) {
        VK.create(provider);
        try (MemoryStack stack = MemoryStack.stackPush()) {
            VkApplicationInfo app = VkApplicationInfo.calloc(stack).sType$Default()
                .pApplicationName(stack.UTF8("LWJGL VMA reference")).apiVersion(VK10.VK_API_VERSION_1_0);
            VkInstanceCreateInfo instanceInfo = VkInstanceCreateInfo.calloc(stack).sType$Default().pApplicationInfo(app);
            PointerBuffer instanceOut = stack.mallocPointer(1);
            if (VK10.vkCreateInstance(instanceInfo, null, instanceOut) != VK10.VK_SUCCESS) throw new AssertionError("vkCreateInstance failed");
            VkInstance instance = new VkInstance(instanceOut.get(0), instanceInfo);
            try {
                IntBuffer physicalCount = stack.ints(0);
                if (VK10.vkEnumeratePhysicalDevices(instance, physicalCount, null) != VK10.VK_SUCCESS || physicalCount.get(0) == 0)
                    throw new AssertionError("host Vulkan has no physical device");
                PointerBuffer physicalOut = stack.mallocPointer(physicalCount.get(0));
                VK10.vkEnumeratePhysicalDevices(instance, physicalCount, physicalOut);
                VkPhysicalDevice physical = new VkPhysicalDevice(physicalOut.get(0), instance);
                IntBuffer familyCount = stack.ints(0);
                VK10.vkGetPhysicalDeviceQueueFamilyProperties(physical, familyCount, null);
                VkQueueFamilyProperties.Buffer families = VkQueueFamilyProperties.calloc(familyCount.get(0), stack);
                VK10.vkGetPhysicalDeviceQueueFamilyProperties(physical, familyCount, families);
                int family = -1;
                for (int i = 0; i < families.capacity(); i++) if (families.get(i).queueCount() > 0) { family = i; break; }
                if (family < 0) throw new AssertionError("no Vulkan queue family");
                VkDeviceQueueCreateInfo.Buffer queues = VkDeviceQueueCreateInfo.calloc(1, stack)
                    .sType$Default().queueFamilyIndex(family).pQueuePriorities(stack.floats(1.0f));
                VkDeviceCreateInfo deviceInfo = VkDeviceCreateInfo.calloc(stack).sType$Default().pQueueCreateInfos(queues);
                PointerBuffer deviceOut = stack.mallocPointer(1);
                if (VK10.vkCreateDevice(physical, deviceInfo, null, deviceOut) != VK10.VK_SUCCESS) throw new AssertionError("vkCreateDevice failed");
                VkDevice device = new VkDevice(deviceOut.get(0), physical, deviceInfo);
                try {
                    VmaVulkanFunctions f = VmaVulkanFunctions.calloc(stack)
                        .vkGetInstanceProcAddr(function(provider, "vkGetInstanceProcAddr"))
                        .vkGetDeviceProcAddr(device.getCapabilities().vkGetDeviceProcAddr)
                        .vkGetPhysicalDeviceProperties(physical.getCapabilities().vkGetPhysicalDeviceProperties)
                        .vkGetPhysicalDeviceMemoryProperties(physical.getCapabilities().vkGetPhysicalDeviceMemoryProperties)
                        .vkAllocateMemory(device.getCapabilities().vkAllocateMemory)
                        .vkFreeMemory(device.getCapabilities().vkFreeMemory)
                        .vkMapMemory(device.getCapabilities().vkMapMemory)
                        .vkUnmapMemory(device.getCapabilities().vkUnmapMemory)
                        .vkFlushMappedMemoryRanges(device.getCapabilities().vkFlushMappedMemoryRanges)
                        .vkInvalidateMappedMemoryRanges(device.getCapabilities().vkInvalidateMappedMemoryRanges)
                        .vkBindBufferMemory(device.getCapabilities().vkBindBufferMemory)
                        .vkBindImageMemory(device.getCapabilities().vkBindImageMemory)
                        .vkGetBufferMemoryRequirements(device.getCapabilities().vkGetBufferMemoryRequirements)
                        .vkGetImageMemoryRequirements(device.getCapabilities().vkGetImageMemoryRequirements)
                        .vkCreateBuffer(device.getCapabilities().vkCreateBuffer)
                        .vkDestroyBuffer(device.getCapabilities().vkDestroyBuffer)
                        .vkCreateImage(device.getCapabilities().vkCreateImage)
                        .vkDestroyImage(device.getCapabilities().vkDestroyImage)
                        .vkCmdCopyBuffer(device.getCapabilities().vkCmdCopyBuffer);
                    VmaAllocatorCreateInfo create = VmaAllocatorCreateInfo.calloc(stack)
                        .physicalDevice(physical).device(device).instance(instance)
                        .pVulkanFunctions(f).vulkanApiVersion(VK10.VK_API_VERSION_1_0);
                    PointerBuffer allocator = stack.mallocPointer(1);
                    int result = Vma.vmaCreateAllocator(create, allocator);
                    if (result != VK10.VK_SUCCESS) throw new AssertionError("vmaCreateAllocator returned " + result);
                    Vma.vmaDestroyAllocator(allocator.get(0));
                } finally { VK10.vkDestroyDevice(device, null); }
            } finally { VK10.vkDestroyInstance(instance, null); }
        }
        VK.destroy();
    }
    public static void main(String[] args) throws Exception {
        System.loadLibrary("lwjgl");
        System.loadLibrary("lwjgl_utilities_probe");
        int provider = checkProvider();
        if (provider != 0) throw new AssertionError("utility resolver or JNI 1.8 module hooks failed: " + provider);
        byte[] png = Base64.getDecoder().decode(args[0]);
        ByteBuffer input = BufferUtils.createByteBuffer(png.length).put(png).flip();
        IntBuffer w = BufferUtils.createIntBuffer(1), h = BufferUtils.createIntBuffer(1), c = BufferUtils.createIntBuffer(1);
        ByteBuffer pixels = STBImage.stbi_load_from_memory(input, w, h, c, 4);
        if (pixels == null || w.get(0) != 1 || h.get(0) != 1 || pixels.get(0) != 0x27)
            throw new AssertionError("pinned STB PNG decode failed: " + STBImage.stbi_failure_reason());
        STBImage.stbi_image_free(pixels);
        ByteBuffer text = BufferUtils.createByteBuffer(32).put("LWJGL".getBytes(StandardCharsets.UTF_8)).put((byte)0).flip();
        ByteBuffer color = BufferUtils.createByteBuffer(4).put(new byte[] { 1, 2, 3, 4 }).flip();
        ByteBuffer vertices = BufferUtils.createByteBuffer(8192);
        if (STBEasyFont.stb_easy_font_print(0, 0, text, color, vertices) <= 0)
            throw new AssertionError("pinned STB text packing failed");
        try (Arena arena = Arena.ofConfined()) {
            testVma(vulkanProvider(Path.of(args[1]), arena));
        }
        System.out.println("Pinned LWJGL STB decode/text packing and VMA Vulkan allocator calls passed");
    }
}
""")
            jars = [CORE_JAR, STB_JAR, VMA_JAR, VULKAN_JAR]
            classpath = ":".join(map(str, [*jars, temp]))
            java_sources = [str(temp / "org/lwjgl/system/Library.java"), str(source)]
            subprocess.run([str(JDK / "javac"), "--release", "25", "-cp", classpath,
                            "-d", str(temp), *java_sources], check=True)
            vulkan_loader = next((p for p in (pathlib.Path("/usr/lib/x86_64-linux-gnu/libvulkan.so.1"),
                                                pathlib.Path("/usr/lib64/libvulkan.so.1"),
                                                pathlib.Path("/usr/lib/libvulkan.so.1")) if p.is_file()), None)
            self.assertIsNotNone(vulkan_loader, "host Vulkan loader missing")
            env = dict(__import__("os").environ)
            swiftshader = pathlib.Path("/usr/lib/chromium/vk_swiftshader_icd.json")
            if swiftshader.is_file():
                env["VK_ICD_FILENAMES"] = str(swiftshader)
            png = base64.b64encode(png_1x1_rgba()).decode()
            env["LD_LIBRARY_PATH"] = str(ROOT / "build/lwjgl-core/host") + ":" + str(ROOT / "build/lwjgl-utilities/host") + ":" + env.get("LD_LIBRARY_PATH", "")
            subprocess.run([str(JDK / "java"), "--enable-native-access=ALL-UNNAMED",
                            "-Dorg.lwjgl.util.NoHashChecks=true",
                            "-Dorg.lwjgl.vulkan.explicitInit=true",
                            f"-Djava.library.path={ROOT / 'build/lwjgl-core/host'}:{ROOT / 'build/lwjgl-utilities/host'}",
                            "-cp", classpath, "LwjglUtilityReference", png, str(vulkan_loader)],
                           cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    unittest.main()
