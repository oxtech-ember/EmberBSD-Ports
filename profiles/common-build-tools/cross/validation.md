# Cross package validation

The package workflow below was checked on 2026-10-08. Ports owns the recipes,
patches and acceptance scripts. The macOS build host used the Ports GCC
16.2.0 cross compiler and the pinned common-profile pkgsrc export. The target
was an AArch64 UTM guest with EmberBSD `EMBER64`, a NetBSD 11.0 base and the
complete `gcc16-16.2.0nb1` package. No desktop was required.

This is VM execution evidence for the named packages. The first three used
a bootstrap GCC12.5 kernel; Binutils used the GCC16/DWARF5 kernel built from
EmberBSD `21cd2464c720159bec0a3ba352e4dee940a58b02`; Python and Meson/Ninja used the same kernel.
These results do not claim a complete GCC16-built userland, LLVM23 package acceptance or
execution of these new packages on a board.

| Package | Checks completed |
| --- | --- |
| pkgconf 3.0.7 | Mac cross build and pkgsrc package checks; normal target installation; all 15 upstream API groups and 14 CLI groups; an installed C library consumer. |
| GNU M4 1.4.21 | Mac cross build and pkgsrc package checks; target installation and Info registration; 242 upstream manual examples with seven unsupported `changeword` cases skipped; stack-overflow check passed. |
| Libtool 2.6.2 | Verified original source, maintained/generated patch equivalence; cross package checks and installation; C11/C++20 shared/static consumers, exceptions through a DSO, selected GCC16 runtime, libtoolize, shlibtool and uninstall. |
| Binutils 2.47nb1 | Mac cross build, full package checks and target installation/integrity; GNU as/ld and archive consumers, DWARF5/64 source lookup, split debug data and stripping, C++20 DSO exceptions, GNU CTF, translated diagnostics and unresolved-symbol errors. |
| Python 3.14.8 | Mac cross build, package checks and target installation/integrity; config-tool and pkg-config C++ embedding, C extensions with ordinary/tagged/stable-ABI filenames, selected runtime and consistent build-details; all 21 selected upstream suites, 5,615 tests run, 478 skipped by upstream conditions. |
| Meson 1.12.1 / Ninja 1.13.2 | Mac cross packaging, normal target installation/integrity; C/C++ shared/static consumers, exceptions through a DSO, Python embedding and browse interpreter, incremental/reconfigured builds, compiler-error propagation, staged/installed RPATH and external pkg-config consumer. Meson's upstream InternalTests ran 78 cases: 77 passed, one skipped for unavailable JSON-schema modules. |

Package SHA256 values identify the actual VM inputs:

```text
pkgconf-3.0.7.tgz     351af223d73169baba9a277208e8d7a6e7682984f5151c32ee7f18432bdfd221
m4-1.4.21.tgz        026972df19145afe7806e6d0eec3450edfd0d542b26789e3652a34491a9c198c
libtool-base-2.6.2.tgz 0862a6c6ab789dd880c017da93ac72fe1f0cb59e19460c9f0b6fb9148a8776e6
binutils-2.47nb1.tgz b07db836b965be43f8f9304c3e22fef385e500ad32ed14ad75beaa6bad5098af
python314-3.14.8.tgz 672b7237f0524304a040961c63e4a00b373ad1b249a09e7ef3ba4387809f5e87
ninja-build-1.13.2.tgz 34990246030305f76a1042f52b9210cb51212c689baa1ff43a28c28fb1aa36db
meson-1.12.1.tgz     ec095a2f57dfdf5344c79b7a95a8e1a8618add1aad8010e3a4c2e50db6470fd0
```

The original-source hashes and URLs are in [sources.tsv](../sources.tsv).
The test entry points and prerequisites are described in [README.md](README.md).
Normal pkgsrc file, interpreter, permission, PIE/RELRO, RPATH and work-directory
checks remained enabled. Installed package integrity was checked on the guest.

Binutils package acceptance explicitly selects the installed GNU as and
direct ld through standard GCC specs. This applies to the installed native
GCC16 package, which still hardcodes base as/ld.

## GCC16 AArch64 cross prefix

