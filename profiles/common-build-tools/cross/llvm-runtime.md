# LLVM runtime and target SDK packages

NetBSD cross builds for AArch64 and amd64 produce two ordinary source packages:

| Package | Payload |
| --- | --- |
| `llvm-23.1.3nb1` | Shared libLLVM, libLTO and libRemarks, their aliases and the upstream license notice. |
| `llvm-devel-23.1.3nb2` | Target tools, headers, static archives, CMake exports and test support. Requires the exact runtime package. |

The runtime keeps the original name for dependency and vulnerability matching.
Runtime revision `nb1` distinguishes it from the earlier complete package.
SDK revision `nb2` adds the direct Python dependency for installed scripts.
Both cross roles use native Python tools without Python C API build flags.
Their lit buildlink role supplies build/test scripts without target RPATHs.
The SDK retains explicit Python/lit runtime dependencies and conflicts with
that earlier package. Native LLVM keeps its complete manifest
and package identity. The separate SDK requires a NetBSD cross build.

Both recipes use the same LLVM 23.1.3 archive, patches and source component.
Each performs an independent full build and installation into its own stage.
This costs two builds. It avoids a shared build-output handoff. All normal and
experimental backend defaults, RTTI, shared LLVM and installed gtest support
remain unchanged. This is a packaging split, not a smaller LLVM build.

Normal pkgsrc expands the full, runtime and SDK PLISTs. The partitions must be
disjoint and cover the complete manifest. The selector checks every staged
file before pruning. Missing, unknown, duplicate and unsafe paths fail.
Link resolution also rejects absolute, escaping, cyclic, missing and dangling
partition targets. Runtime links cannot traverse SDK files. SDK links can use
runtime files through the exact dependency. Selected bytes, modes and symlinks
remain unchanged. Ordinary package checks
run after selection. Do not filter completed archives or edit PROVIDES.

The runtime owns the license notice under `include/llvm/Support`. It does not
own headers. Python and lit remain build prerequisites for the runtime recipe.
The SDK retains their installed tool dependencies. The existing DSO dependencies
remain normal buildlink dependencies, including builtin zlib when selected.
Actual packaged REQUIRES and target ELF closure remain release gates.

`lang/llvm/buildlink3.mk` keeps runtime as a normal dependency and includes
`llvm-devel` with `BUILDLINK_DEPMETHOD=build`. Install both packages in the
build-host target sysroot. Keep native generators separate. The desktop
package-set auditor rejects an LLVM SDK, the old monolith, or an LLVM runtime
with missing or additional payload. It accepts only the prepared runtime
identity. A future LLVM update must update this explicit policy.

## Source packaging checks

Use the real exported pkgsrc tree and native pkgtools. The native manifest
query requires installed native libxml2 option metadata. All writable recipe
copies, objects, package archives and databases stay in the new test directory.

```sh
export EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
python3 -B profiles/common-build-tools/tests/llvm-package-split.py \
    /absolute/exported-pkgsrc /absolute/native-prefix \
    /absolute/cross-tools /absolute/sysroot /absolute/new-split-check
python3 -B profiles/common-build-tools/tests/llvm-package-lifecycle.py \
    /absolute/native-prefix /absolute/new-split-check /absolute/new-lifecycle
python3 -B profiles/common-build-tools/tests/llvm-stage-links.py \
    profiles/common-build-tools/recipes/lang/llvm/files/select-package-stage.py \
    /absolute/new-link-check
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK \
BSDTAR=/absolute/bsdtar python3 -B probes/plasma-mobile/toolkit/tests/package-set-llvm.py \
    /absolute/native-prefix /absolute/new-policy-check
```

These checks use real bmake, stage-selection targets and pkgtools. Payloads
are labelled text fixtures with representative DSO aliases. They establish
manifest selection, dependency roles, archive policy and private package
lifecycle behavior. They do not compile LLVM or execute target programs.

The [Linux/AArch64 split-package acceptance](llvm-linux-aarch64.md) now passes
both real builds, complete package checks, installed payload/ELF closure,
C API/bitcode, four default ORC JITLink lifecycles and ordinary runtime
removal/reinstallation in E34 VM. The accepted native metadata helper agrees
with all 16 target query groups and passes sealing/integrity checks.
The [Mesa26 consumer](../../common-graphics/cross/mesa-linux-aarch64.md) passes
full packaging, installed llvmpipe rendering, all 39 target invocations and
normal package removal/reinstallation on this stack.

The separate [reuse validator](llvm-reuse.md) checks a repeat installation from
accepted fresh objects. Its recipe adapter and actual package acceptance are
separate from these default independent builds.
