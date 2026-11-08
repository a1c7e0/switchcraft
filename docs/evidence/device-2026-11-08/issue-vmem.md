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

Run ffi-test Y (whole 64 KiB reserve/commit) and B (middle two pages of an aligned 16 KiB reservation), then zero-services-test L (private VM Alias memory probe).

Expected behavior:
A supported memory backend must reserve aligned data memory, commit/protect/uncommit/recommit safely, and clean up owned resources. Unsupported process capabilities must be reported truthfully with the raw Result, not as successful mappings.

Actual behavior:
Aligned reserve succeeds but the first public and private commit returns raw 0xfa01. Both a whole 64 KiB and partial two-page mapping reproduce; release/cleanup succeeds. Native ordinary memory/thread tests pass.

Evidence:
### ffi-test.log
```text
[tick=11756747856] 
Switchcraft ffi-test 0.1.0 | hardware status: NOT TESTED
[tick=11758021292] Applet type=0 (Application=0); firmware=21.2.0
[tick=11758148990] Log: sdmc:/switch/mc-runtime/logs/ffi-test.log (open)
[tick=11758274238] libffi Horizon / Java 25 fallback linker prerequisites
A: native downcalls | X: W^X upcall closure | +: exit
This does not initialize a Java 25 VM. Hardware NOT TESTED.
[tick=11758420474] Y: virtual memory reserve / commit / uncommit probe
[tick=11758540646] B: aligned partial mappings / R-NONE-RW protection probe
[tick=11784735216] AAPCS64 integer downcall=42 expected=42 PASS
[tick=11784982658] AAPCS64 mixed integer/FP downcall=41.5 expected=41.5 PASS
[tick=11817055649] libffi closure allocated using libnx JIT RW/RX permissions
[tick=11817303235] FFM-style upcall=42 expected=42 PASS
[tick=11817422919] jitClose Result=0x0
[tick=11817548117] mixed integer/FP upcall=41.5 expected=41.5 PASS
[tick=11817667322] mixed jitClose Result=0x0
[tick=11923935147] vmem reserved 65536 bytes at 0x3279e00000
[tick=11924182852] vmem commit failed: status=4 Result=0xfa01
[tick=11924302399] vmem release status=0 Result=0x0
[tick=11957535608] partial vmem reserve size=16384 alignment=65536 status=0
[tick=11957782463] partial vmem address=0x3279e00000 aligned=PASS; outer pages remain unmapped
[tick=11957902745] partial vmem commit offset=4096 length=8192 status=4 Result=0xfa01
[tick=11958020943] vmem release status=0 Result=0x0
[tick=12003294528] Clean exit: ffi-test
```
SHA256: `20cf21f220cb586c6c1147fc86188d19d1faafba12bbf53bd6fe6f65b6793e5e`

