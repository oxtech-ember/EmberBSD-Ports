# GNU Texinfo source and package roles

This directory owns GNU Texinfo 7.3 for `devel/gtexinfo` and
`pkgtools/pkg_install-info`. Both packages use `Makefile.common`, one
`distinfo`, and one patch directory. The archive and SHA256 are recorded in
[the prerequisite source list](../../../profiles/development-toolchain/sources.tsv).
The official release is dated 2026-03-02. The source is GPLv3 or later.

The full recipe retains its Perl XS libraries, converters, Info reader,
localization option and existing portability patches. The standalone recipe
builds only upstream `gnulib/lib` and `install-info`. It installs
`bin/pkg_install-info`. Its configure, build and runtime do not require Perl.
The package manager continues to use its ordinary Info registration hooks.

`--disable-perl-tools` configures the C-only `info` and `install-info`
programs and their shared upstream gnulib library. It does not probe Perl or
configure the `tta` converter; top-level make builds only those C directories.
The standalone recipe uses this mode and does not pretend a successful Perl
probe. Default configuration still requires Perl and configures the full
converter. Explicit requests to enable Perl-only options conflict with C-only
mode and fail. Cross builds that need the target Info reader may additionally
select `--enable-native-c-only-tools` with explicit `BUILD_CC`, `BUILD_AR`,
`BUILD_RANLIB` and `LD_FOR_BUILD`. This configures upstream's native makedoc
without Perl or tta; the caller builds it with host ABI flags before building
target Info. Registrar-only builds do not select this option. Both top-level
and nested configure make probes use the selected
`CONFIG_SHELL`. The patched Autoconf input and generated files remain paired;
package post-patch preserves their distributed timestamp order to avoid
unintended regeneration with a different Autotools release.

`cross.mk` supplies upstream's native tool sub-configure with pkgsrc's
`NATIVE_CC`, `NATIVE_AR` and `NATIVE_RANLIB`. It retains explicit build and host
triples. The full recipe passes the selected package C compiler to Perl XS.
The SDK supplies the selected native compiler executable and separate
`CPPFLAGS_FOR_BUILD`, `CFLAGS_FOR_BUILD`, `LDFLAGS_FOR_BUILD` and optional
`LIBS_FOR_BUILD`; other pkgsrc cross contexts retain their `NATIVE_CC` command.
Target compilation uses the selected cross context. Native tools execute only
on the development host.

The existing NetBSD/EmberBSD recipe is moved from the prerequisite patch
series without duplicating it. Its Info search path, gnulib portability,
working-iconv provider and gettext include-order fixes remain. See
[prerequisite provenance](../../../profiles/development-toolchain/prerequisites.md#texinfo-73).
The Python iconv test replaces the previous Ruby test and retains its actual
pkgsrc policy and upstream decision fixtures.

The `tta/C` patches declare `xasprintf` and `text_printf` as printf-like and
fix every argument they then report. Node identifiers formatted a 32-bit
`ucs4_t` with `%lx`. On LP64 hosts the upper half was undefined, so a node and
its references could get different identifiers. With GCC 16 on Darwin arm64,
the manuals then failed with nondeterministic "reference to nonexistent node"
errors.

## Checks

Use one native Python interpreter. These commands do not install packages:

```sh
python3 tests/metadata.py /absolute/export /absolute/mk.conf /absolute/bmake
python3 tests/metadata.py /absolute/export /absolute/cross.mk.conf /absolute/bmake --cross
python3 tests/iconv.py /absolute/export/devel/gtexinfo --pkgsrc /absolute/export \
    --source /absolute/patched-texinfo-source --bmake /absolute/bmake
python3 tests/lifecycle.py /absolute/native/pkg_install-info /absolute/new-check-directory
python3 tests/format.py /absolute/configured/texinfo-7.3 /absolute/WRKDIR/new-check \
    --cc /absolute/package-cc --make /absolute/gmake
```

`tests/c-only.py --help` describes the real two-mode configure and native build
check with explicitly selected tools. `tests/cross-configure.py --help` checks
the cross C-only route and propagation of an unavailable native compiler.
Its selected tool PATH must include an `awk` alias for the prefix nawk, as the
normal pkgsrc tool wrapper does. Run `bmake test` in the standalone native
recipe for all 60 upstream registrar
tests. Cross output must be tested on its matching target separately.
`metadata.py --package pkgtools/pkg_install-info` selects only the registrar
when full Texinfo prerequisites are not staged. The default checks both roles.
Full cross Texinfo retains the staged target Perl prerequisite.
`metadata.py` rejects the former 4.5 standalone version and checks the source
owner, package roles, upstream test target and compiler routing.
`format.py` copies a configured source tree and rebuilds `tta/C` with
`-Werror=format`. Its scratch directory must be inside `WRKDIR` when the pkgsrc
compiler wrappers are used. A probe also confirms that a 32-bit code point
for `%lx` is rejected.
`lifecycle.py` checks insertion, idempotence, deletion, compressed input,
unrelated entries and invalid-option failure in a private Info directory.
It does not replace package archive and install/remove/reinstall checks.

A source export or native test does not establish target package execution.
Keep package, cross build, memory analysis and installed target evidence
separate. Never run target executables on the build host.
