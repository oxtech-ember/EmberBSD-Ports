# GCC16 NetBSD cross math capabilities

The NetBSD cross branch previously defined only an old subset of math
capabilities. The target headers and libm can provide the remaining names,
but `<cmath>` hides their `std::` imports without the generated HAVE macros.
The complete upstream standard modules export those names and fail to compile.
Ordinary scalar C++ overloads can still compile through compiler builtins.

`patches/gcc-netbsd-math.patch` adds the existing upstream
`GLIBCXX_CHECK_MATH_SUPPORT` only for NetBSD. It keeps OpenBSD's path unchanged.
The macro disables builtins, compiles declarations and links real functions
against the selected target libm. Missing declarations or symbols remain
unavailable. No consumer capability defines, new math implementation or ABI
change is introduced. GNU Autoconf 2.69 generates the matching configure patch.
The unchanged script is reproduced before regeneration, apart from the
existing pkgsrc libstdc++ SONAME substitution.

The source is GCC 16.2.0 from the original archive pinned in `sources.tsv`.
The local AI-assisted patch is not submitted or accepted upstream. GCC keeps
its copyright, GPLv3+ and Runtime Library Exception. The helpers and independent
fixture use BSD-2-Clause. GNU's [libstdc++ maintenance guide](https://gcc.gnu.org/onlinedocs/libstdc++/manual/appendix_porting.html)
explains the generated configure boundary.

## Reproduce the source checks

Use a new pkgsrc export, the original GCC archive, the genuine GCC16 target
compiler prefix, and a coherent EmberBSD SDK. The compiler must report 16.2.0
and the selected canonical target. The helper never executes target programs.

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK GNU_MAKE=/absolute/gmake \
python3 -B profiles/development-toolchain/tests/cross-math/check.py \
    aarch64 /absolute/new-pkgsrc /absolute/gcc-16.2.0.tar.xz \
    /absolute/gcc16-prefix /absolute/emberbsd-sdk /absolute/new-output
sh profiles/development-toolchain/tests/source-profile.sh
python3 -B profiles/development-toolchain/runtime/tests/package-test.py \
    --sdk-source /absolute/EmberBSD-SDK
```

The independent fixture keeps relocations for 43 literal function names.
The helper prepares audited sources, reverses only the new generated-configure
patch for the baseline, and runs real fresh cross configurations without math
cache answers. It requires the baseline namespace and complete std module to
fail. The candidate must compile and link all names, both complete upstream
modules, and both module consumers. BMI files must be nonempty, and the full
module sources must retain their exact original concatenated bytes. The
upstream make rule's empty-module fallback is not used as acceptance.

Negative inputs use private copies: one missing target declaration, one removed
libm archive member, and one removed generated capability. They must not produce
a positive capability. The selected SDK and previous build receipts are never
changed. Target math numerics, installed module execution and package lifecycle
remain separate gates. No replacement pkg_tools implementation is provided.

## Package identity

This repair introduced compiler `gcc16-16.2.0nb3`, companion libs nb4 and the
runtime-only nb4. The [TLS repair](cross-tls.md) advances them to nb4, nb5
and nb5. The old accepted runtime nb3 cohort retains its identity. The current runtime verifier authenticates both exact
source patches and the staged target capability header through the existing
source and stage manifests. A historical verifier remains read-only and cannot
install or package an old stage as the new revision. The locale-only
inheritance schema and its permitted source delta stay unchanged; this repair
needs a separate coherent build.
