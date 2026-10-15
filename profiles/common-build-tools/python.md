# Python cross packages

The current profile selects Python 3.15.0. Its NetBSD cross-host cases accept
AArch64 and amd64, including the empty-vendor `x86_64--netbsd` triplet.
Unknown hosts and unsupported NetBSD architectures still fail.
Both maintained `configure.ac` cases match the shipped `configure` cases.

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

`tests/source-profile.sh DISTFILES NEW_WORK python-source` verifies original
archive and patch hashes, zero-fuzz application, source export, repeated or
missing patches and both actual configure cross cases. Existing Linux and
unknown-host controls accompany the NetBSD regression.

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
