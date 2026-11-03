# Switchcraft Java 25 hardware test artifacts

Source: [Switchcraft e08f36a9d19cf461312f87a866f9bb1f39d57d98](https://github.com/a1c7e0/switchcraft/tree/e08f36a9d19cf461312f87a866f9bb1f39d57d98). Java runtime: [b7c2ac7fd422bc2543e5c698db4e33a01cc0312d](https://github.com/a1c7e0/java-switch/tree/b7c2ac7fd422bc2543e5c698db4e33a01cc0312d).

These artifacts were cross-built and host-tested. Horizon startup, Java execution, JNI/FFM, agent instrumentation and Minecraft are **NOT TESTED**. The Minecraft title screen has not been reached. The package contains no game files or credentials.

After downloading all files in this branch, reconstruct and verify the two split archives:

```sh
sha256sum -c PART-SHA256SUMS
cat switch-minecraft-test-package.zip.part-* > switch-minecraft-test-package.zip
cat switchcraft-corresponding-source.tar.gz.part-* > switchcraft-corresponding-source.tar.gz
sha256sum -c SHA256SUMS
```

Unpack the SD package and follow its instructions and the source repository hardware test plan. Keep the original logs and crash reports. Source and debug symbols correspond to the binaries in this artifact set.
