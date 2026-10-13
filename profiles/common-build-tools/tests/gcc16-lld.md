# GCC16 with explicit LLD23 selection

This bounded test links C objects with the common GCC16 runtime and LLD23.
It does not install tools or change GCC defaults. Run it on the build host.
Select an EmberBSD 11 AArch64 sysroot with the common GCC16 package installed.

```sh
CC=/absolute/cross/bin/aarch64--netbsd-gcc \
CXX=/absolute/cross/bin/aarch64--netbsd-g++ \
LLD=/absolute/native-llvm23/bin/ld.lld \
READELF=/absolute/cross/bin/aarch64--netbsd-readelf \
SYSROOT=/absolute/emberbsd-sysroot \
    sh profiles/common-build-tools/tests/gcc16-lld.sh /absolute/new-output
```

`CXX` is optional. Without it, the C++ link check reports an explicit skip.
Use absolute paths without spaces or shell metacharacters. The output must not
exist. The script records tool versions, full original and selected specs,
actual invocations, ELF metadata, positive controls and expected failure logs.
Keep the sysroot's source revision and preparation receipt with this output.
ELF compatibility notes alone do not establish sysroot provenance.

The GCC bootstrap can embed absolute `--with-as` and `--with-ld` paths.
A `-B` directory or `-fuse-ld` option need not replace that linker.
The test writes invocation-local GCC specs. It selects the supplied LLD binary
and requires its actual invocation and version banner. The configured GNU
assembler remains selected and is checked independently. The test selects
startup files, C++ headers and `libgcc` from the installed GCC16 package.
It does not fall back to the compiler's bootstrap runtime.

The selected specs change `*linker`, four common-allocation aliases and three loader rules.
Both `*link` and `*netbsd_link_spec` must contain exactly one `-dc` and one `-dp`.
The test replaces each with `-d`. GNU ld defines
these three options as aliases. LLD23 accepts `-d` but ignores it. This is
sufficient for the final links tested here, which allocate COMMON by default.
The output symbol check proves allocation. It does not prove equivalent
relocatable `-r` behavior. See the [GNU ld options](https://sourceware.org/binutils/docs/ld/Options.html)
and [LLD23 option definitions](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.3/lld/ELF/Options.td#L753-L754).

LLD23 does not recognize GCC's `aarch64nbsd` emulation name. The test selects
`aarch64elf` at link time. Invocation-local specs select `/libexec/ld.elf_so`,
which must exist in the sysroot. Exactly one original `/usr/libexec/ld.elf_so`
rule must occur in each of `*link`, `*netbsd_link_spec` and
`*netbsd_link_ld_elf_so`. Unknown layouts or extra old loader paths fail.
Both C and C++ executables use this default without `--dynamic-linker` overrides.
The test retains all other target specs and startup files.

The `original-loader.specs` control has the same LLD and common-allocation
repairs but retains the original interpreter rules. It links the same real
C inputs with the same strict flags. Its ELF interpreter must remain
`/usr/libexec/ld.elf_so` and fail the target interpreter contract. This proves
why a successful link alone is insufficient. The original compiler specs
and the common sysroot remain unchanged.
It verifies AArch64 ELF64 DSO/PIE outputs, interpreter, NetBSD11 and PaX notes,
RELRO, immediate binding, DSO dependencies and absence of sysroot RPATH leaks.

Two controls retain strict failure behavior. An actual undefined reference
must fail with `--no-undefined`. Two tentative common definitions must produce
a successful link with `--warn-common`. The same inputs must fail when
`--fatal-warnings` is added. No warning category is disabled.

This is a non-LTO link check. Compilation uses `-fno-lto`; the script rejects
GCC LTO sections in its objects. Link invocations use `-fno-use-linker-plugin`.
Do not pass `-fno-lto` to a direct LLD link: GCC forwards it to `collect2`,
while raw LLD rejects it. Direct LLD selection does not exercise `collect2`
or the GCC linker-plugin/LTO path. It does not migrate compiler defaults,
validate GNU warning-section compatibility, or accept a full package.
No Valgrind or target runtime pass is implied by host linking.

For target execution, copy `consumer` and `libember-gcc16-lld.so.1` together
into a private directory. Run `./consumer` as an ordinary user on the matched
EmberBSD target. It must print `42` and exit zero. When `CXX` was set, also copy
`consumer-cxx` and `libember-gcc16-lld-cxx.so.1`. `./consumer-cxx` must print
`C++ DSO exception PASS` and exit zero. It throws `std::runtime_error` in the
DSO and catches it in the executable. These outputs use `$ORIGIN` for test
DSOs and `/usr/pkg/gcc16/lib` for the common runtime. Check loaded libraries
before recording runtime results. No package installation is required.
