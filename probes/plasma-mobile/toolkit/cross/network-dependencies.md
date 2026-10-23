# Qt networking prerequisites on EmberBSD

The current target packages use curl 8.23.0nb1, libidn2 2.3.8,
GSettings desktop schemas 51.0 and libproxy 0.5.12. Their build and test
executables are cross-compiled on macOS with GCC 16.2. The CM5 only runs
those executables. This acceptance does not establish a Qt or Plasma session.

The [network delta](../current-network-deps.patch) records the original GNU
and GNOME archives and SHA256. The [libproxy delta](../libproxy-cross.patch)
retains the pinned upstream release and records its original archive and hash.
Both use pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`.
Apply each toolkit delta after its common graphics delta.
Changes are AI-assisted EmberBSD work, not accepted upstream patches.

## Cross-build repairs

Curl's OpenSSL configure path must include the target sysroot. Its installed
`curl-config` and `libcurl.pc` must instead describe the target installation.
The common cross recipe removes the build sysroot and selects the target
GCC16 driver for `curl-config --cc`; historical `--configure` arguments remain
historical. Literal path replacement handles metacharacters and an empty
replacement source safely.

Libproxy and GSettings use the common native introspection generators and
real target GType query runner. The complete toolkit export keeps both
`GDesktopEnums-3.0.gir` and `GDesktopEnums-3.0.typelib` in native and cross
packages. Apply its schema delta after the common graphics delta. The common
runtime profile alone does not require these optional bindings.
The toolkit libproxy delta also restores the complete profile after the
common runtime delta. It keeps GIR and typelib data in native and cross builds.

The temporary libproxy query links and loads
both in-tree libraries, including its private backend. This fixes the failed
GIR link without adding build paths to installed library RPATHs.

Libproxy's `doc` and `vala` package options default to enabled. They select
native documentation/Vala generators. Cross builds may select already-built
`EMBERBSD_GI_DOCGEN_HOST` and `EMBERBSD_VALA_HOST` prefixes; configure verifies
gi-docgen 2026.1 and Vala 0.56.19 before using them. Vala reads GIR data from
the target sysroot. Set `PKG_OPTIONS.libproxy=-doc -vala`
for a desktop runtime package without those optional files. This keeps the
headers, GIR/typelib, GNOME/KDE/environment/portal configuration backends,
Duktape PAC runner and curl support. It avoids a documentation-only Graphviz
build in the desktop's dependency path.

## Reproduce the focused checks

From the Ports root, after preparing the `plasma-mobile` export:

```sh
python3 probes/plasma-mobile/toolkit/tests/graphics-export.py \
    --sdk-source /absolute/EmberBSD-SDK --bmake /absolute/native/bmake \
    --makeconf /absolute/mk.conf --pkgsrc /absolute/prepared-pkgsrc \
    --work /absolute/new-export-check
DIGEST=/absolute/native/digest \
sh probes/plasma-mobile/toolkit/tests/network-deps-source.sh \
    /absolute/distfiles /absolute/prepared-pkgsrc /absolute/new-source-check
BMAKE=/absolute/native/bmake \
sh probes/plasma-mobile/toolkit/tests/curl-cross-metadata.sh \
    /absolute/prepared-pkgsrc /absolute/new-metadata-check
sh probes/plasma-mobile/toolkit/tests/network-cross-consumer.sh \
    /absolute/cross-tools /absolute/sysroot /absolute/new-network-consumer
sh probes/plasma-mobile/toolkit/tests/libproxy-cross-consumer.sh \
    /absolute/cross-tools /absolute/sysroot /absolute/patched-libproxy-source \
    /absolute/new-libproxy-consumer
