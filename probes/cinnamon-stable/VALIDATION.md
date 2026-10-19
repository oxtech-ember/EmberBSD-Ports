# Cinnamon stable port validation

## Cinnamon Menus 6.6.0nb3

The source is the upstream `6.6.0` tag (SHA512
`65402ac018ca4dfd5d7b26808dc665916564b2d2dcac72a8b57125e903bd95c1ecf4c35efb8088fcffd5fab3f394e85d3643816fae4e055d85a3f9622148b756`,
96,541 bytes). The package was cross-built for EmberBSD/AArch64 with GCC
16.2.0, GLib 2.90.1, GObject Introspection 1.86.0 and Meson 1.12.1. All
10 Meson build steps completed. Package checks passed for the headers,
shared library, GIR, typelib, permissions, PIE, RELRO, runtime search
paths and work-directory references. Pkgsrc reported three empty fake-home
directories after the build. The package archive is 71,550 bytes and its
SHA256 is
`d737b5631c2139299e3419045dce77bb2d8819f536ede46a0b8d568eca69f87e`.

The upstream GIR omitted the `GioUnix` namespace, which left the
`launch_uris_as_manager` callback type unresolved. Its GTK-Doc closure
annotations also described the user-data arguments instead of their
callbacks. The patch adds `GioUnix-2.0` to the GIR includes and puts each
closure annotation on the matching callback. A regression check accepts
the packaged GIR and rejects the `nb1` GIR because `GioUnix` is missing.
The patch also raises the upstream Meson minimum to 1.2.0 because the
cross-build environment passed to `gnome.generate_gir()` uses the Meson
`env` argument, which was not available under the previous declared
minimum.

`verifypc` exited successfully with `zlib` ignored because the target base
system provides its `.pc` file. The sparse host pkgsrc copy does not
contain the GCC16 package PLIST, so the checker prints lookup warnings for
that external compiler provider. The upstream Cinnamon Menus source has no
executable unit-test suite; no VM runtime acceptance is claimed.

The local compatibility patch uses `g_string_free_and_steal()` and assigns
the returned buffer to the menu tree. This preserves ownership and uses the
current GLib transfer API. GCC 16.2.0 `-fanalyzer` analyzed all seven C
translation units against the upstream archive and the patched source. The
upstream build reported one ignored-result warning in `menu-layout.c`; the
patched build reported no analyzer findings.

Cppcheck 2.22.0 analyzed all seven C translation units with the actual
pkgsrc compile commands, target headers and GCC16 predefined macros. The
upstream and patched runs each reported 57 findings with no finding delta.
One `legacyUninitvar` report in `desktop_entry_copy()` is a Cppcheck false
positive: the unreachable branch calls GLib's `g_assert_not_reached()`,
which expands to the declared `G_NORETURN` `g_assertion_message_expr()`.
The analysis uses one file-and-line suppression for that report. It does
not add a source suppression or disable a diagnostic category. The unchanged
`uselessAssignmentPtrArg` warning is in the common GLib 2.90.1 header.

## Cinnamon Desktop 6.6.2nb1

The source is the upstream `6.6.2` tag (SHA512
`0637056bc92373909c2ec74bd362819e8fa27092cbcbc79d28a492ac222edd7e7e5e6a6187d1be19084f169a452e64eee5986933c64f8c4f23d425037e6eec0a`,
508,681 bytes). The package cross-built for EmberBSD/AArch64 with GCC 16.2.0.
All 151 Meson build steps completed. The package archive is 263,281 bytes
with SHA256
`e6430c4905d2f9119ed2a8e3613f5bbe0a1e2c6bfd5956fd8c1c32b7ffcca5c5`.

The port omits the GTK 3-only background, RandR and thumbnail components.
The `check-no-gtk3.py` regression check passed against the package archive,
pkg-config log, Meson setup log and Meson dependency record. It checks GIR
and typelib contents, pkg-config metadata and the package file list. A
negative control that adds `gtk+-3.0` to the pkg-config log is rejected.
This proves the Cinnamon Desktop package has no GTK 3 dependency; it does not
claim runtime acceptance of a complete Cinnamon session.

