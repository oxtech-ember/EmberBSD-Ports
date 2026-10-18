# LLVM full-stage reuse validator

`recipes/lang/llvm/files/reuse-package-stage.py` validates a repeat installation
from one accepted LLVM 23.1.3 cross build. It does not build LLVM, install a
package into a sysroot, or create a package identity. The opt-in pkgsrc adapter retains ordinary SDK package checks.
Acceptance of an actual runtime/SDK pair remains a separate build result.

Before recording a reference, complete the ordinary runtime package checks and
archive audit. Supply that archive's accepted SHA256 in the input JSON.
The validator runs
`cmake --install` with the recipe's strip mode into an empty private reference
DESTDIR. It records CMake output in `DESTDIR.llvm-install.log`.
It checks source and object inputs before and after that installation.
Use the complete normalized pkgsrc PLIST and both normalized partition PLISTs.
The validator compares the runtime subset with the accepted package manifest.
It checks the full partition, directly staged ELF headers and Mach-O magic.
The archive digest is a trust input. This helper does not replace the archive
or dependency-closure auditor.

The input JSON uses schema `2` and these fields:

- `version`: `23.1.3`.
- `target`: `opsys`, `version`, `arch`, and `triple`. Supported pairs are
  NetBSD 11.0 with `aarch64`/`aarch64--netbsd` or
  `x86_64`/`x86_64--netbsd`.
- `runtime_work`: the existing common runtime WRKDIR.
- `source`, `build`, `recipe`, `sdk_recipe`: existing absolute tree paths.
  The generated build directory must be inside the recorded source tree.
  Both DESTDIRs must be separate from all four input trees. Place the receipt
  outside those input trees and the reference DESTDIR.
- `flags`: the actual compile/ABI contract. The recipe adapter must produce
  this from current pkgsrc inputs, including the checked configure environment, `MAKE_ENV`, `CMAKE_BUILD_ARGS`,
  selected build tool, build directories and targets, and install command fields.
  `prepare-reuse-inputs.py` replaces this field with current values. It queries
  both roles at `runtime_work` and does not rewrite flag or environment strings.
  A caller must not substitute the receipt's old flags for current values.
- `files`: lists of absolute input paths, grouped by `compiler`, `native_tools`,
  `patches`, and `target_abi`. The last group records the actual external target
  headers and library inputs. Additional groups can hold compile databases
  and provenance.
- `cmake`, `python`, `tar`: selected executable native tools. All three must also
  occur in `files.native_tools`.
- `sdk_source`: the explicit SDK API source. The preparer records all API
  Python files in `files.sdk_api`.
- `install_strip`: the current CMake strip mode (`true` or `false`). Match
  pkgsrc `INSTALL_TARGET`. Record the actual target strip tool and wrapper in
  `files.compiler`. Use the same strip mode for the full reference stage.
- `runtime`: the accepted `archive` path and its `sha256`.
- `manifests`: paths named `full`, `runtime`, and `devel`.

Use one native Python interpreter and SDK API version 1. Set
`EMBERBSD_SDK_SOURCE` to the explicit SDK source directory. The helper does
not install the SDK. The commands are:

```sh
python3 -B reuse-package-stage.py record INPUTS.json EMPTY_REFERENCE_DESTDIR NEW_RECEIPT.json
python3 -B reuse-package-stage.py verify CURRENT_INPUTS.json RECEIPT.json ACCEPTED_SHA256
python3 -B reuse-package-stage.py install CURRENT_INPUTS.json RECEIPT.json ACCEPTED_SHA256 EMPTY_DESTDIR
```

Schema 1 receipts remain readable for immutable verification. They cannot
run a new installation. Record schema 2 with current Python and SDK inputs
for a new installation. Full LLVM inventories use a bounded 128 MiB JSON
limit; the ordinary SDK JSON default remains 16 MiB.

Accept and pin the receipt hash outside the helper before using `install`.
The helper hashes source, recipe, patch, compiler, native-tool and object inputs.
It hashes the normalized manifests and accepted runtime archive. It checks these
inputs before and after installation. CMake may rewrite `install_manifest.txt`;
this is the only excluded generated metadata file. Original objects and source
files must retain their bytes, modes and link targets.

Before CMake starts, the helper creates `.llvm-reuse-quarantine.json` inside
the canonical build directory. This reserved marker moves with the build when
any ancestor is renamed. It prevents concurrent reuse and survives abrupt
caller termination. An existing marker rejects every input snapshot. The
helper does not exclude the marker from an accepted immutable inventory.
After a completed producer or a proven interruption drain, the helper removes
only its unchanged marker.
A completed nonzero status, including `97`, permits a new empty stage.

