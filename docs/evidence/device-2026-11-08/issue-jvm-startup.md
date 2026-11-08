Runtime revision:
`b7c2ac7fd422bc2543e5c698db4e33a01cc0312d` (executed artifact); source analysis/fixes are in a working tree based on d8ca281fce2b0f21424623bdbdfa77e72ceea08f.

Switchcraft revision:
Executed native diagnostics: `e08f36a9d19cf461312f87a866f9bb1f39d57d98`. Launcher: `13e9cffdd740f94c4882d124e7f8a995aabf5193`. Package recipe: 7182ebc1b6db3ef2e00fd9157cd1e3b122cc6ac9. Current Switchcraft source: 91b0eb029bfd2ef93bbf6527795e9642a83a15fa, plus uncommitted device-evidence/Vulkan diagnostics work.

Execution environment:
Physical Switch (Switch 1 task target), firmware 21.2.0; log reports AppletType_Application=0. Atmosphere/hbmenu versions were not supplied.
Cross-build toolchain: aarch64-none-elf-gcc (devkitA64) 15.2.0. Pinned devkitPro image is in Switchcraft dependencies.lock.json. The physical logs, not host execution, establish these failures.

Reproduction:
Download `https://github.com/a1c7e0/switchcraft/releases/download/test-suite-2026-11-08/switchcraft-complete-test-suite-2026-11-08.zip` (SHA256 `5626a9e6e0f56cbbe89830e8e9bc35c93436a5f13fff1f3bb4037860ca4c696e`), extract directly onto the SD root, and use application-mode hbmenu. No game assets or credentials are needed.
To reproduce the original cross-build, check out java-switch b7c2ac7fd422bc2543e5c698db4e33a01cc0312d and run `bash scripts/build-openjdk25-runtime.sh --with-instrument`; Switchcraft e08f36a uses `bash scripts/build-all.sh`. These are the original immutable source/build commands, not a claim of a newly repeated device run.

Standalone java25-test: in separate fresh processes press A (Hello), X (JNI/FFM suite), Y (startup agent). The complete java.base/java.instrument runtime and required smoke JARs are included. Combined switchcraft-java25: after preflight, A or X also reproduces. VM options include -Xmx128M and --enable-native-access=ALL-UNNAMED; standalone Y passes the packaged startup -javaagent. See complete test source at the executed revision for classpaths/options.

Expected behavior:
Either execute the selected genuine workload and retain its result, or report an explicit supported startup failure; preserve a readable result and complete logs. No success should be inferred from a process exit.

Actual behavior:
Standalone all A/X/Y attempts terminate with a libnx data abort, ESR 0x92000005, FAR 0x468. Combined A/X completes resolver/runtime preflight and threadCreate/threadStart Results 0, then aborts with the same FAR. Both stdout/stderr are zero bytes. No Hello/JNI/FFM/agent execution is established. The observed crash follows worker start immediately; user reports an immediate exit, with no measured long wait.