```

The export check applies the common and toolkit patches with zero fuzz.
It checks native and cross package metadata without building a package.
It reports missing GI query inputs separately. It does not supply a target
runner or establish target execution. The check also covers libproxy with
default options and with both optional data sets disabled. The existing libnotify native and cross introspection
defaults remain unchanged.

Execute the resulting ELF files with the existing
[GI target query runner](../../../../pkgsrc/devel/gobject-introspection/files/target-query.py)
and its configured build root/sysroot/SSH destination. Both executables run
without arguments. The runner records the exact selected ELF dependency
hashes, bounds execution, verifies unchanged inputs and removes remote files.
Compilation remains on the development host.

The network test requires `C.UTF-8` on the target. Libcurl's libidn2 backend
interprets names using the current locale; feeding UTF-8 under `C` is invalid.
See [upstream URL encoding requirements](https://curl.se/libcurl/c/CURLOPT_URL.html).
The test verifies exact library versions, SSL/IDN/HTTP2 feature availability,
IDN conversion through both APIs, escaping and invalid URL rejection. It
makes no network requests and does not test a TLS or HTTP/2 transfer.

## Recorded result and limits

On 2026-10-11, the curl, libidn2, GSettings and libproxy packages passed normal
AArch64 package staging, file and runtime-search-path checks on macOS.
Source-delta reproduction, archive and patch hashes, zero-fuzz application,
exact prepared-file comparisons and repeated-patch rejection passed.
The curl metadata regression also passed, including an idempotent second run.

On 2026-10-20, curl was updated from 8.22.0 to 8.23.0nb1 for
CVE-2026-92392. Upstream lists 8.22.0 as affected and 8.23.0 as fixed.
The pinned pkgsrc options enable HTTP/2 by default. The source regression
verified the 8.23.0 archive hashes, exact prepared Makefile and distinfo, and
zero-fuzz application. `show-depends` resolved GCC16, libidn2, nghttp2 and
zlib. GCC16 cross packaging passed pkgsrc file, interpreter, permissions,
PIE, RELRO, RPATH and work-directory checks. The resulting package was
installed in the shared AArch64 sysroot with `pkg_add -U`; all seven recorded
reverse dependencies remain registered. The installed consumer cross-builds
as an AArch64 NetBSD 11.0 ELF and asserts curl 8.23.0 with SSL, IDN and HTTP/2.
`network-cross-consumer.sh` and the curl metadata regression pass. Cppcheck 2.22.0
compared upstream `lib/http2.c` from 8.22.0 and 8.23.0 using target headers,
GCC16 type definitions and the generated curl configuration. It reported 42
and 46 findings respectively. The common array-bound report is a false
positive: the copied GOAWAY reason is capped at `sizeof(scratch) - 1`. The
additional null-pointer reports concern the non-null easy-handle argument
passed through the HTTP/2 filter callbacks; the traced call sites use the
active transfer handle. GCC16 `-fanalyzer` on both releases and Clang Static
Analyzer on 8.23.0 reported no findings. No diagnostic was suppressed.
The 8.23.0 consumer has not yet been executed on the target; the earlier
CM5 run below used the previous curl 8.22.0 package.

On CM5 Rev 1.0 (BCM2712D0, Waveshare CM5-NANO-B), the network consumer passed
against the earlier curl 8.22.0 payload. All three upstream libproxy API tests
passed: proxy lookup, boxed-object copy and freeing a null proxy list.
The real libproxy GType query completed and generated GIR/typelib data.
These runs used isolated copies of the selected sysroot libraries; they do
not claim that the whole desktop dependency set is installed on the board.

Cppcheck and GCC16 checks of the new network consumer passed. Cppcheck's full
libproxy compilation-database analysis stops while parsing the selected GLib
headers; it is not a clean analysis result. The port changes Meson/package
files and leaves the C sources unchanged. Valgrind is unavailable on the
current macOS/AArch64 and EmberBSD/AArch64 setup; no Memcheck pass is claimed.
PAC execution, desktop-specific configuration, schema use in a live session,
full upstream suites and installed-package lifecycle acceptance remain open.

Final cross-package SHA256 values (binaries remain outside Git):

```text
b9145c6e621873fe8fe67cd5191929eb2514efbfd6a4b35eb784ca955236f3e2  curl-8.23.0nb1.tgz
363a85fdbde9b6c7f36329471327a2b857ed277437d92ea607c8b875dc618627  libidn2-2.3.8.tgz
dd7a34aa08d5eccf99818b0269870d7148a4ab33c84e53537834469b9c456db9  gsettings-desktop-schemas-51.0.tgz
aef773ad1eeabc4f629649acfe9374c4477c8f7e9bedcb2332784f7181141127  libproxy-0.5.12nb5.tgz
```
