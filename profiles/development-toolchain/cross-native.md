# GCC16 target compiler built on another host

The `lang/gcc16` recipe can build the target compiler package on the
development host. The build, host and target systems are different:
for example, macOS builds a compiler that runs on and targets
EmberBSD/NetBSD. The [cross-native delta](patches/gcc-cross-native.patch)
adds this mode to the recipe. It advances the recipes to
`gcc16-16.2.0nb5` and `gcc16-libs-16.2.0nb6`. Native builds keep the
upstream configuration.

Consumers such as `lang/clang` need the installed target compiler, its C++
headers and its CRT directory. They do not run it during the cross build.

## Configuration

In cross mode, the recipe:

- passes `--target`, so that build, host and target are explicit;
- uses `--with-build-sysroot` for target headers, fixincludes and target
  libraries; the installed compiler has no sysroot;
- builds target libraries with the existing GCC16 cross compiler
  (`*_FOR_TARGET`), which has the same release and source patches;
- builds generators and the build-host libiberty with the build-host
  compiler and archive tools (`*_FOR_BUILD`, `NATIVE_AR`, `NATIVE_RANLIB`);
- does not pass target search paths or linker flags to build-host programs.

Configure cannot execute the installed assembler and linker on the build
host. When build and host differ, `gcc/configure` probes the assembler and
linker features with `AS_FOR_TARGET` and `LD_FOR_TARGET`, the cross Binutils.
Base NetBSD 11 provides Binutils 2.42.
Probes against 2.47 can select directives that 2.42 rejects. For example,
GCC uses `.base64` when the assembler supports it, from Binutils 2.43.
Thus the cross-built compiler depends on the `binutils>=2.47` package. Links
in its private program directory select that package's `as` and `ld`.
The recipe omits `--with-as` and `--with-ld`. GCC uses these paths on the
build host for its probes. There they name a host tool or no file.

## Layering over the runtime provider

The common cross profile allows this build only with
`EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime`. A compiler provider closure must
still import its complete compiler package. In runtime mode, the compiler
depends on `gcc16-runtime>=16.2.0nb6` and does not contain its files.
[`gcc16-external-runtime.sh`](../common-build-tools/cross/gcc16-external-runtime.sh)
runs after installation into the stage. It reads the installed runtime
file list from the sysroot package database. For each file, it compares:

- the ELF type, `SONAME` and `NEEDED` entries;
- every dynamic symbol: name, version, type, binding, visibility and
  defined/undefined state, and the size of data and TLS symbols;
- the target of each symbolic link.

Only after all files match does it remove them from the compiler stage.
The staged C++ headers must also select the TLS `std::call_once` ABI.
Development links such as `libstdc++.so` remain in the compiler package.

`gcc16-runtime-16.2.0nb6` conflicts only with complete compilers up to nb4
and with `gcc16-libs`. A complete compiler with the same files is still
refused by pkg_add file ownership. The runtime package content is otherwise
unchanged. The cross profile applies the
[development profile](mk.conf) options: C and C++, no NLS, external math
libraries and no Graphite.

## Checks

```sh
sh profiles/common-build-tools/tests/gcc16-external-runtime.sh /absolute/new-work
python3 -B profiles/common-build-tools/tests/cross-targets.py \
    --sdk-source /absolute/EmberBSD-SDK /absolute/bmake
BMAKE=/absolute/bmake sh profiles/development-toolchain/tests/cross-native.sh \
    /absolute/prepared-pkgsrc /absolute/cross-mk.conf /absolute/new-work
```

The cross MAKECONF of the third check must set
`EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime`.

The first check uses fixtures. It must refuse different symbol versions,
object sizes, `NEEDED` entries, links, a missing file, non-TLS headers and a
different `c++config.h`. Its stub package database also has no nb6 runtime case. The second check covers the profile selection. The third
check reads the real recipe metadata for cross and native builds.
