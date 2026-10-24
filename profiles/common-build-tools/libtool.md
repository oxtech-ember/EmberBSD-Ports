# Libtool 2.6.2

The common profile updates the pinned pkgsrc Libtool family to GNU Libtool
2.6.2. The same source release supplies the native target scripts and the
host-side cross Libtool used when building target shared libraries. GNU M4
1.4.21 is an explicit runtime dependency of installed `libtoolize`.

## Source and maintained patches

The original archive is downloaded from GNU; its URL and SHA256 are recorded
in [sources.tsv](sources.tsv). The exported recipe contains pkgsrc BLAKE2s,
SHA512, size and RCS-filtered patch SHA1 checksums. NetBSD pkgsrc identifiers,
authorship and licenses are retained. The refresh and target conversion are
AI-assisted EmberBSD changes, not submitted upstream.

Pkgsrc's maintained `manual-*` changes are refreshed against the current
source. Generated `configure`, `libltdl/configure` and `build-aux/ltmain.sh`
patches come from those maintained inputs. The update preserves pkgsrc's
platform behavior, shared-library naming, installed script layout and
Fortran/cross recipe composition. The Makefile installation-directory hunk
is applied to the current upstream rule.

Regeneration uses Autoconf 2.73 and Automake 1.18.1. Verify the exact generated
files rather than independently editing generated shell code:

```sh
PATH=/absolute/current-autotools/bin:$PATH \
DIGEST=/absolute/host/bin/digest \
sh profiles/common-build-tools/tests/libtool-source.sh \
    /absolute/export /absolute/distfiles /absolute/new-check
```

The gate verifies the archive and pkgsrc patch checksums, applies source and
manual series with zero fuzz, rejects repeated patch application and compares
regenerated configure/ltmain output byte for byte. This gate passed on macOS;
it does not substitute for installed target execution.

## GCC driver-prefix transport

The shared parser preserves GCC's joined `-Bprefix` and separate `-B prefix`
forms in shared-library commands. The separate form retains argument quoting.
The existing `-Bstatic`, `-Bdynamic` and `-Bsymbolic` paths stay unchanged.
Non-GCC configurations retain their earlier argument routing.

Before this fix, Libtool kept the prefix in compile and executable commands,
but omitted it from shared `compiler_flags`. GCC could then find the system
`ld` shim through PATH, despite an explicit configured `LD`. On Darwin, that
shim attempted an external xcrun cache write. Both links could still return
zero. Check the selected command and diagnostics as well as the exit status.

One maintained `manual-ltmain.in` patch supplies the fix. Its generated
`patch-build-aux_ltmain.sh` comes from the upstream shell-only
`build-aux/ltmain.sh` make target. No M4 input changes for this repair.
The packaged script must match that generated output exactly.
The native base, native Fortran and cross Fortran script revisions become
`2.6.2nb1`; cross base becomes `2.6.2nb2`. Rebuild the script providers and
consumers that used earlier configure results. Earlier package acceptance
records below apply only to their recorded inputs.

The common pkgsrc dependency rules require these revisions as additional
provider predicates. They preserve caller and platform requirements,
including a higher caller request with a lower platform floor. Cross
`autoreconf` also requires the repaired native Libtoolize provider.
The [provider metadata regression](tests/libtool-provider-floor.py) checks real
libiconv/libunistring queries against a registered old-provider fixture.
It also checks C/Fortran native/cross roles with BSD make and pkgtools.
No package is installed or replaced by this check.

Pkgsrc's post-configure `libtool-override` hook redirects project scripts to
the common installed provider. Its default depth covers libiconv, nested
libcharset and libunistring. `LIBTOOL_OVERRIDE` can name explicit project paths.
The packaged `share/libtool/build-aux/ltmain.sh` also supplies the same fix to
new projects through `libtoolize`. Do not add copies of the patch to consumers.

Use matching native configurations for the baseline and candidate scripts:

