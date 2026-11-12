# Snapshot 6 module audit evidence

Text-only extracts for [`docs/MINECRAFT_RUNTIME_GAPS.md`](../../MINECRAFT_RUNTIME_GAPS.md).
The official snapshot client and manifest JARs remain in `/tmp/r4-mc-reference`;
this directory contains no game binaries or assets.

- `reference.txt`: immutable metadata/client/runtime identifiers and hashes.
- `jdeps-client-reduced-modules.txt`: reduced module output from the client JAR.
- `jdeps-client-module-refs.txt`: command and selected class-level module refs.
- `jdeps-manifest-classpath-modules.txt`: full static module inventory across
  the client and manifest-selected library JARs.
- `javap-main-entry.txt`: bytecode excerpt for ordering and optional profiler paths.
- `javap-jvmprofiler.txt`: module-presence check and the official no-op fallback when JFR is absent.
