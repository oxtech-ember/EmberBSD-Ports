# Bootstrap compiler-rt builtins

`files/build-builtins.py` builds the first LLVM target runtime for EmberBSD
AArch64 or amd64. It uses the common LLVM release and archive checksum from
`version.mk` and `distinfo`. The compiler runs on the development host. Its
output uses the selected EmberBSD target and preliminary base headers.

This producer builds PIC compiler-rt builtins only. It does not build shared
libunwind, libc++abi, libc++, sanitizers, a sysroot, or a binary package.
It does not change the explicit GCC runtime path. The complete application
sysroot remains unavailable until those other runtime stages are connected.

## Inputs and source scope

Use a native Ports Clang/LLVM prefix for the same release as this recipe.
The prefix supplies CMake, Ninja, Python, the shell, and LLVM object tools.
The controller runs with that prefix's Python. Native CMake configuration
comes from the complete patched LLVM recipe. Host ABI headers and libraries
are not selected as target inputs.

`--base` selects a tree with real `usr/include` headers prepared by the
EmberBSD base producer. It does not need libc, CRT, or a completed SDK receipt.
`--os` selects the corresponding clean OS source checkout. The build records
that revision and hashes every supplied header and relative link. These checks
prove stable input bytes. They do not prove that this OS checkout generated
those headers. `build.json` states that boundary. The caller must retain the
base producer's source association before using the result in an OS release.
An arbitrary header tree is not established as EmberBSD by this command.

The source subset is compiler-rt, the common CMake utilities, third-party
headers, libc's header utilities, and the LLVM license. It contains no compiled
LLVM core source. All eight current `lang/llvm` patches target LLVM core files;
the native prefix already uses that complete recipe. No current Ports patch
changes this compiler-rt subset. The producer checks the complete LLVM patch
inventory and checksums. It refuses a newly added `lang/compiler-rt` recipe
until its source and full patch set are connected. Do not maintain another
runtime patch set in a workspace.

The reviewed NetBSD pkgsrc compiler-rt patches concern Darwin sanitizer debug
flags, SunOS sanitizer availability, and AArch64 sanitizer context handling.
They do not apply to the standalone NetBSD builtins target. The source references
are [pkgsrc compiler-rt](https://github.com/NetBSD/pkgsrc/tree/trunk/lang/compiler-rt/patches)
and [upstream standalone builtins](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/compiler-rt/lib/builtins/CMakeLists.txt).

## Run the producer

Create the parent of the chosen work directory in the shared target object tree.
The work directory itself must not exist. Start with the read-only plan:

```sh
/absolute/host-pkg-llvm/bin/python3.15 -B \
  pkgsrc/lang/llvm/files/build-builtins.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --archive /absolute/distfiles/llvm-project-23.1.4.src.tar.xz \
  --base /absolute/emberbsd-preliminary-base \
  --os /absolute/EmberBSD \
  --host-prefix /absolute/host-pkg-llvm \
  --work /absolute/shared-objects/amd64/llvm-builtins \
  --target amd64 --jobs 4 --plan
```

Remove `--plan` to extract, configure, build, and install. The CMake invocation
uses the explicit target, sysroot, compiler, linker, archive tools, and native
LLVM CMake package. Host compiler flags are not copied to the target build.
The build uses upstream `builtins` and `install-builtins` targets. Test execution
is a later target operation; disabling test generation here does not claim a
passed test suite.

A successful build writes `WORK/stage/runtime.json` with the SDK
`emberbsd-llvm-runtime` component profile `['builtins']`. The installed archive
is discovered from the stage, then checked for the selected ELF architecture.
The stage retains the compiler-rt license. `WORK/build.json` records commands,
inputs, and build status. Numbered logs remain beside the work directory's
sources and objects. Failure removes the completion manifest and preserves the
failed work for diagnosis. The command does not reuse an existing work tree.

The stage does not claim C++ ABI compatibility or target execution. The next
runtime component is PIC static libunwind. Its output can then support the
EmberBSD base producer before shared C++ runtimes are built.

## Regression checks

```sh
python3 -B profiles/common-build-tools/tests/llvm-builtins.py \
  --sdk-source /absolute/EmberBSD-SDK
```

The checks use a small source archive and synthetic ELF members. They exercise
the production extraction, stage inventory, manifest validation, input mutation
refusal, and failed-command status. They also check explicit cross-tool routing.
They do not compile the LLVM release or execute target programs. A real native
prefix and EmberBSD headers are required for that separate build check.
