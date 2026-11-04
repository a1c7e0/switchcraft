# Static Switch curl source provenance

The immutable toolchain contains switch-curl 7.69.1-5. Its package build time
matches devkitPro recipe revision 9937f6ac3171c5dba7324de8edb4e6cc3af3c01f.
UPSTREAM.json pins the original source, unmodified PKGBUILD and libnx SSL patch.
The patch selects libnx's normal SSL service, disables IPv6 and the threaded
resolver, and preserves certificate verification. It is not a Linux TLS backend.

Run `python3 scripts/prepare-curl-source.py` to verify/download the exact archive.
The launcher source bundle includes it as `third-party/curl-7.69.1.tar.xz`, together
with the tracked recipe and patch. Apply `patch -Np1 -i switch-curl.patch`, run
buildconf, source the devkitPro switchvars and use the configure flags in the
unmodified recipe. The pinned OCI toolchain supplies the compiler, libnx and zlib.
This records matching source provenance, not byte-identical rebuild evidence.
The archive's COPYING and patch notices apply; CURL-COPYING.txt is included in
the binary overlay. The recipe's legacy license label does not replace COPYING.
