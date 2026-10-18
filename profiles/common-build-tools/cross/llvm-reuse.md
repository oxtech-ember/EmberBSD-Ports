# LLVM full-stage reuse validator

`recipes/lang/llvm/files/reuse-package-stage.rb` validates a repeat installation
from one accepted LLVM 23.1.3 cross build. It does not build LLVM, install a
package into a sysroot, or create a package identity. The pkgsrc recipe adapter
and acceptance of an actual runtime/SDK pair remain separate work.

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
- `source`, `build`, `recipe`, `sdk_recipe`: existing absolute tree paths.
  The generated build directory must be inside the recorded source tree.
- `flags`: the actual compile/ABI contract. The recipe adapter must produce
  this from current pkgsrc inputs, including the checked configure environment.
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
