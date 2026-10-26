# Bootstrap compiler-rt builtins

The runtime source and build owner is
[`lang/compiler-rt`](../compiler-rt/README.md). It applies the same complete
patch set for native packages, the OS libc integration and target SDK runtimes.
The common LLVM version and release archive remain selected by this recipe's
`version.mk` and `distinfo`.

`files/build-builtins.py` preserves the earlier builtins-only CLI and delegates
to that owner. It prepares patched source, then invokes the `builtins` phase;
it has no separate extraction, CMake recipe or runtime validation. The output
still uses `WORK/stage/runtime.json` with the shared SDK component profile
`['builtins']`, while `WORK/build.json` records commands and status. This stage
does not claim a C++ runtime or target execution.

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

The optional `--plan` inspects inputs and returns the delegated commands without
creating an output. Remove it to prepare and build. `--target-prefix` defaults
to the native LLVM prefix; `--host-compiler-family` defaults to `clang` and may
select an explicit native GCC exception independently of target Clang.
`--patch` defaults to the selected native prefix's patch tool. Git is used for
source inspection. Work must be a new directory beneath an existing parent.

Preliminary headers must come from the caller-selected EmberBSD source. Input
hashes establish stable bytes, including contained symlink targets, but cannot
prove that the selected checkout produced an arbitrary supplied header tree.
The SDK base producer retains that source association. No completed application
SDK is required to build the first builtins archive.

The compatibility regression is
`profiles/common-build-tools/tests/llvm-builtins.py --sdk-source /absolute/EmberBSD-SDK`.
Source integrity, explicit native/target routing, stage inventory, ELF type and
failure checks now live with the common compiler-rt producer. Synthetic stage
checks do not establish an actual LLVM build or target execution.
