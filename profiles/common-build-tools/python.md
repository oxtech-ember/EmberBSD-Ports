# Python cross packages

## PAX source extraction

Python 3.15.1nb2 selects `EXTRACT_USING=bsdtar` through the normal pkgsrc
tools framework. The release uses POSIX PAX `path` records for eight source
names. The legacy pkgsrc `nbtar` reader does not apply those records and can
silently extract the 100-byte fallback names. Keep the archive and PLIST intact.
The selected extractor is a host tool in both native and cross builds.

The common bsdtar recipe uses the existing libarchive 3.8.10 sources and
registered zlib provider. It does not depend on the Python package. Keep the
bootstrap default unchanged: making bsdtar the global extraction default would
give its own zlib dependency an extraction edge back to bsdtar.
The complete SDK graph must verify this ordering and its explicit native tool
path. A metadata check of one recipe does not prove the complete graph.

The [metadata regression](tests/python-pax-metadata.py) accepts `--pkgsrc`,
`--expected-tar`, `--env-json`, `--new-work` and the complete accepted bmake
tuple as repeated `--make-arg=...` arguments. It checks the real Python
revision, native tool dependency, provider path and extractor `-t` operand.
Run it through the SDK owned-process interface. It does not build a package.

The [archive regression](tests/python-pax-extraction.py) creates fifteen finite
fixtures with `--new-work`. They include the eight exact Python names with
synthetic payloads, ordinary ustar, GNU long names, PAX path/linkpath/size/time,
per-file state reset and malformed length records. Add `--tar` and a complete
`--env-json` to run the selected extractor. Optional `--baseline-tar` must
reproduce the legacy silent truncation for all eight names. Neither mode
executes Python from the package under test or edits its release archive.

The existing libarchive reader rejects significant global PAX defaults that
it does not implement. The regression requires failure for global `path` and
`size`; it does not describe these attributes as supported. Unknown global
attributes keep the reader's existing behavior. Malformed archives must return
nonzero. A failed extraction need not be atomic. No archive parser is replaced
or modified by this recipe change.

