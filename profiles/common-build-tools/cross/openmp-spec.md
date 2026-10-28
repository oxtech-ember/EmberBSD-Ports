# Select GCC16 OpenMP development metadata

GCC reads `libgomp.spec` through its compiler-prefix search.
`--sysroot` and a GCC16 CRT `-B` path alone can select the base compiler's
`/usr/lib/libgomp.spec`. A library `-L` path does not select this specs file.
With the GCC16 override, the common cross profile also appends `-B` for the staged
`/usr/pkg/gcc16/lib/` directory to its C and C++ wrappers.
This selects the matching GCC16 specs file before the base copy.
The existing CRT path, library path and target RPATH remain necessary.

Keep `omp.h`, `libgomp.spec` and the development linker files in the build-host
sysroot. The runtime-only package supplies the target shared library.
Its canonical GCC16 NetBSD SONAME is `libgomp.so.1`.
Do not substitute the base compiler's `libgomp.so.2` or add an ABI alias.

## Real compiler and pkgsrc regression

The [focused regression](../tests/cross-openmp-spec.rb) takes an exported
pkgsrc tree, a working cross MAKECONF, historical and current profiles,
and a new output directory:

```sh
git show f1b437c:profiles/common-build-tools/cross/mk.conf > /absolute/old-cross.mk
BMAKE=/absolute/host/bin/bmake ruby \
    profiles/common-build-tools/tests/cross-openmp-spec.rb \
    /absolute/export /absolute/cross.mk.conf /absolute/old-cross.mk \
    /absolute/ports/profiles/common-build-tools/cross/mk.conf \
    /absolute/new-openmp-spec-check
```

The host needs native pkgsrc C wrappers and the tools required to generate
them. The target sysroot needs both genuine specs files, matching GCC16
development files and the runtime package database. Use GCC 16.2.0 with the
literal `aarch64--netbsd` or `x86_64--netbsd` target triplet.
The MAKECONF must include exactly one common cross profile. Keep any private
`CWRAPPERS_APPEND` overrides out of that input; they would mask the old profile.

The test copies the MAKECONF and each profile into its output directory.
It queries actual `devel/zlib` metadata and uses separate `WRKOBJDIR` values.
It invokes pkgsrc's real compiler-dispatch and C-wrapper generation rules in
the normal post-barrier mode. That mode includes the buildlink transformations;
omitting it would produce incomplete wrappers that discard valid linker paths.
No extraction, package compilation, dependency installation or target execution
is requested. The package tree, shared sysroot and package databases stay read-only.

For C and C++, the test checks the actual driver's `-print-file-name` result,
the generated wrapper's result, and the specs pathname reported during linking.
The old profile must select the base copy. The current profile must select
the staged GCC16 copy. This compares independent compiler observations;
it does not check whether the profile contains a particular flag string.

Both profiles cross-compile the existing OpenMP C contract and link it through
their C and C++ wrappers. The test checks actual ELF architecture, `libgomp.so.1`
and target RPATH, and rejects build-host runtime paths. It retains source,
profile, compiler, specs, header and wrapper hashes, child statuses and logs.
The C++ check links the same C object with the genuine C++ driver; it does not
claim separate C++ OpenMP source-language coverage.

On 2026-10-18, the real AArch64 GCC16 Linux-host run passed all four links
and both direct/wrapper selection comparisons. Both specs files currently
contain the same `link_gomp` rule, so the old profile also links successfully
when normal buildlink paths are present. The regression detects the wrong
metadata provider without inventing a historical link failure.
The amd64 path has not run in this check. ELF linking does not establish
OpenMP execution; use the [runtime contract](../../development-toolchain/tests/libgomp.md)
and the accepted package in an EmberBSD VM for that result.
