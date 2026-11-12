# Fixed snapshot Demo launch path

The Instances detail page has an explicit **Play Demo** action for the pinned
`26.4-snapshot-6` profile. It runs a read-only installation verification on a
worker, checks the resolved plan for Java 25, the fixed official main class,
Vulkan, the classpath, the instance heap, and required files, then writes a
small atomic request under `switch/mc-runtime/tmp/`. The request contains the
instance ID and expected current paths; it does not contain a class name,
classpath, VM options, credentials, or a client JAR. The Java 25 application
consumes it once and reconstructs launch data from the saved launcher config,
the current Prism instance, the cached original metadata, and the install
verifier. A malformed, stale, or mismatched request is removed and rejected.

The main class is fixed to `net.minecraft.client.main.Main`. The Demo command
uses the official `--demo` flag and the official reference arguments for
`--graphicsBackend VULKAN`, the snapshot version, instance game directory,
assets directory, and asset-index ID. Its empty `--accessToken` matches the
existing official host Demo reference; this is not an authentication bypass
or a Microsoft account login. The instance's Java heap remains bounded by the
existing 128–1024 MiB profile policy, with a 64 MiB initial heap. Account
credentials are not accepted or stored by this flow. The JVM also runs in
headless AWT mode and selects LWJGL's upstream system allocator, which avoids
desktop jemalloc initialization on Horizon.

After `envSetNextLoad` accepts `switchcraft-java25`, the VM-free launcher exits
with its tasks joined. The Java 25 application releases the libnx console
framebuffer before Java can initialize SDL3/Vulkan, registers native JNI
symbols before the client starts, sets the process working directory to the
instance game directory, and attempts at most one VM in that application
lifetime. It consumes the pending request before starting the VM. A failed or
crashed attempt is not retried in place; review the saved logs and reopen the
application for another explicit attempt. Opening the Java 25 diagnostic with
no validated pending request still shows its A/X/Y diagnostic controls.

The launcher-to-VM handoff is implemented and host-tested, but Switch execution
of the launcher UI, queue handoff, Java startup, SDL/Vulkan client, and title
screen remains **NOT TESTED**. The host tests validate request construction,
validation, one-shot consumption, and rejection behavior; they do not emulate
the console. Record any later device startup and game results as separate
evidence.