BSD implementations informed this choice: [OpenBSD pax](https://github.com/openbsd/src/blob/master/bin/pax/tar.c)
has an extended-header reader; [FreeBSD tar](https://cgit.freebsd.org/src/tree/usr.bin/tar/Makefile)
uses libarchive; [DragonFly tar](https://leaf.dragonflybsd.org/cgi/web-man?command=bsdtar&section=1)
documents PAX extraction. The [NetBSD pax source](https://github.com/NetBSD/src/blob/trunk/bin/pax/tar.c)
and the older pkgsrc copy retain a separate reader. Reuse the existing modern
provider instead of adding a private partial PAX implementation.

Fixture generation and source checks are not native extractor acceptance.
Actual metadata, archive execution and clean Python package installation remain
separate checks.

The current profile selects Python 3.15.1. Its NetBSD cross-host cases accept
AArch64 and amd64, including the empty-vendor `x86_64--netbsd` triplet.
Unknown hosts and unsupported NetBSD architectures still fail.
Both maintained `configure.ac` cases match the shipped `configure` cases.

The shared recipe follows the [3.15.1 maintenance release](https://www.python.org/downloads/release/python-3151/).
Its archive SHA256 and byte size match `distinfo` and `sources.tsv`.
The patch series retains the NetBSD cross metadata and GCC16 adaptations.
Upstream now selects the correct static-library directory for shared and
static-only builds. The build-details patch leaves that upstream logic intact.
Version 3.15.1 reset the package revision. Earlier package results below
apply only to their recorded source versions.

The 3.15.1nb1 Darwin recipe passes the selected `OSX_SDK_PATH` as upstream
`SDKROOT`. Native Darwin fails before configure when that path is missing,
empty, relative or does not name an existing directory. This guard does not
apply to cross builds, Linux or NetBSD. The recipe supplies libffi flags
through the documented `LIBFFI_CFLAGS` and `LIBFFI_LIBS` variables.
The paired `configure.ac` and shipped `configure` guards honor either explicit
variable before the Apple SDK libffi probe. Unset selectors retain upstream
SDK discovery. Linux and NetBSD keep their existing recipe selection.

The preceding Darwin build mixed Apple SDK ffi headers and
`USING_APPLE_OS_LIBFFI` with the selected Ports libffi runtime.
Its `_ctypes.so` load command already named the Ports library.
The fix removes that header/runtime mismatch. It does not establish that the
preceding build loaded an Apple libffi DSO.
Both buildlink and ordinary tool dependencies require Python 3.15.1nb1.
A stronger consumer requirement remains effective.

The source and metadata regression uses the real generated configure blocks,
paired maintained guards, native pkgsrc metadata and pkgsrc version matching:

```sh
python3 -B profiles/common-build-tools/tests/python-darwin-ffi.py \
    --source /absolute/patched-python --recipe /absolute/Ports/pkgsrc/lang/python315 \
    --pkgsrc /absolute/prepared-pkgsrc --makeconf /absolute/native.mk.conf \
    --bmake /absolute/sdk/bin/bmake --shell /absolute/sdk/bin/mksh \
    --pkg-config /absolute/sdk/bin/pkg-config --pkg-admin /absolute/sdk/sbin/pkg_admin \
    --ffi-prefix /absolute/selected-prefix --sandbox-profile /absolute/containment.sb \
    --work /absolute/new-check
```

Cached provider availability isolates selector precedence without compiling.
Controls cover both explicit variables, each variable alone, unchanged Darwin
fallback, explicit SDKROOT without xcrun, Linux selection, the rejected old
provider and a stronger caller floor. Native SDK metadata controls reject missing,
empty, relative, absent and regular-file paths. Cross, Linux and NetBSD
controls keep that failure outside their scope. Add `--sdk-only` to run only
these SDK metadata controls. This check does not accept a new package
or runtime. A clean Darwin rebuild must verify the actual compiler inputs and
`_ctypes.so` load commands before SDK acceptance.

The nb3 header keeps the C11 build assertion an integer constant expression.
The earlier comma expression rejects a file-scope array in `Objects/typeobject.c`
when the Linux pkgsrc build uses GCC16 and GNU C11. Multiplication by zero
retains the same `_Static_assert` without evaluating an operand.
The existing NetBSD, SunOS, C++ and MSVC branches stay unchanged.

Run the actual-header regression with native or target GCC16:

```sh
CC=/absolute/gcc16 CFLAGS='--sysroot=/absolute/target-sysroot' \
    sh profiles/common-build-tools/tests/python-array-ice.sh \
    /absolute/patched/Include/pymacro.h /absolute/pristine/Include/pymacro.h \
    /absolute/new-results
```

Omit `CFLAGS` for a native compiler. Keep the original `patchlevel.h` beside
the patched header. Real native and AArch64 GCC16 compile checks pass for
GNU C11, C17 and C23: array, enum and static initialization succeed; pointer,
false and nonconstant assertions fail. The small native contract passes
Cppcheck 2.22, GCC16 and Clang19 path analysis, execution and strict Memcheck.

Full native `typeobject.c` reproduces the original GCC16 compilation failure.
The repaired GCC analyzer completes with complexity bailouts; it is not a
complete path proof. Clang19 retains one identical inherited null-refcount path.
Cppcheck cannot parse the full GCC16/glibc input, including `__int128` types.
These limits do not change the target Python package acceptance boundary.

Linux's selected native upstream suites also expose the existing pkgsrc `.so`
extension naming policy. The sysconfig tests now verify loader acceptance of
that suffix and the actual preferred tagged loader ABI. This adds no skips.
The corrected 41-case sysconfig run passes, with three upstream platform skips.
The other six selected native suites pass. Target Python 3.15 execution remains
separate from this host generator build and the older 3.14 receipts below.

The nb4 recipe uses its existing GDBM compatibility provider for Linux `_dbm`.
It no longer also requests Berkeley DB through `bdb.buildlink3.mk` on Linux.
Other platforms retain that provider selection, including NetBSD's base `db1`.
This changes dependencies only. Configure still discovers the NDBM header and
library, and the separately packaged `_gdbm` policy stays unchanged.

Run the dependency regression with real Linux and NetBSD configurations:

```sh
BMAKE=/absolute/host/bin/bmake ruby profiles/common-build-tools/tests/python-linux-ndbm.rb \
    /absolute/prepared-pkgsrc /absolute/linux.mk.conf /absolute/netbsd.mk.conf \
    /absolute/previous-Makefile /absolute/new-Makefile /absolute/new-results
```

This checks real pkgsrc metadata without installing dependencies. The Linux
before/after check removes only Berkeley DB dependencies and preserves NDBM
link routing and configure arguments. NetBSD provider metadata stays identical.

Native GCC16 verification on 2026-10-18 uses installed pkgsrc GDBM 1.26 headers
and libraries. Actual CPython 3.15 configure selects `USE_NDBM` with
`-lgdbm_compat`. Its unchanged `make Modules/_dbm.so` target builds the module.
The existing native Python 3.15 interpreter runs all 16 upstream
`test.test_dbm_ndbm` tests with that module; all pass without skips. Loader
diagnostics confirm both GDBM libraries come from the selected 1.26 prefix.
This focused check does not establish a complete native or target package.

Separately, on 2026-10-18, the ordinary Linux GCC16 build of
`python315-3.15.0nb4` passed package checks and installation. The installed
interpreter passed seven upstream suites: sysconfig, NDBM, bzip2, zlib,
ctypes, Readline and SSL. They ran 1093 cases, including 63 skips.
The host library search selected the installed package providers before
other private host libraries; an earlier search order loaded a narrow
ncurses library and rejected `_curses`. The corrected build retains the
wide curses modules. This does not establish the AArch64 Python package.

The focused configure regression uses a previous patched source and the new source:

```sh
PKG_CONFIG=/absolute/host/bin/pkg-config \
    sh profiles/common-build-tools/tests/python-amd64-configure.sh \
    /absolute/baseline-python /absolute/patched-python /absolute/cross-prefix \
    /absolute/target-sysroot /absolute/host/bin/python3.15 /absolute/new-results
```

The old source rejects amd64. The new source completes real GCC16 cross
configuration with the selected target headers and libraries.
No new configure cache answers are added; the test uses the recipe's existing answers.
This checks configuration and LP64 metadata, not a target Python package or execution.
The upstream unsupported-platform warning remains visible.

The recipe declares the runtime platform for build-details generation.
NetBSD `MACHINE_ARCH=x86_64` maps to its kernel machine name `amd64`;
AArch64 retains `evbarm`. Both use the selected target `OS_VERSION`.
`tests/python-build-platform.rb` checks real pkgsrc `MAKE_ENV` and the host
generator against existing target sysconfig inputs. It writes only new outputs
and disables bytecode writes to those inputs. No host platform fallback is used.

The Python 3.14.8 package acceptance recorded below is historical.
Build it with the [macOS cross-package configuration](cross/README.md), using
the shared GCC16 compiler and a complete target sysroot. The source archive
comes from Python upstream; [sources.tsv](sources.tsv) and recipe distinfo
pin its hashes. These AI-assisted EmberBSD adaptations have not been
submitted or accepted upstream.

## Host and target separation

The recipe recognizes NetBSD/AArch64 in both upstream cross-host checks.
The added cases agree between `configure` and `configure.ac`; other unknown
targets still fail. The shipped configure remains the build entry point,
including the inherited pkgsrc adaptations. This does not establish general
support for regenerating it from configure.ac.

Set `EMBERBSD_CROSS_BUILD_PYTHON` to an existing absolute host Python 3.14
executable to reuse it. Upstream configure rejects a different major/minor
version. Without that override, the recipe retains its matching native
pkgsrc Python build dependency. The build interpreter runs generators and
byte compilation; target programs and extension modules use the cross C/C++
compiler. No older target Python is required.

OpenSSL discovery checks the selected target prefix inside the sysroot.
Generated installed sysconfig data and the installed configuration Makefile
use target library paths. `CONFIG_ARGS` preserves the original build receipt.
Build-details uses the target runtime platform, version from the source
header and configured ABI flags. Its extension list follows the target
NetBSD loader, including SOABI and the stable ABI suffix. The static library
path names the installed configuration directory. A different micro version
or ABI of the host Python does not change these target values.
Native builds retain their existing configuration path.

The installed Python configuration script includes the shared-library search
directory in `--ldflags`, matching its shell counterpart. This fixes actual
embedding outside the system library directories.

NetBSD keeps pkgsrc's untagged `.so` modules inside versioned Python directories.
The upstream loader still prefers tagged names. The NetBSD branch of
`test_EXT_SUFFIX_in_vars` explicitly verifies `.so` and loader acceptance;
upstream assumes the configured suffix must be first. `test_soabi` remains
unchanged and checks tagged-name priority. Real consumers exercise ordinary,
`.cpython-314.so` and `.abi3.so` lookup. Existing extension package manifests
and runtime lookup order are preserved.

SQLite autosetup receives explicit build and host identities, with an
`unknown` vendor when pkgsrc uses an empty one. zstd receives its upstream
`UNAME_TARGET_SYSTEM` setting. These changes prevent Darwin shared-library
flags from entering the NetBSD dependency build. They are cross-only pkgsrc
adaptations; native builds keep the original choices.

## Verification

`PYTHON=/absolute/sdk/python3 tests/source-profile.sh DISTFILES NEW_WORK python-source`
uses Python 3.12 or newer and its standard library. It verifies archive and
patch hashes, byte size, installed test/ensurepip source entries, zero-fuzz
application, repeated patch refusal and
normal export. Missing, duplicate, old or foreign source rows, wrong sizes
and changed archive bytes must fail. Existing Linux and unknown-host controls
accompany the NetBSD AArch64 and amd64 configure cases.
The actual build-details generator receives explicit metadata fixtures.
It checks target source version, loader suffixes, shared/static library paths
and unchanged native version selection. These checks build no interpreter
and do not accept a host or target runtime.

`tests/python-cross-tools.sh PKGSRC CROSS_MAKECONF NATIVE_MAKECONF
PYTHON_SOURCE NEW_WORK` checks invalid host interpreter paths, upstream
version rejection, native configuration and literal sysroot removal. The
path fixture covers regexp characters and preserves CONFIG_ARGS.
`tests/python-build-details.sh PYTHON_SOURCE PYTHON_BUILD HOST_PYTHON NEW_WORK`
uses a synthetic source-header version to catch accidental host-version reuse.

On the target, `cross/run-python-tests.sh NEW_OUTPUT` exercises installed
configuration tools, an actual C extension and C++ embedded interpreters.
Both python-config and pkg-config must produce runnable consumers. They
load the selected common runtime and the required extension modules, and
compare installed build-details platform, version, ABI, library paths and
suffixes with the actual runtime.
The script then runs upstream tests for TLS, ctypes, hashing,
UUID, readline, SQLite, decimal, compression, processes, threads, imports,
sysconfig, virtual environments, sockets, PTYs, faults and the REPL.
Only the packaging assertion above is adapted. External network and optional
resource tests are not enabled.

Source preparation, host checks, normal pkgsrc package checks and installed
AArch64 VM acceptance pass. All 21 selected upstream suites passed: 5,615 tests
ran and 478 were skipped by upstream conditions. This is a focused suite,
not the full CPython suite or board acceptance. See the
[common validation record](cross/validation.md) for the exact package hash.
