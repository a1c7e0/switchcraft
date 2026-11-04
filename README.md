# Switchcraft launcher foundation

Source: [2041fe3](https://github.com/a1c7e0/switchcraft/tree/2041fe3), Prism port: 059e858e101edc9314ccb94aa48bd01b282539c5, Java SDK ABI 1 at b7c2ac7fd422bc2543e5c698db4e33a01cc0312d.

Download `switchcraft-launcher-foundation.zip` and verify its SHA-256 against SHA256SUMS. Merge its contents onto the SD root, preserving saves, profiles, configuration and logs. This replaces minecraft-launcher.nro and adds documentation, licenses and current launcher source. Use application-mode hbmenu. L/R switches section; D-pad/stick moves focus; A selects; B goes back; X creates an instance; + closes. System keyboard and touch are implemented but hardware untested.

The archive is an overlay for the [Java25 test package](https://github.com/a1c7e0/switchcraft/tree/artifacts/java25-e08f36a). Diagnostics and complete runtime images remain in that base package; this milestone does not rebuild or relabel them. Their unchanged SDK/runtime corresponding source is supplied in the base artifact set. The current launcher source and adapted Prism originals/licenses are included here and inside the SD overlay. The combined launcher is distributed under GPL-3.0-only with applicable Apache-2.0/MIT notices.

All Horizon UI/input/font/keyboard execution is **NOT TESTED**. The NRO remains VM-free and cannot launch Minecraft on Switch. PNGs are HOST UI PREVIEW renders from original display fixtures, not device screenshots or game execution evidence. Twenty-six relevant host tests passed; a live SHA256-verified Prism snapshot-6 metadata-to-instance-to-plan check passed. Full Qt networking, online game installation, account login and mod management have not been ported. See PRISM_PORT.md and the immutable source documentation for exact scope.

`launcher-debug-symbols.zip` matches this NRO. `manifest.json` records the NRO build ID, actual cached SDK archive/library hashes and source pins.
