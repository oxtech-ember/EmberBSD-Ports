# Shared bundled nawk

Origin: EmberBSD adaptations are AI-assisted. Original licenses remain intact.

The shared `lang/nawk` recipe selects One True Awk snapshot 20260426,
commit `5739fd79bcfc75ba7526773d0cf634521f8aca3c`.
The project [does not normally make formal releases](https://github.com/onetrueawk/awk/blob/20260426/README.md).
On 2026-10-24, the latest tag and upstream master name that exact commit.
The [official comparison](https://github.com/onetrueawk/awk/compare/20260426...master)
contains no later commits. No untagged fix or second snapshot is required.
`pkgsrc/lang/nawk/SOURCE.json` pins the archive URL, SHA256, size and file map.
The common source manifest pins the same bytes.

The replacement recipe supplies one bundled source tree to both the initial
bootstrap copy and the ordinary package extraction. The upstream pinned
pkgsrc recipe remains the immutable donor; `pkgsrc/replaces` selects the new
owner for every source composition. The common tools replacement floor
rejects installed nawk 20250726 and retains stronger caller requirements.
The bootstrap self guard prevents a circular awk dependency.
The fixed initial `darwin-installed-utilities-v1.json` profile describes its
original installed seed bytes. It is not ordinary provider admission and is
not rewritten as a receipt for this source update.

## Source adaptations

This snapshot adds upstream UTF-8 and CSV behavior. String operations count
Unicode code points. Review byte-count assumptions in consumers and run
upstream UTF-8/CSV tests during native acceptance.

The bundled `lib.c` preserves the [NetBSD ctype repair](https://github.com/NetBSD/pkgsrc/commit/7099c72bfddcbf9671d3a3478636cf05e73bbfaa).
Byte arguments use unsigned-char casts before classification or conversion.
The adaptation also covers new hexadecimal and format-width checks.
Wide-character operations keep their upstream behavior.

The local `split()` memory fix uses the existing checked `tostring()` helper
for source and separator copies. The CSV scratch allocation includes the NUL
byte and reports allocation failure through `FATAL`. The source gate binds
these exact changes to the pinned upstream bytes. Source checks do not
establish allocator-failure, sanitizer or package runtime acceptance.
Upstream source, licenses, FIXES, FIXES.1e and all test cases remain in the bundle.
The testdir harness requires explicit `CC`, `awk` and `oldawk` selections.
It honors `CPPFLAGS`, `CFLAGS` and `LDFLAGS` for its native echo helper.
No system compiler or reference awk is selected by default.
The manual uses the installed `nawk` command and retains the original book title.
The derived build Makefile retains the complete upstream Lucent copyright
and permission notice. The source gate compares that block byte for byte.

The build Makefile consumes pre-generated parser files and `proctab.c`.
It uses the selected compiler and linker flags in bootstrap and ordinary
builds. It does not build or run a host parser generator.

For a prepared native test tree, select an executable in `CC` and pass
flags separately. `CC` must not contain arguments or a command tuple.
Select the comparison interpreter explicitly through the SDK scope too.

```sh
cd /absolute/private/nawk-test-tree
CC=/absolute/selected/gcc16 \
CPPFLAGS='SELECTED_CPPFLAGS' CFLAGS='SELECTED_CFLAGS' \
LDFLAGS='SELECTED_LDFLAGS' \
awk=/absolute/private/nawk-test-tree/a.out \
oldawk=/absolute/selected/comparison-nawk \
    /absolute/selected/sh ./REGRESS
```

## Parser source preparation

The upstream makefile defaults to Bison. The BSD bundled integration selects
a pinned byacc to prepare `awkgram.tab.c` and `awkgram.tab.h`.
A selected native GCC16 builds upstream `maketab.c`; that helper produces
`proctab.c`. Do not reuse tables from the preceding source snapshot.

```sh
SELECTED_PYTHON -B pkgsrc/lang/nawk/regenerate.py \
    --source /absolute/Ports/pkgsrc/lang/nawk/files \
    --byacc /absolute/selected/byacc --cc /absolute/selected/gcc16 \
    --ccflags 'SELECTED_NATIVE_FLAGS' --work /absolute/new-generator-work
```

`--plan` prints argv without running generators or writing files.
Select and admit the interpreter, generator and GCC16 producer through the
SDK contract before an actual run. This helper does not qualify its tools.
It writes exact argv and diagnostics to private evidence.
Review and copy only the three generated source files and `GENERATED.json`
into `files/`. The public manifest records input/output hashes and tool
identities without private paths. Repeat generation must produce the same bytes.

## Source and metadata checks

```sh
SELECTED_PYTHON -B profiles/common-build-tools/tests/nawk-source.py \
    /absolute/distfiles/nawk-20260426.tar.gz /absolute/Ports/pkgsrc/lang/nawk \
    /absolute/new-source-check --bmake /absolute/selected/bmake
SELECTED_PYTHON -B profiles/common-build-tools/tests/nawk-metadata.py \
    --tools-mk /absolute/prepared-pkgsrc/mk/tools/replace.mk \
    --bmake /absolute/selected/bmake --pkg-admin /absolute/selected/pkg_admin \
    --work /absolute/new-metadata-check
```

`--source-only` verifies the pinned source, licenses, tests and BSD casts.
It does not accept missing generated data. The default gate also verifies
parser inputs, output hashes, token-table agreement and the actual make plan.
Negative controls reject changed archive bytes, lost casts, changed licenses,
changed pins and foreign source paths. Metadata controls reject the old tool
provider and preserve a stronger caller, the self guard and unselected tools.
These checks do not establish C compilation, analysis or target/native runtime.
