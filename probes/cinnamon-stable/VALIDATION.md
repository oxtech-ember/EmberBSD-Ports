# CJS 140.1 locale-array cleanup

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
