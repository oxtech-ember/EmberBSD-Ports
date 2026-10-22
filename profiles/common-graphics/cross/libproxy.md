# Libproxy curl option types

The common libproxy 0.5.12nb5 recipe uses `long` values for three variadic
curl options. The values remain `1`, `1` and `30`.
[CURLOPT_NOSIGNAL](https://curl.se/libcurl/c/CURLOPT_NOSIGNAL.html),
[CURLOPT_FOLLOWLOCATION](https://curl.se/libcurl/c/CURLOPT_FOLLOWLOCATION.html)
and [CURLOPT_CONNECTTIMEOUT](https://curl.se/libcurl/c/CURLOPT_CONNECTTIMEOUT.html)
require `long`. Global revision 5 applies to native and cross packages.
The existing cross selection of optional bindings and documentation is unchanged.
The patch is AI-assisted and has not been submitted upstream.

## Actual-source regression

Use [libproxy-pac-download.c](../tests/libproxy-pac-download.c) with the actual
configured manager source and generated `px-backend-config.h`. Do not copy its
implementation into the test. Preserve the original build flags when compiling
the complete target translation unit with `-Werror=attribute-warning`.
The unpatched source must fail at all three options. The patched source must pass.

The following native Darwin command uses GCC16 and native GLib/curl headers.
Set `CC`, `NATIVE_PREFIX`, `LIBPROXY_SOURCE` and `LIBPROXY_BUILD` to their actual
paths. Use a new working directory for the test executable and temporary PAC file.
`LIBPROXY_BUILD` is the configured Meson output directory.

```sh
"$CC" -isysroot "$(xcrun --show-sdk-path)" -std=gnu11 -O1 -g \
    -Werror=attribute-warning -ffunction-sections -fdata-sections \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -fno-sanitize-recover=all -Wl,-dead_strip \
    -I"$LIBPROXY_SOURCE/src/backend" -I"$LIBPROXY_BUILD/src/backend" \
    -I"$LIBPROXY_BUILD" \
    -DEMBERBSD_LIBPROXY_MANAGER_SOURCE="\"$LIBPROXY_SOURCE/src/backend/px-manager.c\"" \
    /path/to/EmberBSD-Ports/profiles/common-graphics/tests/libproxy-pac-download.c \
    -o libproxy-pac-download \
    $("$NATIVE_PREFIX/bin/pkg-config" --cflags --libs glib-2.0 gobject-2.0 gio-2.0 libcurl)
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ./libproxy-pac-download
```

The test checks exact bytes from owned `file:` and `pac+file:` inputs and reuses
the real curl handle. It initializes only the manager fields used by the downloader.
It does not exercise the GObject lifecycle, failure paths or external networking.
The source and test pass this native GCC16 ASan/UBSan check. Dependency DSOs are
not instrumented. Darwin leak detection hangs in an independent empty-program
probe, so this check does not establish leak freedom. Valgrind is not supported
on this host. Installed target execution remains a separate acceptance gate.

## Source analysis

GCC16 `-fanalyzer` and Clang Static Analyzer use the real target translation unit
and generated headers. GCC reports the three curl type warnings before the patch
and no diagnostics after it. Both path analyzers add no findings.
Clang is used only for analysis. Target objects use GCC16.

Cppcheck 2.22 cannot parse the unmodified GCC-preprocessed GLib cleanup macros
when a diagnostic pragma precedes a typedef. A supplemental input removes only
GCC diagnostic pragma text. It retains all C tokens, line markers, ABI, packing
and visibility directives. That input reports the same 16 warnings and 138 style
findings before and after the patch, with no errors or new findings. The exact
raw parser failure and inherited findings remain part of the acceptance evidence.
They do not establish that the complete library is free of defects.
