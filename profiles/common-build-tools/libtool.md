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