If the SDK raises `ProcessOwnershipError`, the helper retains the marker.
All `record`, `verify`, and `install` calls then refuse the same build identity.
An ancestor alias, build rename, or complete source relocation keeps this guard.
Malformed markers and marker symlinks also cause refusal. Before recovery,
prove that the producer session has stopped. Check the source and object hashes.
Preserve the marker and install log as evidence before controlled marker removal.
Do not relocate the source tree to avoid the quarantine check.

The private full stage must match the reference bytes, modes and symlinks before
partition selection. This check also rejects an input that changes temporarily
during installation and then returns to its recorded state. Run the ordinary
SDK selector and pkgsrc package checks after this gate. A successful helper run
is not SDK package acceptance. Keep failed private stages for diagnosis until
the caller has preserved the required evidence.

`tests/llvm-stage-reuse.py CMAKE NEW_WORK` exercises real CMake installation
with labelled data fixtures. It checks input drift, incomplete stages, temporary
object mutation, and mutation after installation. It does not compile LLVM or
claim target runtime acceptance.
`tests/llvm-reuse-recovery.py NEW_WORK` injects typed process results to check
quarantine and safe retry policy without starting producers.
`tests/llvm-host-status.py NEW_WORK` checks the actual native CLI main blocks
with injected failures and signals. Set `EMBERBSD_SDK_SOURCE` for these tests.

## Prepare the current pkgsrc contract

Supply a native Python executable with `EMBERBSD_LLVM_REUSE_PYTHON` and the input
inventory JSON with `EMBERBSD_LLVM_REUSE_INPUTS`. Run `llvm-reuse-inputs` in the
runtime recipe after the ordinary runtime package and archive checks. Use the
same selected environment and command-line compilation settings as the build.
The target writes `${WRKDIR}/.llvm-reuse-inputs.json`. It rejects overlap with
the accepted receipt, including a hardlink alias, before an atomic JSON write.

The Python preparer runs the current recipe's post-barrier metadata query at the
common runtime WRKDIR. It retains command-line overrides through MAKEFLAGS and
uses bmake `-v` to read expanded variables. `_MAKEVARS_MK=defined` prevents the
query from reading old phase caches. This is a read-only query; it does not
configure or compile the source. Current recipe roots, target ABI, source and
build roots must match the supplied inventory. The preparer records the loaded
pkgsrc makefiles and current native tools. The selected GCC drivers and strip
tool must occur in the explicit compiler inventory.

Review that inventory before accepting the runtime receipt. Include compiler
internals, wrappers and their configuration, selected native tool inputs, and
the actual external target headers and link inputs. Use the compiler dependency
files and target provider manifests to prove the selected ABI inputs. Do not
substitute the old installed LLVM package for a fresh source or build receipt.
The source and patch provenance and actual compile database remain required
build evidence. An incomplete inventory is not acceptance.

Use the generated context with `record`. Pin the accepted receipt hash. Check
that the ordinary SDK target dependencies are already installed before starting
its package phase. Coordinate any provider replacement separately.

For the SDK package, set the explicit SDK source and all four reuse variables:

```sh
bmake package \
  EMBERBSD_SDK_SOURCE=/absolute/SDK/source \
  EMBERBSD_LLVM_REUSE_PYTHON=/absolute/native/python3 \
  EMBERBSD_LLVM_REUSE_INPUTS=/absolute/inventory.json \
  EMBERBSD_LLVM_REUSE_RECEIPT=/absolute/accepted-receipt.json \
  EMBERBSD_LLVM_REUSE_SHA256=ACCEPTED_SHA256
```

This opt-in is valid only for the separate NetBSD cross SDK. Its private WRKSRC
holds pkgsrc state. `NO_BUILD` and `NO_CONFIGURE` prevent another LLVM compile.
The extract and patch overrides verify the accepted context; pkgsrc creates its
normal phase cookies. The install override repeats CMake installation into the
private SDK DESTDIR. The full-stage equality gate runs before the existing SDK
partition selector and ordinary package checks. Source and object trees stay at
the accepted common location. Native full LLVM and default cross builds retain
their existing path.

`tests/llvm-reuse-adapter.py PKGSRC MAKECONF BMAKE NEW_WORK` uses actual pkgsrc
queries with an explicitly labelled input fixture. It checks command override
propagation, literal SDK paths inside arbitrary flags and environment values,
refusal of an unaccepted receipt at the extract, patch and install hooks, and
a real CMake fixture installation through those hooks. The ordinary SDK PLIST
gate must reject that deliberately incomplete fixture. These tests do not
compile LLVM or establish acceptance of a target package.
