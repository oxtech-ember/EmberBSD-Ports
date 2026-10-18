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

The runtime builder configures the normal GCC source and builds native support
libraries. It selects genuine metadata leaf targets: `libgcc.mvars`, `tconfig.h`,
`machmode.h`, `mode-classes.def` and `version.h`. The recorded support identity
is `gcc-leaf-metadata-v1`. It can build a host `xgcc` metadata driver; it must
not build `cc1` or `cc1plus`. The installed application compiler performs all
target compilation with an explicit seed sysroot.

The broad upstream `libgcc-support` target also installs compiler headers.
Its fixincludes macro-list prerequisite builds a local `cc1`, even when its
command uses the external compiler. This mode avoids that target. It keeps
the authenticated external compiler's own internal and fixed headers. It
disables no header feature. An empty `build/gcc/include` output directory lets
upstream libgcc publish its freshly built `unwind.h`; it supplies no replacement
compiler header. Top-level target-library targets remain excluded because
their upstream rules depend on `all-gcc`.

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

## Resume a failed native support phase

The support prerequisites include upstream `all-build-libcpp`. Build-side
programs use a different libcpp archive from the host-side `all-libcpp` target.

Use the explicit checkpoint before changing helper source files. Keep the
actual nonzero exit-status file from the failed parent command.

```sh
sh profiles/development-toolchain/bootstrap/support-resume.sh checkpoint \
    /absolute/work /absolute/parent-failure-exit.txt
```

The checkpoint authenticates every original input hash. It freezes the
original receipt, helper bytes and failed logs. It records complete source,
build and seed inventories, regular-file hashes and symlink targets.
These manifests do not pin mode bits, ownership or timestamps. They
authenticate tree contents and links, not all filesystem metadata.
It does not accept completed work, language frontends, target-library objects,
a runtime build plan or a nonempty target stage.

Run `build.sh --check --resume-support --external-compiler` with the original
arguments, native tools and flags. Remove only `--check` to continue. The
builder verifies the frozen parent and unchanged compiler, seed, source and
support trees. It keeps generated configure state and valid native objects.
Upstream make completes missing support prerequisites. It then builds fresh
target libraries through the normal external-compiler path.

The distinct `runtime-only-external-support-resume` marker requires the parent
contract. Older verifiers reject this marker. The current receipt names the
original parent input SHA256. The compiler identity can change only its old
`libgcc-support` claim to `gcc-leaf-metadata-v1`; compiler binaries stay fixed.
The old identity stays in the parent. Historical helper hash paths resolve to frozen copies; current helper hashes are recorded
separately. The original parent receipt stays unchanged. The package verifier
checks this explicit parent chain with its ordinary runtime and package gates.
This mode cannot resume a target-library or frontend build.
