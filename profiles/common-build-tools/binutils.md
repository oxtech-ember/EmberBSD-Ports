# Binutils 2.47

The common profile replaces the canonical `devel/binutils` recipe with 2.47nb3.
It supplies GNU assembler, linker, archive and ELF inspection tools for
EmberBSD applications. The source archive comes from upstream; its SHA256
and original URL are in [sources.tsv](sources.tsv). The downloaded release
signature was checked against Nick Clifton's release signing key.

This recipe derives from pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`. Existing NetBSD patch identifiers,
authors and upstream licenses are retained. EmberBSD adaptations are
AI-assisted and have not been submitted or accepted upstream.

## Source changes

- Retain the inherited NetBSD AArch64 and ARM EABI linker emulations.
  Refresh `ld/Makefile.am`, its shipped generated `Makefile.in`, and
  `ld/configure.tgt` for the current upstream source.
- Retain the inherited `safe-ctype.h` compatibility patch unchanged.
- Read `DW_FORM_line_strp` using the line table's own DWARF32/64 format.
  GCC's `-gdwarf64` can emit a 64-bit CU with a 32-bit line table; upstream
  BFD incorrectly used the CU width and failed source lookup. Indexed
  strings continue to use their CU's string-offset table format.
- Load a `DT_NEEDED` shared object only once when the LTO plugin is active.
  Upstream ld (PR ld/28849, since 2.39) loads these objects before the
  plugin reads all symbols and again after it opens all inputs. The second
  copy makes each definition of the first copy a reference. With
  `--copy-dt-needed-entries`, each `.gnu.warning.SYMBOL` of an indirect
  library, such as libc through libm, gives a warning, and
  `--fatal-warnings` stops the link. ld now uses the first object again.
  The same failure occurs with upstream master.
- Remove gold options and four gold patches because this upstream release
  no longer includes gold. BFD ld remains the selected GNU linker.
- Drop the obsolete `bfd/cache.c` SunOS include-only patch; the current
  source does not need that inherited extra include.
- Use host Perl for the shipped POD-to-man-page generator, host Texinfo for
  Info manuals, and host `msgfmt` for translation catalogs.
- Declare gettext through pkgsrc buildlink. NetBSD's base libintl supplies
  the public API but not the GNU-private `_nl_expand_alias` probe symbol;
  pkgsrc already handles that distinction. Carry its gettext cache results
  into the recursive configure calls that Binutils runs during `make`.
- Select `--with-system-zlib` and the common `devel/zlib` buildlink dependency.
  The bundled zlib is excluded. The nb3 ABI dependency floor rebuilds BFD
  consumers against the package with this shared dependency.

The [cross configuration](cross/README.md) supplies absolute host
`CC_FOR_BUILD` and `CXX_FOR_BUILD` paths. BFD's `chew` documentation generator
must run on the Mac; the assembler, linker and ELF tools are target programs.
The pkgsrc cross Libtool override resolves `depcomp` from the selected
cross-tool prefix. Native Libtool lookup is unchanged. `V=1` avoids placing
Automake's silent-rule `@echo` inside the depcomp shell continuation.

The target sysroot needs the complete base library development files,
including `libintl`, rather than only libc and the compiler's runtime.
Missing libraries must fail the package checks; disabling translation
catalogs does not repair an incomplete sysroot.

## Validation

`tests/binutils-zlib.py` evaluates the actual common recipe with a selected
exported pkgsrc framework and complete `--make-arg` tuple. It checks the
system-zlib configure option, package dependency and nb3 ABI floor using a
temporary recipe and empty package database. `--environment` selects the
renderer JSON containing the metadata environment. No package target runs;
package compilation and installed linkage remain separate checks.

`tests/cross-generators.sh` checks actual pkgsrc native/cross auxiliary
selection, compiles and executes a host generator, and rejects relative or
missing host compiler paths. The complete exported cross patch applies
without fuzz to pinned pkgsrc.

`cross/run-binutils-tests.sh NEW_WORK` is the installed AArch64 acceptance
entry point. It requires the complete common GCC16 package. It exercises
GNU assembler/linker selection, static archives, DWARF5/64 source lookup,
separate debug information, stripping, C++ exceptions across a DSO,
GCC CTF emission/linking/inspection, translation catalogs and
unresolved-symbol errors. The DWARF64 check covers both assembler-generated
32-bit and compiler-generated 64-bit line tables.

The installed native GCC16 package hardcodes `/usr/bin/as` and
`/usr/bin/ld`; `-B` does not override those paths. The acceptance script
selects the installed GNU assembler and direct ELF linker through a local
standard GCC specs file and verifies the actual commands. This keeps the
native package unchanged. It does not establish its default-tool migration.

The separate [GCC16 cross recipe](../development-toolchain/cross/README.md)
builds this pinned Binutils 2.47 source and patch set for the selected target.
It installs `as`, `ld`, and the linker scripts in the cross prefix before it
configures GCC. GCC uses those paths by default. Its
[`lto-binutils.py`](../development-toolchain/cross/tests/lto-binutils.py)
acceptance verifies the AArch64 `collect2`/plugin/LTO path without `-B` or
specs. This cross-prefix result does not migrate the installed native package
or establish target execution.

This GNU CTF workflow is separate from the OS's NetBSD DWARF-to-CTF tools.
Updating the package does not replace the OS bootstrap toolchain or prove
acceptance of a GCC16-built userland. Actual package and VM results belong
in the [validation record](cross/validation.md).
