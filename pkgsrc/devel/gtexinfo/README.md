# GNU Texinfo source and package roles

This directory owns GNU Texinfo 7.3 for `devel/gtexinfo` and
`pkgtools/pkg_install-info`. Both packages use `Makefile.common`, one
`distinfo`, and one patch directory. The archive and SHA256 are recorded in
[the prerequisite source list](../../../profiles/development-toolchain/sources.tsv).
The official release is dated 2026-03-02. The source is GPLv3 or later.

The full recipe retains its Perl XS libraries, converters, Info reader,
localization option and existing portability patches. The standalone recipe
builds only upstream `gnulib/lib` and `install-info`. It installs
`bin/pkg_install-info`. It does not install the full converter or a runtime
Perl dependency. Its native Perl dependency belongs to upstream configure.
The package manager continues to use its ordinary Info registration hooks.

`cross.mk` supplies upstream's native tool sub-configure with pkgsrc's
`NATIVE_CC`, `NATIVE_AR` and `NATIVE_RANLIB`. It retains explicit build and host
triples. The full recipe passes the selected package C compiler to Perl XS.
Target compilation uses the common GCC16 context. Native tools execute only
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

Run `bmake test` in the standalone native recipe for all 60 upstream registrar
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