```sh
python3 -B profiles/common-build-tools/tests/libtool-driver-prefix.py \
    --baseline /absolute/baseline/bin/libtool \
    --candidate /absolute/candidate/bin/libtool \
    --cc /absolute/gcc16/bin/gcc --driver-prefix /absolute/native/bin \
    --host-abi /absolute/native-sdk --sandbox-profile /absolute/contained.sb \
    --pkgsrc /absolute/prepared-pkgsrc --bmake /absolute/native/bin/bmake \
    --shell /absolute/native/bin/mksh --work /absolute/new-results
```

The native Darwin regression builds and runs small GCC16 shared consumers.
Joined and separate prefixes must survive without external cache diagnostics.
Dry runs check C/C++, quoted paths, unchanged special flags and non-GCC routes.
A missing separate prefix must fail. The real pkgsrc override target also
checks the three project layouts against one common candidate provider.
This does not qualify a complete Libtool package, target runtime or SDK.

## Native Fortran SDK selection

For native GCC16 on macOS, use the existing `GCCBASE`,
`GCC_VERSION_SUFFIX=-16`, `USE_NATIVE_GCC=yes` and `USE_PKGSRC_GCC=no`
contracts. Select an installed SDK with `MACOSX_DEPLOYMENT_TARGET`.
The Darwin platform passes its selected `OSX_SDK_PATH` to both the `f77`
cwrapper and the legacy `FC` wrapper. C and C++ keep their existing flags.
Target NetBSD wrappers do not receive a macOS SDK.

Run the bounded platform regression from a pinned prepared pkgsrc source.
It applies the patch with zero fuzz, rejects a repeat, and compares real BSD
make results for native Darwin and both target architectures.

```sh
python3.15 -B profiles/common-build-tools/tests/darwin-fortran-sdk.py \
    --ports-source /absolute/EmberBSD-Ports --sdk-source /absolute/EmberBSD-SDK \
    --bmake /absolute/host/bin/bmake --pkgsrc-source /absolute/prepared-pkgsrc \
    /absolute/new-platform-check
```

A separate native GCC16.2 control compiles and links
[`native-sdk.f90`](../../probes/gcc16-fortran/native-sdk.f90).
On a host with a missing configured SDK, the original Fortran flags fail to
find `System`. The same command with `-isysroot` and the actual `xcrun` SDK
links an arm64 Mach-O executable. That executable was not run. This is a
native SDK transport check. Native Libtool package and tag acceptance remain
separate. No target SDK, compiler or runtime is changed by this check.

## Host and target scripts

The host `cross-libtool-base` dispatcher uses its configured cross prefix.
Its `shlibtool` must call the adjacent target-configured `libtool`, not the
native host `libtool`. The native `libtool-base` recipe retains its own prefix.

Check both recipes with existing native and cross Libtool installations:

```sh
BMAKE=/absolute/host/bin/bmake \
sh profiles/common-build-tools/tests/cross-shlibtool.sh \
    /absolute/export /absolute/cross-mk.conf \
    /absolute/export/cross/cross-libtool-base/Makefile \
    /absolute/host /absolute/new-dispatch-check
```

This AArch64/NetBSD check runs the actual generation and installation targets
in a private prefix. It compares executed `--config` results and rejects the
original wrong-prefix dispatcher. It also checks the shared-only tag.
It compiles no source and does not update any package database. The host cross
package must still pass ordinary package checks before installation.

The complete `cross-libtool-base` 2.6.2nb1 package passes ordinary checks
on macOS arm64. Its source recipe is from `c26300d`; the ELF checker guard
is from `4394b7e`. Normal package replacement and all 56 installed entries
pass. The installed dispatcher selects `aarch64--netbsd`, enables shared
libraries and disables static libraries. Native Libtool remains unchanged.
The package SHA256 is
`42458882623701b7d84cdba7d691961622119b08c1ba79a70e9644b330498823`.
This host-tool check does not establish a complete gettext or Fcitx package.

A native cross-tool package retains the host object format even when its
Libtool configuration describes ELF target libraries. The RELRO gate selects
its ELF backend only for ELF packages. It does not change `CHECK_RELRO` or
suppress target library checks. Test the gate with actual ELF shared objects:

```sh
BMAKE=/absolute/host/bin/bmake CHECK_AWK=/absolute/host/bin/nawk \
CROSS_AS=/absolute/cross/bin/aarch64--netbsd-as \
CROSS_LD=/absolute/cross/bin/aarch64--netbsd-ld \
READELF=/absolute/cross/bin/aarch64--netbsd-readelf \
sh profiles/common-build-tools/tests/relro-format.sh /absolute/export \
    /absolute/export/mk/check/check-relro.mk /absolute/new-relro-check
```

The native-script case keeps the RELRO policy enabled without invoking an
unavailable backend. The ELF cases accept RELRO and reject missing RELRO
through the ordinary pkgsrc error gate. The test runs no target program.

Cross configure must execute on the Mac, but installed `libtool`,
`libtoolize` and `shlibtool` must run on NetBSD. The scoped recipe converts
configured host shell, sed, linker and compiler paths to target paths. It
uses the selected `/usr/pkg/gcc16` compiler and runtime, not a second ABI.
Unconverted known build directories fail the conversion.

The target `/bin/sh` has no mksh `print` builtin, so the configured echo
operation uses portable `printf`. `max_cmd_len` is 196608: NetBSD 11's 256 KiB
ARG_MAX with the upstream BSD three-quarter safety margin. Querying host
`sysctl` during cross configure cannot establish this target value.

The [cross package profile](cross/README.md) separates host and target
package metadata and preserves the target CRT choice through compiler
wrappers. `run-libtool-tests.sh` exercises installed C11/C++20 shared and
static consumers, exception handling through a DSO, loaded GCC16 libraries,
libtoolize macro installation, shlibtool and uninstall. Run it in an EmberBSD
AArch64 guest after ordinary `pkg_add` installation, with a new output path.
Fortran consumer execution remains outside this acceptance gate.

The shared profile also selects the C Libtool tag explicitly in libiconv
1.19nb1's hand-written compile/link rules. This keeps the actual consumer
compiler when Libtool was configured with an additional language-standard
flag; it does not change the compiler or skip Libtool checks.

The pinned GTS 0.7.6 recipe disabled all Libtool tags. Libtool 2.6.2 then
failed to select its C compiler for the ordinary untagged compile command.
Passing `CC` to `--with-tags` is invalid because GTS uses that option only to
add secondary tags. The common-tools export removes the empty override, keeps
Libtool's default C tag and patches GTS's generated compile and link rules to
pass `--tag=CC`; it bumps GTS to nb9 and records the pkgsrc patch checksum.
This keeps the C-only build contract and the feature used by the host Graphviz
dependency. It does not disable the feature or suppress build checks.

Cppcheck 2.22.0 compares the 35 C translation units in the host GTS build
before and after this recipe-only change. Both runs report 122 diagnostics
with zero errors and the same diagnostic identifiers. The parser also reports
one syntax limitation in the Darwin SDK `sys/_types/_errno_t.h` header.
Clang Static Analyzer 21.0.0 reports the same 27 findings in both trees:
18 dead stores, three conditional null dereferences and six assignments from
uninitialized values. No source patch or diagnostic suppression was added.

The `boundary_loops` warning follows an abstract empty-list path. Its only
caller first adds the three edges of a valid triangle to the boundary. The
`gts_triangle_vertices_edges` warning requires a triangle without its required
edges; `gts_triangle_set` rejects null edges, and valid triangle construction
sets all three edges. The ear-clipping warning requires a missing surface edge
class or invalid ear vertices; valid constructed surfaces supply both. These
are upstream object-contract paths, not changes in the Libtool rules. Six
expansion warnings depend on positive lengths: callers pass fixed length four
or lengths returned by zero-eliminating helpers, which return at least one.
The malformed-triangle API path remains an upstream robustness item.

GCC16 `-fanalyzer` was not run. The host GTS package uses Apple Clang, and the
target package attempt stopped in Netpbm's native `typegen` build before GTS
configuration because that generator received target linker flags. The host
analysis does not establish target runtime behavior.
