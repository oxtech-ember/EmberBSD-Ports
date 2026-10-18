# LLVM full-stage reuse validator

`recipes/lang/llvm/files/reuse-package-stage.rb` validates a repeat installation
from one accepted LLVM 23.1.3 cross build. It does not build LLVM, install a
package into a sysroot, or create a package identity. The opt-in pkgsrc adapter retains ordinary SDK package checks.
Acceptance of an actual runtime/SDK pair remains a separate build result.

Before recording a reference, complete the ordinary runtime package checks and
archive audit. Supply that archive's accepted SHA256 in the input JSON.
The validator runs
`cmake --install` with the recipe's strip mode into an empty private reference
DESTDIR. It checks source and object inputs before and after that installation.
Use the complete normalized pkgsrc PLIST and both normalized partition PLISTs.
The validator compares the runtime subset with the accepted package manifest.
It checks the full partition, directly staged ELF headers and Mach-O magic.
The archive digest is a trust input. This helper does not replace the archive
or dependency-closure auditor.

The input JSON uses schema `1` and these fields:

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
  this from current pkgsrc inputs, including the checked configure environment.
  `prepare-reuse-inputs.rb` replaces this field with current values. It queries
  both roles at `runtime_work` and does not rewrite flag or environment strings.
  A caller must not substitute the receipt's old flags for current values.
- `files`: lists of absolute input paths, grouped by `compiler`, `native_tools`,
  `patches`, and `target_abi`. The last group records the actual external target
  headers and library inputs. Additional groups can hold compile databases
  and provenance.
- `cmake`, `perl`, `tar`: selected executable native tools. All three must also
  occur in `files.native_tools`.
- `install_strip`: the current CMake strip mode (`true` or `false`). Match
  pkgsrc `INSTALL_TARGET`. Record the actual target strip tool and wrapper in
  `files.compiler`. Use the same strip mode for the full reference stage.
- `runtime`: the accepted `archive` path and its `sha256`.
- `manifests`: paths named `full`, `runtime`, and `devel`.

Use a native Ruby interpreter. The commands are:

```sh
ruby reuse-package-stage.rb record INPUTS.json EMPTY_REFERENCE_DESTDIR NEW_RECEIPT.json
ruby reuse-package-stage.rb verify CURRENT_INPUTS.json RECEIPT.json ACCEPTED_SHA256
ruby reuse-package-stage.rb install CURRENT_INPUTS.json RECEIPT.json ACCEPTED_SHA256 EMPTY_DESTDIR
```

Accept and pin the receipt hash outside the helper before using `install`.
The helper hashes source, recipe, patch, compiler, native-tool and object inputs.
It hashes the normalized manifests and accepted runtime archive. It checks these
inputs before and after installation. CMake may rewrite `install_manifest.txt`;
this is the only excluded generated metadata file. Original objects and source
files must retain their bytes, modes and link targets.

The private full stage must match the reference bytes, modes and symlinks before
partition selection. This check also rejects an input that changes temporarily
during installation and then returns to its recorded state. Run the ordinary
SDK selector and pkgsrc package checks after this gate. A successful helper run
is not SDK package acceptance. Keep failed private stages for diagnosis until
the caller has preserved the required evidence.

`tests/llvm-stage-reuse.rb CMAKE PERL NEW_WORK` exercises real CMake installation
with labelled data fixtures. It checks input drift, incomplete stages, temporary
object mutation, and mutation after installation. It does not compile LLVM or
claim target runtime acceptance.

## Prepare the current pkgsrc contract

Supply a native Ruby executable with `EMBERBSD_LLVM_REUSE_RUBY` and the input
inventory JSON with `EMBERBSD_LLVM_REUSE_INPUTS`. Run `llvm-reuse-inputs` in the
runtime recipe after the ordinary runtime package and archive checks. Use the
same selected environment and command-line compilation settings as the build.
The target writes `${WRKDIR}/.llvm-reuse-inputs.json`.

The Ruby preparer runs the current recipe's post-barrier metadata query at the
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

For the SDK package, set all four variables:

```sh
bmake package \
  EMBERBSD_LLVM_REUSE_RUBY=/absolute/native/ruby \
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

`tests/llvm-reuse-adapter.rb PKGSRC MAKECONF BMAKE NEW_WORK` uses actual pkgsrc
queries with an explicitly labelled input fixture. It checks command override
propagation, literal SDK paths inside arbitrary flags and environment values,
refusal of an unaccepted receipt at the extract, patch and install hooks, and
a real CMake fixture installation through those hooks. The ordinary SDK PLIST
gate must reject that deliberately incomplete fixture. These tests do not
compile LLVM or establish acceptance of a target package.
