# Structural Mach-O package metadata

The native Darwin resolver uses selected `od`, `lipo` and `otool` commands.
It does not need file or libmagic. Requiring file here would create a cycle:
file needs libtool-base, whose package metadata would then need file.
No shared-library or dependency check is disabled.

The command interfaces are `MACHO_OD`, `MACHO_LIPO` and `MACHO_OTOOL`.
Their defaults use the corresponding `TOOLS_PLATFORM` selections.
Normal Darwin pkgsrc retains its platform utility paths. The common native
prefix configuration supplies its selected commands. For example:

```make
MACHO_OD= ${LOCALBASE}/bin/god
MACHO_LIPO= ${LOCALBASE}/bin/llvm-lipo
MACHO_OTOOL= ${LOCALBASE}/bin/llvm-otool
```

Both shared-library checks and package metadata pass these commands explicitly.
Direct AWK callers must supply the same environment variables.
A command failure remains an error, including failure after partial output.
The resolver uses a shell status trailer because POSIX awk `close()` does not
provide a portable child exit status.

`od` reads eight signature bytes. It does not parse object tables.
The CAFEBABE overlap follows
[LLVM `identify_magic`](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/llvm/lib/BinaryFormat/Magic.cpp).
The same low-byte bound separates Java class candidates from universal Mach-O.
Selected object tools validate recognized containers and their slices.
`otool -hv` supplies each slice's file type. Only `EXECUTE` images resolve
`@executable_path` relative to their own directory. Runpath, architecture,
provider ownership and build-directory checks keep their existing behavior.
Cross ELF packages do not enter this resolver.

Run the finite regressions without a compiler:

```sh
python3 -B profiles/common-build-tools/tests/macho-structure-tools.py \
  --pkgsrc /absolute/prepared-pkgsrc --patch /absolute/bin/nbpatch \
  --od /absolute/prefix/bin/god --lipo /absolute/prefix/bin/llvm-lipo \
  --otool /absolute/prefix/bin/llvm-otool --awk /absolute/prefix/bin/nawk
```

The prepared tree must contain the existing Mach-O load-command patch.
Add `--bmake` and `--makeconf` to query the real composed pkgsrc include tree.
Use `--make-arg NAME=VALUE` for required command-line configuration settings.
Repeat `--awk` to check another POSIX AWK implementation.
The metadata queries cover file, libtool-base and a Python package.
Byte fixtures cover scripts, text, Java, thin/fat objects, malformed images,
per-slice file types and selected command failures. They do not compile code.
Installed package and application checks remain separate.
