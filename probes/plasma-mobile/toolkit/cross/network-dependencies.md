# Qt networking prerequisites on EmberBSD

The current target packages use curl 8.22.0nb1, libidn2 2.3.8,
GSettings desktop schemas 51.0 and libproxy 0.5.12. Their build and test
executables are cross-compiled on macOS with GCC 16.2. The CM5 only runs
those executables. This acceptance does not establish a Qt or Plasma session.

The [network delta](../current-network-deps.patch) records the original GNU
and GNOME archives and SHA256. The [libproxy delta](../libproxy-cross.patch)
retains the pinned upstream release and records its original archive and hash.
Both apply after pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`.
Changes are AI-assisted EmberBSD work, not accepted upstream patches.

## Cross-build repairs

Curl's OpenSSL configure path must include the target sysroot. Its installed
`curl-config` and `libcurl.pc` must instead describe the target installation.
The common cross recipe removes the build sysroot and selects the target
GCC16 driver for `curl-config --cc`; historical `--configure` arguments remain
historical. Literal path replacement handles metacharacters and an empty
replacement source safely.

Libproxy and GSettings use the common native introspection generators and
real target GType query runner. The temporary libproxy query links and loads
both in-tree libraries, including its private backend. This fixes the failed
GIR link without adding build paths to installed library RPATHs.

Libproxy's `doc` and `vala` package options default to enabled. They select
native documentation/Vala generators. Set `PKG_OPTIONS.libproxy=-doc -vala`
for a desktop runtime package without those optional files. This keeps the
headers, GIR/typelib, GNOME/KDE/environment/portal configuration backends,
Duktape PAC runner and curl support. It avoids a documentation-only Graphviz
build in the desktop's dependency path.

## Reproduce the focused checks

From the Ports root, after preparing the `plasma-mobile` export:

```sh
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

Execute the resulting ELF files with the existing
[GI target query runner](../../../../profiles/common-graphics/recipes/devel/gobject-introspection/files/target-query.rb)
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

On CM5 Rev 1.0 (BCM2712D0, Waveshare CM5-NANO-B), the network consumer passed,\nincluding a repeat against the final curl nb1 payload. All three upstream libproxy API tests
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
5daca679a93add098434042060620f9cd3247ab967f49ceea3671941bcaf0399  curl-8.22.0nb1.tgz
363a85fdbde9b6c7f36329471327a2b857ed277437d92ea607c8b875dc618627  libidn2-2.3.8.tgz
dd7a34aa08d5eccf99818b0269870d7148a4ab33c84e53537834469b9c456db9  gsettings-desktop-schemas-51.0.tgz
aef773ad1eeabc4f629649acfe9374c4477c8f7e9bedcb2332784f7181141127  libproxy-0.5.12nb5.tgz
```
