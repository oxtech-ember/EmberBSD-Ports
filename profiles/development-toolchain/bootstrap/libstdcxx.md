# Rebuild libstdc++ with the application compiler

`rebuild-libstdcxx.rb` prepares a fresh library build for the
[NetBSD locale repair](../locale.md). It uses the existing application GCC16
compiler with POSIX threads. It does not rebuild compiler frontends or change
the old runtime stage. The helper and inheritance verifier have host refusal
tests. The complete new library build and target package acceptance remain
separate checks.

Use the original GCC16.2 archive, the completed original bootstrap stage,
its unchanged pkgsrc export, and a separate export with the locale repair.
The permitted recipe delta is the pinned two-file locale patch and its compiler
package revision. Other source changes require a different build path.
The source pin is in [inheritance.rb](../runtime/recipe/files/inheritance.rb).
It includes the configured `sscanf` conversion fallback.

First run the read-only preflight:

```sh
CROSS_JOBS=2 ruby profiles/development-toolchain/bootstrap/rebuild-libstdcxx.rb \
    --check aarch64 /absolute/new-pkgsrc /absolute/original-pkgsrc \
    /absolute/gcc-16.2.0.tar.xz /absolute/application-toolchain \
    /absolute/emberbsd-sysroot /absolute/original-runtime-work \
    /absolute/new-runtime-work
```

`amd64` uses the corresponding genuine compiler and seed. Paths must be
absolute and contain no whitespace or shell metacharacters. `GNU_MAKE` can
select an absolute GNU make executable. Remove `--check` only after reviewing
the inputs and reserving build space. A new work path is mandatory.

The preflight checks the complete original stage, source recipe delta,
application compiler receipt, target architecture, version, POSIX threads,
GNU binutils and EmberBSD seed hashes. Two explicit `-B` directories select
GCC16 CRT and libgcc. Base OS CRT/libgcc must not satisfy these inputs.
The old source archive and recipe identities remain unchanged.

Source preparation uses the ordinary complete archive, zero-fuzz patches and
the existing `libstdc++.so.7` ABI substitution. The helper runs the actual
`libstdc++-v3/configure`, `make all` and `make DESTDIR=... install`.
It retains the generic locale backend, POSIX threads, upstream subdirectories,
feature defaults and canonical NetBSD API cache settings. The real compiler's
raw C++ driver uses `-nostdinc++`; new generated headers serve the library build.
No old generated configure output or library objects are reused.
The preserved cache settings are recipe policy, not new target API measurements.

The installed locale header must match the prepared source. All C++ headers
and libstdc++ outputs come from the fresh installation. An explicit list carries
the original libgcc CRT/support objects and selected libgcc, OpenMP and atomic
DSOs into the assembly stage. The helper verifies their hashes against an exact
parent snapshot. It never labels those libraries as newly compiled.
This stage contains only selected inherited development files. SDK import must
preserve the existing unversioned linker aliases, OpenMP headers and specs.
It must not replace the whole GCC16 development prefix with this partial stage.

`inheritance.json` records disjoint rebuilt and inherited ownership. The
verifier checks the complete parent snapshot against its historical receipt
paths without editing the old receipt. It rejects a parent that is itself a
rebuild, changed source components, changed inherited bytes, an unchanged old
libstdc++ DSO, missing new headers, and mismatched build logs or retained
configure arguments/status/header snapshots. Existing full
stage, ELF, SONAME, dependency, runtime-path and package-payload gates still apply.

The new marker is `runtime-libstdcxx-rebuild`. The original bootstrap marker and
resume rules remain unchanged. A rebuilt stage cannot be packaged as nb2;
package revision and coordinated SDK import belong to the runtime owner.
Keep both stages and their receipts until the new package and consumers pass.

Full source preparation needs about 1.4 GiB before objects and stages. Reserve
at least 1.8 GiB and additional space for concurrent builds. The helper does not
install into the SDK, register a compiler package, start a VM or delete inputs.
Target acceptance must verify locale conversion, exceptions, threads, the
loaded DSOs and retained OpenMP/atomic behavior. Rebuild affected consumers
against the newly installed headers during the coordinated SDK update.