On Linux x86_64, the GCC16.2 AArch64 cross prefix selects Ports Binutils 2.47
by default. `profiles/development-toolchain/cross/build.py` now builds the
pinned source and patch set before it configures GCC. No manual `-B` or specs
file selects the tools. The build requires GCC 16 host compilers and records
the source, patch, linker-script, and output hashes in `inputs.txt`.

The source archive SHA256 is
`154ab23b60070e8f27013c22977f1129425d67d1e8acd6e13010e617811e4cff`.
Its SHA512 is
`3126a1064374d8da40d4d70630c204ed1e75d542c447d53fca9778c7ceff095c28e9b445e15a313fef9729082d7966471ee6b5b715d479aa6d568528743e1d98`.
The Ports recipe and source manifest match revision `8e93331`. Cross recipe
commit `534ad94` adds the build and acceptance scripts without changing those
Binutils source inputs.

The [LTO acceptance script](../../development-toolchain/cross/tests/lto-binutils.py)
passed with the installed GCC 16.2 C and C++ drivers.
Both compilers reported `aarch64--netbsd`; both selected the prefix's `as`
and `ld`. The link traces named `collect2`, GCC's `liblto_plugin.so`,
`lto-wrapper`, and the selected assembler and linker. Both outputs are
ELF64 AArch64 executables. The test used `-flto` and the linker plugin without
manual tool overrides. Split-DWARF generation also passes with the selected
Binutils `readelf`. A secondary `aarch64elf` emulation link passed through
the installed linker scripts.

This is compile/link acceptance only. No verified EmberBSD application
sysroot or target VM was available in this check. It does not establish
program execution or update the installed native GCC16 package.

The [BFD repair](../binutils.md) resolves a real GCC16 DWARF64 CU with a
DWARF32 line table. The same object fails with the saved original addr2line
and resolves correctly with nb1. A matching CU64/line64 control is unchanged.
All six installed acceptance groups passed, including both line-table
formats and the GNU nm diagnostic loaded from its installed catalog.
Meson acceptance also selects current GNU as/ld explicitly, with strict
compiler/linker warnings. Base ld 2.42 fails the identical shared-library
object because it emits unused compatibility-symbol warnings; GNU ld 2.47
passes. Installed consumers load the selected GCC16 libstdc++.so.7 without
loader-path overrides. The Meson check uses explicit specs; it is separate
from the GCC16 cross-prefix default-tool and LTO acceptance above.

Python uses the normal target loader, without library-path overrides. Its
upstream cases exercise TLS, ctypes/libffi, SQLite, UUID, decimal, readline,
compression, process/thread handling, imports, virtual environments and REPL.
The [port](../python.md) fixes cross-host selection, OpenSSL discovery,
installed target metadata and embedding flags. The original loader order and
extension package names are preserved. One NetBSD test assertion explicitly
checks that retained packaging convention; the rest of the selected tests
keep their upstream behavior.
Source/export, host-version rejection and a synthetic target-version metadata
regression pass. SQLite and zstd dependencies also cross-build with explicit
target identity and execute through their Python consumers.

The cross regression uses actual pkgsrc parsing and package metadata. It
covers native host dependency selection, missing inspection tools and target
libraries, malformed ELF, script/empty-file handling, target symlink aliases,
cycles, package-owned libraries and explicit shared-library exceptions.
The constrained Info-tool case also rejects a missing target utility and
unrelated unsupported runtime tools.

A separate package-manager regression compares the original and repaired
`pkg_add` using isolated package databases. It exercises alternate-root
installation/update and same-version reinstall, target ownership paths,
script suppression, preservation of another package's parent directory,
partial-extraction rollback and unchanged native replacement behavior. These are
host-side package-manager checks, not execution of target binaries.

Native host bootstrap checks also pass: explicit current CMake/CPack and
msgfmt selection, unchanged defaults without opt-in, rejection of invalid
tools, pkgsrc job limits and compiled C/C++/libintl consumers. The
gettext-tools 1.0nb1 host package links its direct XML dependency and passes
installed XML/ITS translation. This does not accept a target CMake or gettext
package. The exact cross patch export matches 41 files from pinned pkgsrc
with zero fuzz. These adaptations retain full package checks and NLS.