### zero-services-test.log
```text
[tick=12129382692] 
Switchcraft zero-services-test 0.1.0 | hardware status: NOT TESTED
[tick=12129855195] Applet type=0 (Application=0); firmware=21.2.0
[tick=12129909386] Log: sdmc:/switch/mc-runtime/logs/zero-services-test.log (open)
[tick=12129964537] OpenJDK25 Horizon OS-service components only
NO Java VM, NO classfile execution; hardware NOT TESTED.
A: time/synchronization probe | X: native thread/permit probe | +: exit
[tick=12130116206] Y: experimental fault-island probe; may abort if recovery is unsupported
[tick=12130311980] B: deferred native thread ownership / join / close probe
[tick=12130364218] L: private VM Alias memory / split release / SDK ownership probe
[tick=12194335694] Genuine OpenJDK25 os:: timing and HorizonSemaphore primitives
[tick=12194512059] Counter frequency=19200000 Hz
[tick=12194575646] os::javaTimeNanos samples=10000 span=697188 ns monotonic=PASS
[tick=12194628012] os::javaTimeMillis=1737943965570 (Horizon/newlib wall clock)
[tick=12194679216] HorizonSemaphore token accounting=PASS; contention not exercised
[tick=12194733259] HotSpot Atomic 64-bit add/CAS/load=PASS; contention not exercised
[tick=12194784578] No Java VM startup, classfile execution, JNI, or Java FFM was tested.
[tick=12194873528] PlatformMonitor wait(2ms)=-3 expected timeout=-3; mutex reacquired
[tick=12194924579] PlatformMutex/Monitor accounting/timeout=PASS; contention not exercised
[tick=12194995810] PlatformEvent coalesced permits and real timed wait=PASS
[tick=12252895329] native parent identity status=0 Result=0x0 id=668
[tick=12253058383] native create stack=131072 status=0 Result=0x0
[tick=12253108116] native start status=0 Result=0x0
[tick=12253169331] native join status=0 Result=0x0
[tick=12253221372] native close status=0 Result=0x0 (libnx cannot report svcCloseHandle Result)
[tick=12253276041] native child id=674 stack Result=0x0 identity Result=0x0 completed=64
[tick=12253326273] native thread / stack bounds / 64 permit handoffs: PASS; no VM/JNI test
[tick=12253379259] HotSpot library TLS + compiler __thread isolation=PASS; opaque markers, no Thread/JavaThread objects
[tick=12274015831] Actual process-lifetime native reaper startup: status=0 Result=0x0
[tick=12274177043] Retired worker still alive: queued/inflight=1 async Result=0x0
[tick=12274420437] Deferred join/close: pending=0 async Result=0x0; PASS
[tick=12314656197] Native Alias memory probe: begin (physical mapping syscalls; no VM execution)
[tick=12314814080] memory probe reserve aligned private 16 KiB: OK raw=0x0
[tick=12314863491] memory probe alignment: PASS address=0x3279e00000 alignment=65536
[tick=12314913140] memory probe commit private 4 pages: SYSTEM raw=0xfa01
[tick=12314964518] memory probe cleanup private parent: OK raw=0x0
[tick=12315014391] Native Alias memory probe: FAIL; retained ownership will be retried on next press
[tick=12771296500] Closing this application process; reopen application-mode hbmenu for another native test.
[tick=12771454638] Clean exit: zero-services-test
[tick=14472676033] 
Switchcraft zero-services-test 0.1.0 | hardware status: NOT TESTED
[tick=14472717520] Applet type=0 (Application=0); firmware=21.2.0
[tick=14472769916] Log: sdmc:/switch/mc-runtime/logs/zero-services-test.log (open)
[tick=14472823844] OpenJDK25 Horizon OS-service components only
NO Java VM, NO classfile execution; hardware NOT TESTED.
A: time/synchronization probe | X: native thread/permit probe | +: exit
[tick=14472874152] Y: experimental fault-island probe; may abort if recovery is unsupported
[tick=14472923285] B: deferred native thread ownership / join / close probe
[tick=14472972382] L: private VM Alias memory / split release / SDK ownership probe
[tick=14482015721] SafeFetch target address 0: query Result=0x0 permissions=0x0
[tick=14482171336] SafeFetch valid 32/64-bit loads=PASS
[tick=14482219617] Attempt SafeFetch32 at unreadable address 0; recovery is hardware NOT TESTED
[tick=14482266251] SafeFetch32 fault result=-12345 expected=-12345
[tick=14482310224] Attempt SafeFetchN at unreadable address 0
[tick=14482379388] SafeFetchN fault result=-67890 expected=-67890
[tick=14482427203] SafeFetch fault-island recovery=PASS; no general Java exception/VM claim
[tick=14567136725] Closing this application process; reopen application-mode hbmenu for another native test.
[tick=14567196512] Clean exit: zero-services-test
[tick=14830205842] 
Switchcraft zero-services-test 0.1.0 | hardware status: NOT TESTED
[tick=14830250067] Applet type=0 (Application=0); firmware=21.2.0
[tick=14830309273] Log: sdmc:/switch/mc-runtime/logs/zero-services-test.log (open)
[tick=14830372295] OpenJDK25 Horizon OS-service components only
NO Java VM, NO classfile execution; hardware NOT TESTED.
A: time/synchronization probe | X: native thread/permit probe | +: exit
[tick=14830428076] Y: experimental fault-island probe; may abort if recovery is unsupported
[tick=14830482530] B: deferred native thread ownership / join / close probe
[tick=14830539075] L: private VM Alias memory / split release / SDK ownership probe
[tick=14864095667] SafeFetch target address 0: query Result=0x0 permissions=0x0
[tick=14864261826] SafeFetch valid 32/64-bit loads=PASS
[tick=14864321254] Attempt SafeFetch32 at unreadable address 0; recovery is hardware NOT TESTED
[tick=14864377863] SafeFetch32 fault result=-12345 expected=-12345
[tick=14864434836] Attempt SafeFetchN at unreadable address 0
[tick=14864489495] SafeFetchN fault result=-67890 expected=-67890
[tick=14864545166] SafeFetch fault-island recovery=PASS; no general Java exception/VM claim
[tick=14991456530] Closing this application process; reopen application-mode hbmenu for another native test.
[tick=14991620155] Clean exit: zero-services-test
```
SHA256: `98a6f46a5f2079383aab036a189ef1d212f50d9034fcdcef163552e7a74566b6`

Analysis:
Confirmed in b7c2ac7 src/vmem_horizon.c and ports/openjdk25/src/hotspot/os/horizon/horizon_memory_bridge.c: commit calls real svcMapPhysicalMemory. Public Horizon kernel source checks nonzero process SystemResourceSize before mapping and returns InvalidState (0xfa01) when it is zero. Existing physical logs do not yet print SystemResourceSizeTotal, so that specific process field remains to be captured. Alignment passed; changing heap size or Alias address cannot grant process resources. No loader/NPDM privilege change or unsafe mapping is requested.

Requested action for java-switch:
Preserve raw Result and report unsupported physical mappings. Add process SystemResource diagnostics and implement a legitimate separately documented data-memory backend usable in this homebrew process context, if possible, with actual NONE/R/RW protection and explicit budget/ownership semantics. Preserve public ABI1 and its unmapped-reserve contract. Acceptance: source/host mock regressions plus physical L/FFI repeat results; do not close solely on compilation.