Cppcheck 2.22.0 analyzed all 21 C translation units with the Meson compilation
database, target headers and GCC16 predefined macros. Upstream and patched
runs each reported five findings, with no finding delta. The two
`autoVariables` reports in `gnome-languages.c` are false positives for
`g_steal_pointer()` transfers: the function returns the allocated capture
string and clears the automatic-cleanup owner. The two
`CastAddressToIntegerAtReturn` reports are the paired `GPOINTER_TO_INT()`
reads of integer counters stored with `GINT_TO_POINTER()`. The unchanged
`uselessAssignmentPtrArg` report is in the common GLib 2.90.1 header.

GCC 16.2.0 `-fanalyzer` analyzed all 11 patched C translation units and
reported one `-Wanalyzer-null-argument` at `gnome-languages.c:300`; the same
report occurs in the upstream source. This is an inter-library contract
false positive for the selected EmberBSD source revision
`c31375ea778b72aed57871c2e9e4aeb4b386e76d`: its
`lib/libc/locale/nl_langinfo.c` maps `CODESET` to `LC_CTYPE` and returns an
empty string if the stored codeset pointer is null. Therefore
`nl_langinfo_l(CODESET, locale)` returns a non-null string for a valid locale.
No analyzer suppression or source change was added for this finding.
Clang Static Analyzer 21.0.0 analyzed all 11 patched translation units with
no diagnostics. Its upstream comparison, like GCC's, could not compile the
upstream-only GDK header and an ungenerated D-Bus header without restoring the
GTK 3 dependency.

The host `verifypc` check is incomplete because `pkg_admin` is unavailable on
the build host; GCC16 provider PLIST lookups also warn in the sparse host
pkgsrc tree. The build emitted an existing unused-variable warning in
`gvc-mixer-control.c` and compatibility warnings from target `libm`. No VM
or full-session runtime acceptance is claimed.

## CJS 140.1 locale-array cleanup

The input is the upstream `140.1` tag at
`3f8ca7c65bd1d8c4f1e93c984f179d44d71fcb65`.
The original source archive SHA256 is
`1e223ce6229a7dc926b5ec3ee42040f6848e466ab51eb36c415c283b0b03098c`.
The unchanged `libgjs-private/gjs-util.c` SHA256 is
`7b63c7ebd13be82804901bbd101b17e56473510251cfc0b70f140d880b6efa73`.

| Check | Baseline | Repaired source |
| --- | --- | --- |
| Native Apple Clang 21.0.0, four cleanup cases | Four failures | Four passes |
| Native ASan/UBSan, the same four cases | Four instrumented failures | Four passes |
| GCC 16.2.0 AArch64 compilation | Pass | Pass |
| GCC 16.2.0 `-fanalyzer`, target headers/options | No finding | No finding |
| Clang Static Analyzer 23.1.3, target headers/options | Null dereference | No finding |
| Cppcheck 2.22.0, target compilation database, Unix64 | One inherited header finding | The same header finding |
| EmberBSD 11/AArch64 VM, GCC16 target program | Empty array: SIGSEGV, status 139 | Four passes |

The four cases cover an empty array, one populated entry, all entries and
four thread exits. The harness uses the actual source helper bodies and the
same destructor callback convention as the production code.
The baseline failure is the causal control for the two-line repair.

Cppcheck's unchanged `uselessAssignmentPtrArg` finding is in the common
GLib 2.90.1 header `glib/gstrfuncs.h:568`. It does not originate in this
patch. This check does not suppress it. The common GLib provider owns any
follow-up review of that header finding. GCC's analyzer does not find this
defect; its empty output is not evidence that the baseline is correct.

The native compiler runs AddressSanitizer and UndefinedBehaviorSanitizer.
LeakSanitizer reports that leak detection is unsupported on this Darwin
host. No leak-check pass is claimed.
[Valgrind's supported platforms](https://valgrind.org/info/platforms.html)
do not include this macOS/arm64 host or EmberBSD/AArch64 target.
These runs are not Memcheck runs.

The VM cases execute a focused source-derived contract. They do not run the
complete CJS interpreter, a package lifecycle, JavaScript bindings, or a
Cinnamon session. Full CJS still needs the operating-system `uselocale()`
interface described in [README.md](README.md).