Evidence:
### java25-test.log
```text
[tick=15503665580] 
Switchcraft java25-test 0.1.0 | hardware status: NOT TESTED
[tick=15503853309] Applet type=0 (Application=0); firmware=21.2.0
[tick=15503979511] Log: sdmc:/switch/mc-runtime/logs/java25-test.log (open)
[tick=15504103733] Genuine OpenJDK25 Zero startup diagnostic; device execution NOT TESTED
[tick=15504224546] Process memory: total=3444572160 used=3440488448 bytes rc=0x0/0x0
[tick=15504342456] Process limit minus current use=4083712 bytes (not JVM heap)
[tick=15504462394] Newlib malloc arena=14336000 allocated=14307936 free-in-arena=28064 bytes
[tick=15504583277] Kernel-used memory includes reserved heap; arena free space is separate.
[tick=15506522896] 4 MiB allocation/write/read/free: PASS
[tick=15506786822] Newlib configured heap=268435456 bytes; loader heap override=1 size=3431952384 bytes
[tick=15506908914] JVM request is -Xmx128M; process total/used budget is reported above and the loader override takes precedence over the configured newlib heap.
[tick=15507030359] A: classfile-69 Hello | X: full Java25Smoke suite | Y: startup javaagent/JVMTI/ClassFileLoadHook [device NOT TESTED] | +: exit
One VM launch per process.
[tick=15539294975] Selected Java25 mode=classfile-69-Hello
[tick=15539539263] runtime query status=0 available=1 Java=25 JNI=1
[tick=15539670769] OpenJDK25 will run on a 4 MiB worker; UI updates pause during the worker join. Initial diagnostics are in sdmc:/switch/mc-runtime/logs/java25-test.log; VM stdout/stderr will append to sdmc:/switch/mc-runtime/logs/java25-vm-stdout.log and sdmc:/switch/mc-runtime/logs/java25-vm-stderr.log. If startup hangs, use Home and close the application from the system UI.
[tick=15540163615] libnx fatal exception: descriptor=0x00000101 PC=0x000000370b012750 ESR=0x92000005 FAR=0x0000000000000468
[tick=15873996928] 
Switchcraft java25-test 0.1.0 | hardware status: NOT TESTED
[tick=15874073570] Applet type=0 (Application=0); firmware=21.2.0
[tick=15874191192] Log: sdmc:/switch/mc-runtime/logs/java25-test.log (open)
[tick=15874307109] Genuine OpenJDK25 Zero startup diagnostic; device execution NOT TESTED
[tick=15874423629] Process memory: total=3444572160 used=3440488448 bytes rc=0x0/0x0
[tick=15875621708] Process limit minus current use=4083712 bytes (not JVM heap)
[tick=15875740907] Newlib malloc arena=14336000 allocated=14307936 free-in-arena=28064 bytes
[tick=15876088820] Kernel-used memory includes reserved heap; arena free space is separate.
[tick=15878956637] 4 MiB allocation/write/read/free: PASS
[tick=15880205556] Newlib configured heap=268435456 bytes; loader heap override=1 size=3431952384 bytes
[tick=15881217227] JVM request is -Xmx128M; process total/used budget is reported above and the loader override takes precedence over the configured newlib heap.
[tick=15882021595] A: classfile-69 Hello | X: full Java25Smoke suite | Y: startup javaagent/JVMTI/ClassFileLoadHook [device NOT TESTED] | +: exit
One VM launch per process.
[tick=16005214719] Selected Java25 mode=Java25Smoke
[tick=16005458238] runtime query status=0 available=1 Java=25 JNI=1
[tick=16005852565] OpenJDK25 will run on a 4 MiB worker; UI updates pause during the worker join. Initial diagnostics are in sdmc:/switch/mc-runtime/logs/java25-test.log; VM stdout/stderr will append to sdmc:/switch/mc-runtime/logs/java25-vm-stdout.log and sdmc:/switch/mc-runtime/logs/java25-vm-stderr.log. If startup hangs, use Home and close the application from the system UI.
[tick=16006277072] libnx fatal exception: descriptor=0x00000101 PC=0x00000024c3c20750 ESR=0x92000005 FAR=0x0000000000000468
[tick=16223755382] 
Switchcraft java25-test 0.1.0 | hardware status: NOT TESTED
[tick=16223831428] Applet type=0 (Application=0); firmware=21.2.0
[tick=16223945195] Log: sdmc:/switch/mc-runtime/logs/java25-test.log (open)
[tick=16224059425] Genuine OpenJDK25 Zero startup diagnostic; device execution NOT TESTED
[tick=16224175056] Process memory: total=3444572160 used=3440488448 bytes rc=0x0/0x0
[tick=16224288491] Process limit minus current use=4083712 bytes (not JVM heap)
[tick=16224403871] Newlib malloc arena=14336000 allocated=14307936 free-in-arena=28064 bytes
[tick=16224517838] Kernel-used memory includes reserved heap; arena free space is separate.
[tick=16227087640] 4 MiB allocation/write/read/free: PASS
[tick=16227330856] Newlib configured heap=268435456 bytes; loader heap override=1 size=3431952384 bytes
[tick=16227452030] JVM request is -Xmx128M; process total/used budget is reported above and the loader override takes precedence over the configured newlib heap.
[tick=16227571987] A: classfile-69 Hello | X: full Java25Smoke suite | Y: startup javaagent/JVMTI/ClassFileLoadHook [device NOT TESTED] | +: exit
One VM launch per process.
[tick=16242016019] Selected Java25 mode=startup-javaagent (cross-built; device NOT TESTED)
[tick=16242263366] runtime query status=0 available=1 Java=25 JNI=1
[tick=16242386982] Y selected: genuine startup -javaagent request; premain/JVMTI transformation is cross-built but device execution NOT TESTED.
[tick=16242520082] OpenJDK25 will run on a 4 MiB worker; UI updates pause during the worker join. Initial diagnostics are in sdmc:/switch/mc-runtime/logs/java25-test.log; VM stdout/stderr will append to sdmc:/switch/mc-runtime/logs/java25-vm-stdout.log and sdmc:/switch/mc-runtime/logs/java25-vm-stderr.log. If startup hangs, use Home and close the application from the system UI.
[tick=16242930408] libnx fatal exception: descriptor=0x00000101 PC=0x00000023b5503750 ESR=0x92000005 FAR=0x0000000000000468
```
SHA256: `ba5bf2fa0212eea5c5d4be3742561ee9674a005d4a831237c22b86f62f2ca176`

