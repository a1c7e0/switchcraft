/* Experimental same-process VM + JDK + SDL/Vulkan resolver smoke test. */
#include "platform.h"
#include <javaswitch/runtime.h>
#include <javaswitch/native_resolver.h>
#include <switchcraft/composite_resolver.h>
#include <switchcraft/native_symbols_jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <stdatomic.h>

/* Retain physical budget for VM Alias mappings. The loader may override this. */
size_t __nx_heap_size=256u*1024u*1024u;
u64 __nx_exception_stack_size=64u*1024u;
u8 __nx_exception_stack[64u*1024u] __attribute__((aligned(16)));
/* Best-effort fatal diagnostics only; this is not a fault recovery handler. */
void __libnx_exception_handler(ThreadExceptionDump *dump){
    sc_diag_exception(dump);
}
static Thread worker;
static atomic_bool finished;
static JsLaunchResult launch_result;
static int launch_status=JS_UNAVAILABLE;
static char vm_stdout[192],vm_stderr[192];
static const char *const options[]={"--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED"};
static JsLaunchRequest request={
    .abi_version=JS_ABI_VERSION,.required_java_major=25,.backend="openjdk25",
    .classpath=SC_ROOT "/tests/java25-hello.jar",.main_class="HelloHorizon25",.heap_mib=128
};
static void run_vm(void *unused){
    (void)unused;
    sc_diag_stage(2); /* Shared with the runtime provider's startup stages. */
    launch_status=js_runtime_launch_with_options(&request,options,1,&launch_result);
    atomic_store_explicit(&finished,true,memory_order_release);
}
static bool check_symbol(const char *module,const char *symbol){
    uintptr_t address=0;
    int status=js_native_symbol_lookup(module,symbol,&address);
    sc_log("Resolver module=%s symbol=%s status=%d address=%s\n",module,symbol,status,address?"present":"missing");
    return status==JS_OK && address!=0;
}
int main(void){
    sc_init("switchcraft-java25");
    sc_log("Experimental real Zero VM + composed JDK/SDL/Vulkan resolver; hardware NOT TESTED.\n");
    sc_memory();
    sc_log("Native heap=%zu loader override=%d bytes=%llu; worker stack=4 MiB Java heap=128 MiB\n",
           __nx_heap_size,envHasHeapOverride(),(unsigned long long)(envHasHeapOverride()?envGetHeapOverrideSize():0));
    sc_log("A: classfile-69 Hello | X: Java JNI/FFM SDL version smoke | +: exit without a VM.\n"
           "Use standalone java25-test A/X/Y in separate fresh application processes first.\n");
    u64 keys=0;bool selected=false,ffi_smoke=false;
    while(sc_frame(&keys)){
        if(keys&HidNpadButton_A){selected=true;break;}
        if(keys&HidNpadButton_X){selected=true;ffi_smoke=true;break;}
    }
    if(!selected){sc_exit();return 0;}
    if(appletGetAppletType()!=AppletType_Application){
        sc_log("Application-mode hbmenu is required; VM startup skipped.\n");goto done;
    }
    if(ffi_smoke){
        request.classpath=SC_ROOT "/tests/switchcraft-native-smoke.jar";
        request.main_class="org/switchcraft/runtime/HorizonResolverSmoke";
        request.on_vm_ready=sc_register_native_symbols;
        sc_log("Selected Java JNI/FFM SDL version test; requires real fallback linker.\n");
    }
    int rc=sc_install_composite_resolver();
    sc_log("STAGE install combined resolver=%d\n",rc);
    if(rc!=JS_OK)goto done;
    if(!check_symbol("java","JNI_OnLoad_java") || !check_symbol("SDL3","SDL_CreateWindow") ||
       !check_symbol("SDL3","SDL_Vulkan_CreateSurface") || !check_symbol("vulkan","vkGetInstanceProcAddr")){
        sc_log("STAGE resolver preflight failed; VM not started\n");goto done;
    }
    JsRuntimeInfo info={0};rc=js_runtime_query("openjdk25",&info);
    sc_log("STAGE runtime query=%d available=%d JNI=%d version=%u (symbol presence only)\n",rc,info.available,info.standard_jni,info.java_major);
    if(rc!=JS_OK||!info.available||!info.standard_jni||info.java_major!=25)goto done;
    unsigned long long attempt=(unsigned long long)armGetSystemTick();
    snprintf(vm_stdout,sizeof(vm_stdout),SC_LOGS "/switchcraft-java25-vm-%llu-stdout.log",attempt);
    snprintf(vm_stderr,sizeof(vm_stderr),SC_LOGS "/switchcraft-java25-vm-%llu-stderr.log",attempt);
    sc_log("STAGE VM output redirect; worker join pauses UI. HOME can close a stalled application.\nstdout=%s\nstderr=%s\n",vm_stdout,vm_stderr);consoleUpdate(NULL);
    fflush(stdout);fflush(stderr);sc_log_console(false);
    if(!freopen(vm_stdout,"a",stdout)){
        sc_log("VM stdout redirect failed errno=%d\n",errno);goto done;
    }
    if(!freopen(vm_stderr,"a",stderr)){
        sc_log("VM stderr redirect failed errno=%d\n",errno);goto done;
    }
    if(setvbuf(stdout,NULL,_IOLBF,0)||setvbuf(stderr,NULL,_IOLBF,0)){
        sc_log("VM output buffering failed; startup skipped\n");goto done;
    }
    rc=threadCreate(&worker,run_vm,NULL,NULL,4u*1024u*1024u,0x2c,-2);
    sc_log("STAGE worker create Result=0x%x\n",rc);
    if(R_FAILED(rc))goto done;
    sc_diag_stage(1);
    rc=threadStart(&worker);sc_log("STAGE worker start Result=0x%x\n",rc);
    if(R_FAILED(rc)){Result closed=threadClose(&worker);sc_log("Unstarted worker close Result=0x%x\n",closed);goto done;}
    rc=threadWaitForExit(&worker);sc_log("STAGE worker join Result=0x%x\n",rc);
    if(R_FAILED(rc)){sc_log("Worker ownership retained until process exit\n");goto done;}
    if(atomic_load_explicit(&finished,memory_order_acquire))
        sc_log("STAGE VM status=%d stage=%s; verify actual Hello output separately\n",launch_status,launch_result.stage?launch_result.stage:"unknown");
    else sc_log("Worker exited without publishing a result\n");
    rc=threadClose(&worker);sc_log("STAGE worker close Result=0x%x\n",rc);
    sc_diag_report();
done:
    sc_result_review(launch_status,launch_result.stage?launch_result.stage:"preflight-or-worker-failed",vm_stdout,vm_stderr);
    sc_log("Closing application process after result review; reopen application-mode hbmenu for another test.\n");
    fflush(NULL);sc_exit();svcExitProcess();
}
