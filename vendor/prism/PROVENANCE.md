# Prism Launcher metadata port provenance

The upstream source tree is Prism Launcher commit `059e858e101edc9314ccb94aa48bd01b282539c5`.
The files in `upstream/` are unmodified originals copied from these paths:

| Original path | SHA-256 |
|---|---|
| `launcher/meta/JsonFormat.cpp` | `82d4bcade535ef466f380960b3ace16266f735f33f29965d90e8b35dd93b8818` |
| `launcher/meta/VersionList.cpp` | `fcb92472cb0a17dd7fd3c9417180d0e7c7c1e7e7fa1aa91c8e3852e265019f9e` |
| `launcher/minecraft/OneSixVersionFormat.cpp` | `ea943114d030e7566d1f93c0508d3bc3334ec15b2abfd725f644165b8edc768b` |
| `launcher/minecraft/VersionFile.cpp` | `9eb6ed49e2955edd3acc0e850fe5ac92772df36cbd5970d3dde13757a64da48b` |
| `launcher/minecraft/Library.cpp` | `ea809ec6dbc5782867bd3686ab8d5ca4353c6a2facbf64d2b78737e1155c0beb` |
| `launcher/minecraft/Rule.cpp` | `767e0ebb9356882a01d96c94a0a3747e10eea5f9e16d6e7cc68c8149c52f2568` |
| `launcher/minecraft/PackProfile.cpp` | `db875101f76a0aaa4325f5cf60cfe841b5e0ab25d330d88177fee11861ea0c51` |

The implementation in `src/prism_metadata.cpp` ports the format-version checks and
version-list time ordering from `JsonFormat`/`VersionList`, component-file ordering
and patch-before-cache lookup from `PackProfile`, and ordered component application,
requirements, conflicts, Maven-coordinate replacement, Minecraft-owned asset fields,
and added JVM arguments from `OneSixVersionFormat`, `VersionFile`, and
`ComponentUpdateTask`.

Supported offline subset: cached `formatVersion` 1 package indexes; `mmc-pack.json`
formatVersion 1 and ordered enabled/disabled entries; `net.minecraft` and `org.lwjgl3`
components; `requires` exact versions, advisory `suggests`, and `conflicts`; local
`patches/<uid>.json` override; component `libraries`, main class, Minecraft asset and
Java metadata, and `+jvmArgs`. `prism_components_for_version` selects cached exact or suggested dependency versions from a pinned vanilla metadata record, but does not choose latest versions. Missing cached metadata, conflicts, requirements,
unknown component UIDs, and unsupported operations fail explicitly. This port does
not perform network metadata fetching, dependency installation/latest-compatible
selection, arbitrary component types, jar mods, mod loaders, agents, Maven file
operations, tweakers, or Prism UI/task behavior. It does not include game assets,
JARs, accounts, or credentials.

The sources retain their upstream notices. GPL-covered Prism portions are under
GPL-3.0-only; included legacy MultiMC-derived portions retain their Apache-2.0
notices. Full license texts are in `licenses/PRISM-GPL-3.0.txt` and
`licenses/PRISM-APACHE-2.0.txt`.

## Real metadata validation fixtures

The pinned-profile fixtures under `tests/fixtures/prism/real/` are unmodified
metadata JSON fetched from the Prism metadata cache, not game binaries:

| Fixture | SHA-256 |
|---|---|
| `net.minecraft.json` (26.4-snapshot-6) | `2a5400ce3d80b79877803f63bc6b6e8d90a03568fea68b3fdfbea6b195b7f1c6` |
| `org.lwjgl3.json` (3.4.3) | `a7fb39cc0aaaf7c545667f570f3baaaf103e51974da45cf74dc92c112c083406` |
| `net.minecraft-index.json` | `ebe63e7f7fcbfa7444d92413f73bf7c9582111d60c60992423f8cfff766a3ec9` |

The fixture exercises the live component dependency (`net.minecraft` suggests
`org.lwjgl3` 3.4.3), `compatibleJavaMajors`, Maven mainJar reconstruction,
legacy `minecraftArguments`, and retained `+traits` / `+jvmArgs`. `XR:Initial`
is separately tagged `_prism_unsupported_traits` so the launch planner can fail
closed for unsupported XR launch behavior without erasing the source metadata.
The index API compares strictly validated Gregorian UTC instants, including explicit timezone offsets,
matching timestamp order rather than lexicographic string order. It rejects malformed dates and offsets.
