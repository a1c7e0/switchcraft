# Switchcraft launcher manager

Source: [`13e9cffdd740f94c4882d124e7f8a995aabf5193`](https://github.com/a1c7e0/switchcraft/tree/13e9cffdd740f94c4882d124e7f8a995aabf5193).
Runtime SDK pin: `b7c2ac7fd422bc2543e5c698db4e33a01cc0312d`, public ABI 1.
**All physical Horizon execution remains NOT TESTED.**

Download `switchcraft-launcher-foundation.zip` (the established filename now contains the manager milestone), verify `SHA256SUMS`, and merge its contents onto the SD root. Preserve profiles, saves, existing configuration and logs. It replaces only minecraft-launcher.nro and adds documentation, licenses and corresponding source. Use application-mode hbmenu.

The launcher provides controller/touch navigation, light/dark themes, system keyboard fields, Prism profiles and component metadata, online version catalog/install/repair, local cryptographic checks, safe task cancellation, folder import, settings-only duplicate, and archive/restore. Unsupported components and runtime blockers remain visible. Microsoft authentication, mod management and the full Qt task framework are not implemented. This NRO is VM-free and cannot launch Minecraft on Horizon.

See [the complete launcher test checklist](https://github.com/a1c7e0/switchcraft/blob/13e9cffdd740f94c4882d124e7f8a995aabf5193/docs/LAUNCHER_TESTS.md). The separate [Java25 base package](https://github.com/a1c7e0/switchcraft/tree/artifacts/java25-e08f36a) supplies the unchanged diagnostic NROs/runtime images and SDK source. Its Java/native tests remain required in fresh application processes. This overlay does not replace them.

Host acceptance: 55 launcher tests and 11 additional integration tests passed. The production installer downloaded and verified 5,459 artifacts / 599,338,934 bytes. Minecraft 26.4-snapshot-6 reached its Demo title on Linux Java25 with the strict Vulkan bridge on 2026-11-04; selecting Quit Game exited normally with status 0. These are host results. One additional archive-mutation audit could not be rerun because the original pinned runtime tarballs are absent from the restored workspace; its complete initial errors and environment explanation are retained in the source documentation.

The manifest records source/runtime revisions, source provenance, NRO format/build ID and hashes, and actual host acceptance evidence. `launcher-debug-symbols.zip` matches this NRO; `launcher-corresponding-source.tar.gz` includes the original curl source with its Switch SSL patch/recipe and the portable Prism port sources/notices. No game JARs/assets, desktop runtimes, Nintendo fonts, credentials or keys are distributed.
