# Mesa sealer prefix regression

```sh
python3.15 -B -E -S profiles/common-graphics/tests/mesa-sealer-prefix.py \
    --sdk-source /absolute/EmberBSD-SDK --work-parent /absolute/private-work-parent
```

Add `--host-prefix /absolute/host-pkg-llvm --archive /absolute/mesa-26.2.6.tar.xz`
to run the source-patch check. It selects only bsdtar and patch from that prefix.
It extracts five pinned archive files. The production BSD-compatible patch
argv applies the canonical BVNC, host Objective-C and sampler-layout patches
with zero fuzz and no backup or reject files. BVNC and Objective-C use no
offsets. The unchanged sampler-layout patch has one expected offset of 84 lines
in the pinned 26.2.6 archive. Any other offset fails. It compiles nothing.

The check imports the real sealer. It uses the current SDK `load_host_prefix`
on native-header byte fixtures. It requests only bsdtar, patch, otool and spirv-val.
It runs no fixture executable, compiler query, generator or shader smoke.
This does not qualify an installed host prefix.

Standalone sealing requires `--host-prefix`, `--pkgdb` and `--lock-directory`.
Use the same absolute package database and lock namespace as the package writer.
A shared SDK context lease protects the prefix and package database before tool
selection and until sealing ends. The fixture checks writer exclusion, nested
read leases, refusal before work on a busy input and release after an error.
The SDK rejects output overlap with the prefix, package database, source or
build. This includes aliases and protected ancestor paths before work creation.

The runtime fixtures use the selected otool text interface. They cover shared
LLVM, Translator, SPIRV-Tools and GCC runtime paths, image-local and inherited
`@rpath`, `@loader_path`, cycles and a copied output location. OS ABI paths
are terminal. Prefix escapes, external symlinks, missing tools, unresolved
paths, conflicting otool output and embedded dyld environment commands fail.
A causal case removes only containment and must admit the same outside fixture.

The sealer resolves real `@rpath` files. It does not infer the existence of
an `@rpath` image in the dyld shared cache. Direct absolute OS ABI loads remain
supported. `LC_LAZY_DYLIB_INFO` is rejected because otool's load-command text
does not decode its indirect library paths. Neither limitation is hidden.

Actual sealing still copies the genuine Mesa tools and runs the unchanged
OpenCL, validator, NIR and selected PCO smoke steps. These fixtures do not
establish that build, shader output, package execution or GPU runtime.
