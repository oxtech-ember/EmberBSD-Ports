# GCC16 AArch64 Fortran Cross-Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cross-build current Fortran-enabled pkgsrc dependencies for EmberBSD AArch64 with GCC 16.2, then produce the approved openTPU package.

**Architecture:** Extend the existing AArch64 GCC16 frontend and audited runtime provider. Add pkgsrc compiler and cross-Libtool support through a Ports patch applied to fresh exports. Build the pinned NumPy 2.5.3 recipe with its normal BLAS dependency, then build and validate py-opentpu.

**Tech Stack:** GCC 16.2.0, Binutils 2.47, pkgsrc 2026Q3, EmberBSD AArch64 sysroot, Python 3.15 target, NumPy 2.5.3, openTPU 0.1.0.

**Spec:** `docs/superpowers/specs/2026-10-18-gcc16-aarch64-fortran-design.md`

## Global Constraints

- Target triplet is `aarch64--netbsd` and target ABI remains EmberBSD AArch64.
- Use the existing GCC 16.2.0 source and Binutils 2.47 Ports toolchain.
- Keep pkgsrc changes in versioned Ports patches; do not edit the pinned pkgsrc submodule.
- Keep NumPy 2.5.3 and its BLAS dependency; do not add older compilers, runtimes, or libraries.
- Keep openTPU source revision `730ca28feb77b5598090e97ab209f302f0c56eec`, package version `0.1.0`, and NumPy runtime dependency.
- Do not claim EmberBSD execution, RTL, FPGA, or model-inference acceptance.

## Review Focus

- Compiler and runtime receipts must identify one GCC version, target, ABI, and `/usr/pkg/gcc16` prefix.
- Every staged Fortran DSO must have its target SONAME and only accepted EmberBSD/GCC16 dependencies.
- pkgsrc wrappers and Libtool must invoke the selected target compiler and must not retain host paths.
- The NumPy package must link the selected BLAS implementation and retain its runtime dependency metadata.
- The openTPU PLIST and package scripts must include all payload and target Python shebangs.

---

### Task 1: Add the GCC16 AArch64 Fortran compiler and runtime

**Files:**
- Modify: `profiles/development-toolchain/cross/pipeline.py`
- Modify: `profiles/development-toolchain/cross/README.md`
- Modify: `profiles/development-toolchain/tests/python/controllers-test.py`
- Create: `profiles/development-toolchain/cross/tests/fortran-smoke.py`
- Modify: `profiles/development-toolchain/bootstrap/pipeline.py`
- Modify: `profiles/development-toolchain/bootstrap/README.md`
- Modify: `profiles/development-toolchain/bootstrap/runtime_libraries.py`
- Modify: `profiles/development-toolchain/runtime/recipe/files/runtime.py`
- Modify: `profiles/development-toolchain/runtime/recipe/Makefile`
- Modify: `profiles/development-toolchain/runtime/recipe/PLIST`
- Modify: `profiles/development-toolchain/runtime/recipe/DESCR`
- Modify: `profiles/development-toolchain/runtime/recipe/files/relro.py`
- Modify: `profiles/development-toolchain/runtime/recipe/files/inheritance.py`
- Modify: `profiles/development-toolchain/runtime/tests/package-test.py`
- Modify: `profiles/development-toolchain/runtime/README.md`

**Interfaces:**
- Consumes: The existing GCC 16.2.0 archive, AArch64 cross Binutils, and verified EmberBSD sysroot.
- Produces: A target `aarch64--netbsd-gfortran`, a receipted Fortran runtime stage, and a `gcc16-runtime` package with the required Fortran runtime SONAMEs.

- [ ] **Step 1: Add failing fixtures for Fortran mode and runtime selection.** Check compiler options, target identity, runtime selections, and rejection of unrecorded or foreign runtime files.
- [ ] **Step 2: Run the focused fixtures.** Confirm they fail because the current scripts do not accept the Fortran mode or runtime selection.
- [ ] **Step 3: Implement the opt-in Fortran runtime build.** Build the target libraries from the GCC 16.2 source and record their exact ordered selection.
- [ ] **Step 4: Extend the runtime provider.** Validate and package the selected libraries. Preserve the existing C++-only selections, inheritance checks, RELRO rules, and package identity checks.
- [ ] **Step 5: Build the AArch64 application cross compiler with the Fortran frontend.** Use a fresh sysroot containing the accepted runtime provider.
- [ ] **Step 6: Add and run the target Fortran smoke check.** Compile and link an I/O program. Inspect its ELF machine, SONAME dependencies, and dynamic paths.
- [ ] **Step 7: Run the focused host fixtures and the real AArch64 runtime/compiler builds.** Save logs, receipts, package hash, and exact compiler/runtime versions.
- [ ] **Step 8: Commit the reviewed toolchain and runtime changes.**

