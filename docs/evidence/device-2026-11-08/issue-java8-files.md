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

Open java-test in a fresh process and press A. The suite uses sdmc:/switch/mc-runtime/instances/java-smoke; no user JAR is required.

Expected behavior:
miniJVM recognizes Horizon device-prefixed absolute paths and performs a real exclusive create/write/read/delete in its owned diagnostic directory, leaving any preexisting user file unchanged.

Actual behavior:
Arithmetic, exception handling, separate-JAR loading, reflection, Java thread start/join and 512 KiB allocation pass. DiagnosticSmoke.java:33 then throws RuntimeException FAIL: exclusive file creation; call_main -> 1. The native Switchcraft SD roundtrip succeeds separately.

Evidence:
### java-test.log
```text
[tick=10845615608] 
Switchcraft java-test 0.1.0 | hardware status: NOT TESTED
[tick=10845755909] Applet type=0 (Application=0); firmware=21.2.0
[tick=10845880929] Log: sdmc:/switch/mc-runtime/logs/java-test.log (open)
[tick=10846711410] EXPERIMENTAL miniJVM interpreter diagnostic
Not OpenJDK; no Minecraft/LWJGL/Fabric support.
A: bundled suite | X: tests/user.jar class UserMain
One run per process | B: diagnostics | +: exit
[tick=11020575984] Initializing miniJVM interpreter, classic GC, Java 8 class library
[tick=11020647358] [INFO] object layout: ptr=64b MemoryBlock=24 Instance=24 JArrayHeader=32 field_off=24 arr_len_off=24 arr_body_off=32
[tick=11020765697] [INFO] gc backend : classic malloc
[tick=11057532577] jvm_init -> 0
[tick=11065403514] H[tick=11065496192] e[tick=11065618905] l[tick=11065734504] l[tick=11065850115] o[tick=11065966514]  [tick=11066082735] W[tick=11066199388] o[tick=11067864154] r[tick=11068904018] l[tick=11069765014] d[tick=11070524426]  [tick=11070646442] f[tick=11070779644] r[tick=11070897338] o[tick=11071014010] m[tick=11071129951]  [tick=11071249214] J[tick=11071368338] a[tick=11071483406] v[tick=11071601245] a[tick=11071722050]  [tick=11071839499] b[tick=11071955749] y[tick=11072071812] t[tick=11072187499] e[tick=11072306090] c[tick=11072422261] o[tick=11072538455] d[tick=11072654609] e[tick=11072770991] 
[tick=11072889708] P[tick=11073009278] A[tick=11073125311] S[tick=11073243870] S[tick=11073359592] :[tick=11073475012]  [tick=11073592712] a[tick=11073708910] r[tick=11073825205] i[tick=11073941153] t[tick=11074056073] h[tick=11074172801] m[tick=11074289464] e[tick=11074406271] t[tick=11074522411] i[tick=11074636838] c[tick=11074755436] 
[tick=11075032664] P[tick=11075099135] A[tick=11075217945] S[tick=11075331803] S[tick=11075446604] :[tick=11075561478]  [tick=11075676860] e[tick=11075794109] x[tick=11075908503] c[tick=11076022863] e[tick=11076140297] p[tick=11076256973] t[tick=11076370911] i[tick=11076485805] o[tick=11076618388] n[tick=11076734492]  [tick=11076849092] h[tick=11076963243] a[tick=11077080122] n[tick=11077193748] d[tick=11077307450] l[tick=11077424313] i[tick=11077538753] n[tick=11078303159] g[tick=11078351365] 
[tick=11079009474] P[tick=11079038275] A[tick=11079086828] S[tick=11079135394] S[tick=11079186992] :[tick=11079233909]  [tick=11079281808] s[tick=11079330291] e[tick=11079378638] p[tick=11079426830] a[tick=11079477530] r[tick=11079525946] a[tick=11079577843] t[tick=11079624617] e[tick=11079674988]  [tick=11079722380] J[tick=11079771926] A[tick=11079825511] R[tick=11079872805]  [tick=11079921115] c[tick=11079970585] l[tick=11080018320] a[tick=11080065022] s[tick=11080113149] s[tick=11080181583]  [tick=11080229069] l[tick=11080276293] o[tick=11080325515] a[tick=11080375721] d[tick=11080422041] i[tick=11080469673] n[tick=11080517556] g[tick=11080565023] 
[tick=11081296104] P[tick=11081321556] A[tick=11081366643] S[tick=11081413942] S[tick=11081457905] :[tick=11081502029]  [tick=11081547111] r[tick=11081595110] e[tick=11081639899] f[tick=11081685815] l[tick=11081730432] e[tick=11081778306] c[tick=11081822793] t[tick=11081866777] i[tick=11081911552] o[tick=11081956078] n[tick=11082000859]  [tick=11082045649] i[tick=11082091361] n[tick=11082159854] v[tick=11082204531] o[tick=11082248492] c[tick=11082293401] a[tick=11082339547] t[tick=11082398575] i[tick=11082443465] o[tick=11082488056] n[tick=11082535493] 
[tick=11084498937] P[tick=11084648034] A[tick=11084693300] S[tick=11084739407] S[tick=11084784166] :[tick=11084828716]  [tick=11084872964] J[tick=11084920155] a[tick=11084964037] v[tick=11085008098] a[tick=11085048940]  [tick=11085089274] t[tick=11085130099] h[tick=11085170715] r[tick=11085210777] e[tick=11085254809] a[tick=11085295728] d[tick=11085335929]  [tick=11085376320] s[tick=11085440157] t[tick=11085480959] a[tick=11085521558] r[tick=11085561582] t[tick=11085604515] /[tick=11085644150] j[tick=11085683971] o[tick=11085724343] i[tick=11085764999] n[tick=11085806453] 
[tick=11085850081] P[tick=11085892598] A[tick=11085935840] S[tick=11085975524] S[tick=11086015442] :[tick=11086055831]  [tick=11086114179] a[tick=11086177327] l[tick=11086227238] l[tick=11086281033] o[tick=11086330661] c[tick=11086380885] a[tick=11086431217] t[tick=11086481743] i[tick=11086535163] o[tick=11086584624] n[tick=11086634872]  [tick=11086686261] 5[tick=11086758027] 1[tick=11086810913] 2[tick=11086861527]  [tick=11086911458] K[tick=11086961528] i[tick=11087011831] B[tick=11087061836] 
[tick=11087172420] Exception threw: java/lang/RuntimeException: FAIL: exclusive file creation
    at DiagnosticSmoke.check(DiagnosticSmoke.java:9)
    at DiagnosticSmoke.main(DiagnosticSmoke.java:33)

[tick=11087201736] call_main -> 1
[tick=11087254132] JVM teardown begins
[tick=11089677342] JVM teardown completed
[tick=11089835406] Java suite return=1 (confirm every PASS line)
[tick=11413214530] Clean exit: java-test
```
SHA256: `417e1e607098118ead6c13db3132f101a9f37360a5b582eddb19424f577181aa`

