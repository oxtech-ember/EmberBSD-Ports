# Current editline dependency

This canonical recipe supplies the OS base library and replaces `devel/editline` in the exported tree.
It selects libedit 20260512-3.1, released on 2026-05-12.
The upstream download page lists it as current on 2026-10-14:
<https://thrysoee.dk/editline/>.

`Makefile` selects the archive. `distinfo` records its hashes and every patch.
The SDK source preparer verifies both inputs and applies all recipe patches.
The license remains modified BSD.

The recipe comes from pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`.
All four inherited patches apply without fuzz to this current release:

- `patch-libedit.pc.in` retains the pkgsrc readline header search directory.
- `patch-src_sys.h` retains Darwin header declarations and removes conflicting SunOS declarations.
- `patch-src_terminal.c` retains the illumos termcap declaration fix.
- `patch-src_terminal.h` removes duplicate SunOS declarations.

The local `patch-configure.ac` adds detection of the upstream `libncursesw` name.
The existing library fallbacks remain available. Current pkgsrc names its
wide ncurses library `libncurses`; its normal buildlink transform handles both names.
The recipe requires ncurses 6.6 and GCC 16.2. Autoreconf regenerates configure.
An EmberBSD base built from these sources installs the exact recipe `distinfo`
at `/usr/share/emberbsd/ports/editline.distinfo`. Consumers use that base library
only when the marker matches this recipe and the base headers and library exist.
The base retains its OS ABI and SONAME. It is not replaced by the portable package.

The common EmberBSD defaults identify NetBSD-ABI package builds with
`EMBERBSD_PORTS=yes`. A stale or unmarked base in that context stops the build.
Rebuild the base from the current recipe before building its consumers.
The exported tree marker `EMBERBSD-PKGSRC-REVISION` also identifies a NetBSD-ABI
EmberBSD build without that profile setting. An installed source marker identifies
the target when the recipe is used outside the exported tree.
`PREFER.editline=pkgsrc` is rejected for an EmberBSD target because it would
install a second provider. Other systems can build the portable package.
Direct builds of this portable package also stop for an EmberBSD target.
Use the SDK source preparation and native base build instead.
The marker records source identity; release checks must also verify installed
library bytes and the consumers' loaded library.

The local `patch-src_filecomplete.c` and `patch-src_readline.c` release
generated completion strings when result allocation fails. The former also
handles failure to allocate the common prefix. The allocation-failure check
links the real static library with allocator wrappers. It rejects both
unpatched implementations, then tests five injected failures and normal completion.

The history parser repair in `patch-src_readline.c` preserves buffer ownership
when allocation fails or substitution syntax is incomplete. It reserves space
for the search-pattern terminator. `files/history-allocation.c` includes the
actual configured `readline.c` translation unit. Its allocator always moves
resized buffers and checks ownership on every exit. Run it with `ownership`
or `boundaries` to isolate failure paths and exact allocation boundaries.

The local `patch-src_el.c` keeps the `secure_getenv` fallback private.
This preserves the base library ABI when the target libc lacks that function.
Run `tests/private-symbols.py --nm /absolute/nm /absolute/libedit.so.3`
against the actual built library. The check also accepts the real `el.o`.
The unpatched fallback must fail the check when it is compiled on that target.

The local patches and control checks were prepared with AI assistance.
They have not been submitted upstream.

Run the installed consumer and staged lifecycle check from the profile:

```sh
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK \
  sh profiles/shells/editline-control.sh /absolute/work /absolute/current-ncurses-prefix /absolute/libedit.tar.gz
sh profiles/shells/analyze.sh /absolute/work editline
```

Use an empty work directory, current GCC16/autotools, and Valgrind on PATH.
The ncurses prefix must contain the current 6.6 wide library and headers.
The command preserves all default libedit features and builds upstream examples.
Upstream `make check` defines no test cases in this release.
The additional consumer checks history, narrow/wide tokenization, invalid input,
line input, EOF and repeated cleanup through installed headers and the shared library.
The script verifies staging, installation, removal, reinstallation and Valgrind Memcheck.
The completion regression also runs under Memcheck. It frees every allocation.
These are host controls. They do not establish native EmberBSD package acceptance.

## Analysis boundary

The Linux/GCC 16.2.0 control records 61 C compiler invocations for 32 files.
This includes the three upstream examples. PIC and static objects retain their
actual feature options and headers. Path analyzers replace optimization with
`-O0`; Clang uses GNU C23, matching the GCC16 default. Cppcheck uses its normal
branch limit and records each coverage limitation. The upstream C baseline and inherited platform patches
produce identical diagnostics with the same configuration:

| Analyzer | Baseline diagnostics |
| --- | --- |
| Cppcheck 2.22.0 | 2 errors, 6 warnings, 2 portability, 1276 style, 22 information |
| GCC 16.2.0 `-fanalyzer` | 19 reports at 11 distinct locations |
| Clang 23.1.3 Static Analyzer | 32 reports at 17 distinct locations |

All GCC and Clang commands finish successfully. Diagnostic findings remain open;
the Cppcheck command correctly returns failure when it reports findings.
The baseline retains the configured ncurses detection and generated headers.
Only the three inherited C portability patches are reversed for that comparison.

The two completion repairs pass a fresh build and causal failure tests.
Repeated analysis of their four PIC/static commands removes the Clang completion
allocation leak. It adds no diagnostic. Other source files retain the baseline findings.
No warning category or assertion is disabled.

Several inherited diagnostics have specific modeling limits. Cppcheck treats
`MB_LEN_MAX` as 1 through GCC header forwarding; the actual compiler gives 16.
Its `%zu` warning conflates Linux `size_t` with its identical `unsigned long` type.
The `reallocarr` pointer-size copies transfer pointer values through an output
argument; they do not copy pointed-to data. The callback line buffer transfers
ownership to the readline application callback. No suppression masks these reports.

Remaining readline error-path and upstream-example findings need separate
triage and regressions. In particular, example directory-open and multibyte
conversion failure paths are outside the installed-consumer checks above.
This control does not claim a clean analysis of the complete upstream library.

## Provider and export regressions

Run the actual BSD make fragments with the pinned pkgsrc framework and real
`pkg_admin` matcher. The tests create and remove only their own temporary trees.
They do not install a package or change the base system.

```sh
python3 pkgsrc/devel/editline/tests/builtin.py \
  --bmake /absolute/bmake --pkg-admin /absolute/pkg_admin \
  --pkgsrc /absolute/pinned-pkgsrc --work-parent /absolute/temporary
python3 pkgsrc/devel/editline/tests/recipe.py \
  --bmake /absolute/bmake --pkg-admin /absolute/pkg_admin \
  --pkgsrc /absolute/pinned-pkgsrc --work-parent /absolute/temporary
python3 pkgsrc/devel/editline/tests/export.py \
  --pkgsrc /absolute/pinned-pkgsrc --work-parent /absolute/temporary
```

The portable source control requires a clean Ports checkout and the SDK source
preparation command. It keeps the verified source tree immutable and uses a
separate mutable copy for Autoconf and compilation.
