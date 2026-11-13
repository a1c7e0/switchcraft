# Java 25 diagnostic menu

The combined `switchcraft-java25` application writes its detailed startup
diagnostics to `sdmc:/switch/mc-runtime/logs/switchcraft-java25.log`. After
startup checks, it replaces the scrolled console view with a short menu that
shows the source revision, hardware status, and every controller action. This
keeps the menu visible while waiting for input without adding repeated output
to the SD log.

Use application-mode hbmenu. A, X, Y, B, R, or L starts at most one VM attempt
in the current process; `+` exits without starting a VM. Start A, X, and Y in
separate fresh application processes. Close with `+` and reopen hbmenu before
another attempt. A validated pending Minecraft launch request continues to
autoexecute without pausing at this diagnostic menu. After a VM returns, the
existing result viewer remains active and waits for `+` to close the process.

The menu text is also covered by `tests/java25_menu_host.c`, which can be
compiled and run on a host without libnx. Host formatting checks do not verify
console readability or Java execution on a Switch; hardware status remains
NOT TESTED until physical-device evidence is collected.