### Task 2: Enable pkgsrc cross Fortran through Ports

**Files:**
- Modify: `profiles/common-build-tools/cross/mk.conf`
- Modify: `profiles/common-build-tools/cross/README.md`
- Modify: `profiles/common-build-tools/libtool.md`
- Modify: `scripts/prepare-pkgsrc.py`
- Modify: `scripts/check-published-patches.sh`
- Create: `profiles/common-build-tools/patches/pkgsrc-cross-fortran.patch`
- Create: `profiles/common-build-tools/tests/cross-fortran.py`
- Modify: `profiles/common-build-tools/tests/source-profile.sh`

**Interfaces:**
- Consumes: Task 1 compiler and runtime.
- Produces: Cross `FC`/`F77` selection, Fortran-aware cross-Libtool, and a fresh pkgsrc export that accepts Fortran packages.

- [ ] **Step 1: Add a failing export fixture.** Check patch registration, compiler wrappers, pkgsrc Fortran acceptance, and cross-Libtool paths.
- [ ] **Step 2: Run the fixture against the unmodified export.** Confirm it exposes the current blanket Fortran rejection and missing cross-Libtool selection.
- [ ] **Step 3: Add the pkgsrc patch and target compiler configuration.** Keep C/C++ cross behavior unchanged. Apply changes only to exported pkgsrc trees.
- [ ] **Step 4: Run export and metadata checks.** Verify `FC`, `F77`, `PKG_LIBTOOL`, and `PKG_SHLIBTOOL` select target-aware tools with no host sysroot paths.
- [ ] **Step 5: Build a real Fortran BLAS package through pkgsrc.** Run normal package checks and inspect the target ELF dependencies.
- [ ] **Step 6: Commit the reviewed Ports cross-support changes.**

### Task 3: Build NumPy with BLAS and package openTPU

**Files:**
- Create: `pkgsrc/local-ai/py-opentpu/PLIST`
- Modify: `README.md`
- Modify: `profiles/ai-cpu/README.md`

**Interfaces:**
- Consumes: Tasks 1 and 2, the verified target sysroot, and the approved py-opentpu recipe.
- Produces: AArch64 NumPy and openTPU packages, package payload checks, and host test evidence.

- [ ] **Step 1: Prepare a fresh `common-build-tools` export and task-owned cross configuration.** Record disk space and exact temporary paths.
- [ ] **Step 2: Build the current target BLAS package and NumPy 2.5.3.** Use GCC16, the Fortran runtime provider, and ordinary pkgsrc BLAS configuration.
- [ ] **Step 3: Generate and review the openTPU PLIST.** Confirm all Python modules, metadata, entry points, data files, license, and provenance are present.
- [ ] **Step 4: Build the AArch64 openTPU package.** Run pkgsrc checksum, staging, dependency, PLIST, and package checks.
- [ ] **Step 5: Inspect package scripts and dependencies.** Check target Python shebangs, NumPy package dependency, architecture, payload, and package SHA256.
- [ ] **Step 6: Run the selected host openTPU tests.** Report host tests separately from target package checks.
- [ ] **Step 7: Update Ports and wiki E8/E11 status from accepted evidence.** Keep E8's remaining independent items open.
- [ ] **Step 8: Commit the reviewed package and evidence updates.**

### Task 4: Final review and cleanup

- [ ] **Step 1: Run the focused regression suite for changed scripts, runtime packaging, pkgsrc export, and target package checks.**
- [ ] **Step 2: Run the whole-branch review and resolve load-bearing findings.**
- [ ] **Step 3: Preserve the accepted package, hashes, and concise evidence outside Git.**
- [ ] **Step 4: Remove only task-owned temporary trees after verifying retained outputs.** Keep shared toolchains, sysroots, pkgsrc caches, and unrelated artifacts.
- [ ] **Step 5: Record disk space before and after cleanup, then commit and push the final evidence update.**
