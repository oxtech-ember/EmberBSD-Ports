# Build the runtime with an existing POSIX GCC16

Use `build.sh --external-compiler` to cross-build libgcc, its CRT and libstdc++
with an existing host-executable GCC16.2.0 application compiler. This mode
supports amd64 and AArch64 without multilib. It records the actual compiler
binaries; it does not claim that a missing compiler-build receipt exists.

The original GCC archive, prepared recipe, explicit EmberBSD seed and pinned
host math versions have the same guards as the kernel bootstrap. The existing
compiler must report the exact version, target ABI and POSIX threads. Both
frontends must resolve inside its prefix. Its drivers, frontends and GNU target
binutils are hashed before building. Compiler hashes must remain unchanged.
The initial libgcc configure can use existing bootstrap CRT/libgcc for conftests.
Record those selected files, hashes and provenance in the seed receipt. They are
bootstrap dependencies; fresh CRT/runtime outputs must replace them in final links.

The caller authenticates the compiler and the fork-built seed; hashes alone
cannot establish their source provenance.

```sh
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ \
AR=/absolute/native/ar NM=/absolute/native/nm RANLIB=/absolute/native/ranlib \
GNU_MAKE=/absolute/native/gmake CROSS_JOBS=2 \
EMBERBSD_SYSROOT_SOURCE=FULL_EMBERBSD_COMMIT \
EMBERBSD_SYSROOT_PROVENANCE=/absolute/seed-provenance.json \
sh profiles/development-toolchain/bootstrap/build.sh --check \
  --external-compiler --target aarch64 /absolute/prepared-pkgsrc \
  /absolute/gcc-16.2.0.tar.xz /absolute/application-compiler \
  /absolute/emberbsd-seed /absolute/host-math/prefix /absolute/new-work
```

Use absolute native `AR`, `NM` and `RANLIB` paths for host metadata.
A compiler prefix can contain generic aliases for target binutils. Those
aliases cannot inspect native host objects. The standard variables reach
upstream native configure and make unchanged. The receipt records their
selection. Direct target library rules then select the audited absolute
`*_FOR_TARGET` tools. No LTO feature or diagnostic is disabled.

After checking the printed inputs, remove only `--check` to build. The work
path must be new. This mode does not support frontend resume or optional
OpenMP/atomic extensions. It leaves the supplied compiler and seed unchanged.

The pinned host math helper retains its default native GCC16 contract.
For native metadata prerequisites on a host with Clang, select its explicit
host-only mode. This mode accepts Darwin and GNU/Linux with matching architecture, OS and libc.
It rejects a foreign OS or libc ABI on the same architecture.
It retains source hashes, the GMP repair, upstream checks and GMP contracts.
It does not select Clang for any target compilation.

```sh
HOST_CC=/absolute/native/clang HOST_CXX=/absolute/native/clang++ CROSS_JOBS=2 \
sh profiles/development-toolchain/cross/host-math.sh --native-clang \
  /absolute/archives /absolute/netbsd-tools /absolute/new-host-math
```

The runtime builder configures the normal GCC source, builds native support
libraries, and invokes the actual upstream `libgcc-support` target. That target
provides `libgcc.mvars`, headers and driver specs. It can build a host `xgcc`
driver for metadata; it must not build `cc1` or `cc1plus`. The installed
application compiler performs all target compilation with an explicit seed
sysroot. Top-level target-library targets are excluded because their upstream
rules depend on `all-gcc`.

The builder then executes each runtime's real configure, make and staged install
rules. It retains the POSIX-thread configuration, NetBSD ABI, current recipe
patches and RELRO link flags. No SDK or runtime file is copied into the OS seed.
The output includes the separate `runtime-only-external-compiler` marker,
compiler receipt, build plan, generated support snapshot and complete stage
file hashes and symlinks. The runtime verifier applies its normal ELF,
SONAME, dependency, path, RELRO and package gates to this scope.

Run the input and dispatcher fixtures, then the runtime package suite:

```sh
sh profiles/development-toolchain/bootstrap/tests/inputs.sh
sh profiles/development-toolchain/bootstrap/tests/external-pipeline.sh
ruby profiles/development-toolchain/runtime/tests/package-test.rb
```

Fixtures exercise both target selections, wrong compiler/seed/ABI, missing
frontends, compiler-receipt changes, a changed seed and forbidden frontend
creation. Dispatcher fixtures reject `all-gcc` and target-library recursion.
They do not compile GCC or qualify a complete runtime build. A real build must
retain its exit status, commands, receipts and output hashes separately.

Build success does not establish target execution or installed package closure.
Use one declared runtime provider. The runtime-only package conflicts with the
full compiler package; staging build inputs does not authorize overwriting its
files or removing development packages. Installation ownership and target
consumer acceptance remain separate checks.