### java25-vm-stdout.log
```text
(zero bytes)
```
SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

### java25-vm-stderr.log
```text
(zero bytes)
```
SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

### switchcraft-java25.log
```text
[tick=16575430949] 
SESSION start tick=16575424714 app=switchcraft-java25 version=0.1.0 source=e08f36a9d19cf461312f87a866f9bb1f39d57d98 | hardware status: NOT TESTED
[tick=16575804427] Applet type=0 (Application=0); firmware=21.2.0
[tick=16575925777] Log: sdmc:/switch/mc-runtime/logs/switchcraft-java25.log (open)
[tick=16576044616] Experimental real Zero VM + composed JDK/SDL/Vulkan resolver; hardware NOT TESTED.
[tick=16576164110] Process memory: total=3444572160 used=3440488448 bytes rc=0x0/0x0
[tick=16576282193] Process limit minus current use=4083712 bytes (not JVM heap)
[tick=16576404014] Newlib malloc arena=14336000 allocated=14308032 free-in-arena=27968 bytes
[tick=16576526033] Kernel-used memory includes reserved heap; arena free space is separate.
[tick=16576993155] 4 MiB allocation/write/read/free: PASS
[tick=16577230607] Native heap=268435456 loader override=1 bytes=3419639808; worker stack=4 MiB Java heap=128 MiB
[tick=16577359317] A: classfile-69 Hello | X: Java JNI/FFM SDL version smoke | +: exit without a VM.
Use standalone java25-test A/X/Y in separate fresh application processes first.
[tick=16595934928] STAGE install combined resolver=0
[tick=16596187618] Resolver module=java symbol=JNI_OnLoad_java status=0 address=present
[tick=16596306319] Resolver module=SDL3 symbol=SDL_CreateWindow status=0 address=present
[tick=16596426727] Resolver module=SDL3 symbol=SDL_Vulkan_CreateSurface status=0 address=present
[tick=16596544231] Resolver module=vulkan symbol=vkGetInstanceProcAddr status=0 address=present
[tick=16596661710] STAGE runtime query=0 available=1 JNI=1 version=25 (symbol presence only)
[tick=16596780265] STAGE VM output redirect; worker join pauses UI. HOME can close a stalled application.
[tick=16597552852] STAGE worker create Result=0x0
[tick=16597674042] STAGE worker start Result=0x0
[tick=16597840188] Fatal exception descriptor=0x00000101 PC=0x000000684c027950 ESR=0x92000005 FAR=0x0000000000000468
[tick=16959438861] 
SESSION start tick=16959433966 app=switchcraft-java25 version=0.1.0 source=e08f36a9d19cf461312f87a866f9bb1f39d57d98 | hardware status: NOT TESTED
[tick=16962306924] Applet type=0 (Application=0); firmware=21.2.0
[tick=16962425258] Log: sdmc:/switch/mc-runtime/logs/switchcraft-java25.log (open)
[tick=16962543365] Experimental real Zero VM + composed JDK/SDL/Vulkan resolver; hardware NOT TESTED.
[tick=16962660706] Process memory: total=3444572160 used=3440488448 bytes rc=0x0/0x0
[tick=16962780398] Process limit minus current use=4083712 bytes (not JVM heap)
[tick=16962900611] Newlib malloc arena=14336000 allocated=14308032 free-in-arena=27968 bytes
[tick=16963017614] Kernel-used memory includes reserved heap; arena free space is separate.
[tick=16963499050] 4 MiB allocation/write/read/free: PASS
[tick=16964415014] Native heap=268435456 loader override=1 bytes=3419639808; worker stack=4 MiB Java heap=128 MiB
[tick=16964775806] A: classfile-69 Hello | X: Java JNI/FFM SDL version smoke | +: exit without a VM.
Use standalone java25-test A/X/Y in separate fresh application processes first.
[tick=16978655926] Selected Java JNI/FFM SDL version test; requires real fallback linker.
[tick=16978900162] STAGE install combined resolver=0
[tick=16979016955] Resolver module=java symbol=JNI_OnLoad_java status=0 address=present
[tick=16979138191] Resolver module=SDL3 symbol=SDL_CreateWindow status=0 address=present
[tick=16979255231] Resolver module=SDL3 symbol=SDL_Vulkan_CreateSurface status=0 address=present
[tick=16979371777] Resolver module=vulkan symbol=vkGetInstanceProcAddr status=0 address=present
[tick=16979487543] STAGE runtime query=0 available=1 JNI=1 version=25 (symbol presence only)
[tick=16979600229] STAGE VM output redirect; worker join pauses UI. HOME can close a stalled application.
[tick=16980042192] STAGE worker create Result=0x0
[tick=16980268591] STAGE worker start Result=0x0
[tick=16980529661] Fatal exception descriptor=0x00000101 PC=0x0000001e7ec79950 ESR=0x92000005 FAR=0x0000000000000468
```
SHA256: `41b5bf980b5738c8bedd72303e1d828db2a6cac9322589384955fba7dd68af16`

### switchcraft-java25-vm-stdout.log
```text
(zero bytes)
```
SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

### switchcraft-java25-vm-stderr.log
```text
(zero bytes)
```
SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

No crash report/full register dump was supplied. Raw ASLR PCs do not uniquely determine the faulting ELF offset.

Analysis:
Confirmed: standalone and composed diagnostics both reproduce; static symbol/provider queries succeed, worker start succeeds in the composed trace. This is earlier than any observed Java output. Existing native TLS/thread/SafeFetch probes passed and do not exercise VM thread initialization. Hypothesis: early VM/native-thread/TLS initialization; current evidence cannot identify the exact instruction or prove which internal VM stage was reached. Do not map a raw ASLR PC by assuming a module base.

Requested action for java-switch:
Fix the source-confirmed cause once localized, and add raw, bounded fatal register/relative-PC and stage diagnostics plus retained result review to src/java25_vm_test.c and its platform support. Preserve one VM per process and safe process termination. Acceptance: on physical application-mode Switch the A Hello output is retained; then independently X and Y succeed in fresh processes. Leave this execution issue open until device evidence validates it.