### switch-diagnostics.log
```text
[tick=9443035613] 
SESSION start tick=9443030779 app=switch-diagnostics version=0.1.0 source=e08f36a9d19cf461312f87a866f9bb1f39d57d98 | hardware status: NOT TESTED
[tick=9443163398] Applet type=0 (Application=0); firmware=21.2.0
[tick=9443287549] Log: sdmc:/switch/mc-runtime/logs/switch-diagnostics.log (open)
[tick=9848144520] SD write/read/compare: PASS; remove=0 errno=17
[tick=10148575793] Process memory: total=3444572160 used=3440488448 bytes rc=0x0/0x0
[tick=10148820340] Process limit minus current use=4083712 bytes (not JVM heap)
[tick=10148938306] Newlib malloc arena=14188544 allocated=14166768 free-in-arena=21776 bytes
[tick=10149060277] Kernel-used memory includes reserved heap; arena free space is separate.
[tick=10149531512] 4 MiB allocation/write/read/free: PASS
[tick=10391774269] threadCreate=0x0
[tick=10392017860] thread start/join=0x0 sum=500500 expected=500500: PASS
[tick=10725534782] Clean exit: switch-diagnostics
```
SHA256: `d7c534dd873977b8c94c5267a7b55ef54fa02f8e57e9d75db87b854629dcb636`

Analysis:
Confirmed source finding: FileSystemPosix.isAbsolute accepts only a leading slash, so the sdmc:/ absolute device URI is treated as relative and FileSystemImpl.getFullPath prepends the startup directory. The launcher already sets startup_dir to that same device directory. Native libc fopen(sdmc:/...) itself works in the SD roundtrip. The test also used a fixed java-smoke.txt and unchecked mkdirs, making subsequent diagnostics ambiguous when a file survives an earlier failure.

Requested action for java-switch:
Patch the maintained Java8 class-library source in a generated copy (keep pristine upstream source immutable), recognize supported device absolute paths, use owned unique diagnostic paths, and test actual native exclusive-file behavior. Preserve preexisting data and Java File.createNewFile semantics. Acceptance: genuine miniJVM host regression with a simulated sdmc: device path, then physical java-test A reaches DIAGNOSTIC SUITE PASS and reports cleanup. Do not close on host-only success.
