# Snapshot 6 runtime module audit

This report records a static audit of the official `26.4-snapshot-6` client
and its pinned Linux manifest libraries against the current Switchcraft Java 25
image. It does not claim a new game launch or establish that every statically
referenced class is eagerly loaded on the ordinary title path.

## Immutable inputs

The checked-in official metadata is
[`26.4-snapshot-6.json`](evidence/official-metadata/26.4-snapshot-6.json).
It identifies `net.minecraft.client.main.Main`, Java 25, and client SHA-1
`8a97d5dafe80783525a2807b220527b65df724a5` (42,156,998 bytes). The downloaded
client matched that SHA-1; its SHA-256 is
`09d7e86508eb8b01c8e6ecc268ac1e4f8b9f0153c8fcff3201bf3f170199ca8b`.
The official metadata itself has SHA-256
`d6f3110b4bbf368cdcd6c02fded7eb80b0a84b4930d5b3f3538562b4295a2c95`.

At the time of this static audit, the java-switch revision pinned by `dependencies.lock.json` was
`4d362d4830cfa4e88313dadfcd3a865e826609a5`. The generated-input marker records
that same source revision and the runtime archive hash. This is a historical input record; the current integration pin is defined by the lock file. The verified image
package reports exactly two modules: `java.base` and `java.instrument` (39
hashed runtime image files). These identifiers and hashes are transcribed in
[`reference.txt`](evidence/minecraft-r4-module-audit/reference.txt).

The official client and manifest libraries were downloaded only to
`/tmp/r4-mc-reference`. The cache contains 67 manifest-selected library JARs
and the client; no assets were downloaded. No game binaries, libraries, or
assets were added to the repository.

## Static module findings

On the client JAR alone, `jdeps --print-module-deps` reports these reduced
module roots:

`java.base,java.desktop,java.management,java.naming,java.net.http,jdk.jfr`

Class-level analysis with the manifest classpath finds direct client bytecode
references to `java.xml`; the reduced root output does not show it.
Representative bytecode references are:

| Module absent from current image | Classes and API references in the client | What the reference indicates |
| --- | --- | --- |
| `java.desktop` | `Channel`, `OpenAlUtil`, `SoundBuffer`, `AudioStream` → `javax.sound.sampled.AudioFormat` | Java Sound types occur in audio code. This alone does not prove that a particular code path or audio provider is initialized first. |
| `java.management` | `SystemReport`, `Minecraft`, `Util` → `ManagementFactory`, MXBeans, `ThreadInfo` | System reporting, management metrics, uptime, and diagnostics reference management APIs. |
| `java.naming` | `ServerRedirectHandler` → `InitialDirContext`, `DirContext`, directory attributes | Multiplayer server redirect / DNS-related functionality references JNDI. |
| `java.net.http` | Realms `FileDownload` and `FileUpload` → `HttpClient`, `HttpRequest`, `HttpResponse` | Realms transfer code references the JDK HTTP client. |
| `java.xml` | `JUnitLikeTestReporter` → `DocumentBuilderFactory`, `TransformerFactory`, DOM | XML reporting code references the XML module. |
| `jdk.jfr` | `JfrProfiler`, JFR event and parser classes → `jdk.jfr` APIs | Profiling and event-reporting classes reference JFR. |

Analyzing every manifest-selected classpath JAR adds static references to
`java.compiler`, `java.datatransfer`, `java.logging`, `java.rmi`,
`java.scripting`, `java.sql`, `jdk.compiler`, `jdk.httpserver`, `jdk.javadoc`,
and `jdk.unsupported`. The artifact/class evidence narrows their meaning:

- ICU4J documentation taglet classes and Log4j annotation processors account
  for `java.compiler`; ICU4J documentation classes account for `jdk.compiler`
  and `jdk.javadoc`.
- JNA platform drag-and-drop classes account for `java.datatransfer`.
- Guava, Netty, JNA, Commons Compress, Log4j, and ICU4J include references to
  `java.logging`.
- Log4j's JDBC, scripting, and JMX-related classes account for `java.sql`,
  `java.scripting`, and `java.rmi`; Gson also includes SQL adapter classes.
- MSAL4J's interactive authorization listener references `jdk.httpserver`.
- Guava, Netty, LZ4, Log4j, JOML, and LWJGL use `sun.misc.Unsafe` from
  `jdk.unsupported`.

These are static references across full JAR contents, including tool, optional,
and feature-specific classes. The full list is not a claim that every listed
module is needed for the standard demo launch. In particular, `java.compiler`,
`jdk.compiler`, and `jdk.javadoc` references are confined to library tooling
classes in this analysis; the JFR call in `Main` is guarded by the
`--jfrProfile` option.

## Entrypoint ordering and limits of static analysis

`javap -c -p net.minecraft.client.main.Main` shows `Main.main` first calling
`SharedConstants.tryDetectVersion`, then parsing options. The `JvmProfiler`
call is conditional on the JFR option. It later calls `ClientBootstrap.bootstrap`
and, at bytecode offsets 1542–1548, constructs `Minecraft` after
`RenderSystem.initRenderThread` at offset 1539. See the verbatim excerpts in
[`javap-main-entry.txt`](evidence/minecraft-r4-module-audit/javap-main-entry.txt).

The first calls shown use `java.base` and classpath code. JFR is a known
conditional entrypoint when requested; it is not enabled by the standard
reference command. `JvmProfiler` itself checks for the `jdk.jfr` module before resolving
`FlightRecorder` and selects the game's own `NoOpProfiler` when it is absent;
see [`javap-jvmprofiler.txt`](evidence/minecraft-r4-module-audit/javap-jvmprofiler.txt).
The `jdeps` references do not establish when the VM resolves
or initializes the other classes, whether an optional code path is taken, or
which failure would occur first in the reduced image. No specific first module
blocker for a normal title launch is therefore claimed from this static audit.

## Integration status and remaining work

The last title reference remains the previously recorded Linux host run; it is
not Horizon evidence. No new title, launcher, or device execution is claimed
here. Current integration work reports a genuine cross-built JNI core with
1,957 JNI exports and two lifecycle entries, a real `SharedLibrary` adapter, and combined Y tests that enter
real JNI, SDL, FFM, and Vulkan code. Those new paths remain untested on Horizon.

Use this ordered follow-up:

1. Verify the packaged application classpath against the R3 missing
   `HelloHorizon25`, `Java25Smoke`, and `AgentSmokeAgent` classes, then run the
   standalone application and startup-agent paths on the device. A VM
   `vm-ready` marker alone is not an application or agent pass.
2. Exercise the actual native-provider families on device and close the
   cross-build-to-runtime gap: complete SDL coverage, then Vulkan and VMA
   services, plus each native family the title reaches. JNI symbol coverage
   or a resolver entry is not proof of provider behavior.
3. Add or enable only the JDK modules needed by demonstrated title paths, with
   genuine bytecode, native libraries, service registrations, and provider
   implementations. Inclusion of module classes in an image does not supply
   native services. In particular, do not represent AWT/JavaSound,
   socket/TLS, JFR, or other provider functionality with empty or fake module
   stubs.

Historical Linux title evidence and current device results remain described in
[`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) and the dated device
feedback reports. Keep the host and Horizon claims separate.
