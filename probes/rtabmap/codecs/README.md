# Shared PNG and JPEG providers

This helper builds the existing common providers for the RTAB-Map CPU profile:

- PNG 1.6.59 from `pkgsrc/graphics/png`;
- libjpeg-turbo 3.2.0nb2 from the pinned pkgsrc `graphics/libjpeg-turbo` recipe.

It does not add another provider recipe. It checks the original archive pins
and each canonical patch checksum before applying the recipe patches.
It keeps PNG's chunk-cache and allocation limits, default APNG selection,
and architecture flags. It keeps JPEG8 ABI compatibility, position-independent
code, system zlib, and the recipe's five patches.

The helper requires GCC 16.2.0, Ruby, GNU make, CMake, Ninja, patch, tar,
and SHA256/SHA1 utilities. Use an absolute new work directory. Set
`CODECS_JOBS=1` or `2` to control concurrent compiler jobs.

Fetch the two archives from [sources.tsv](sources.tsv). Set `jpeg_recipe`
to `graphics/libjpeg-turbo` inside the pinned pkgsrc export. The helper reads
the canonical PNG recipe from its owning Ports checkout.

```sh
sh probes/rtabmap/codecs/build.sh cross "$gcc_prefix" "$sysroot" /usr/pkg \
  "$archives" "$jpeg_recipe" "$new_cross_work"
```

The output contains `png/stage/usr/pkg` and `jpeg/stage/usr/pkg`.
Their `files.txt` manifests must match the canonical PLIST. The PNG check
expands its libtool `.la` entry into the platform's real libraries. It also
keeps `.la`, static archives, tools, headers, pkg-config files, and manuals.
The JPEG check compares all 41 entries directly.
PNG's raw compiler log also retains configure probes. Select library source
entries when using its compilation database; transient configure sources no
longer exist after configuration.

`merge-stage.rb STAGE_PREFIX TARGET_PREFIX RECEIPT` merges only new or
byte-identical entries. It rejects an existing incompatible provider.
Use the normal package tools for target installation and lifecycle checks.

Build the portable native controls separately:

```sh
sh probes/rtabmap/codecs/build.sh native "$native_gcc_prefix" - "$native_prefix" \
  "$archives" "$jpeg_recipe" "$new_native_work"
```

The native control disables x86 SIMD because this bounded Memcheck profile
does not require NASM. The AArch64 target uses the normal ARM64 SIMD backend.
Native portable-code results do not establish x86 SIMD correctness or
physical-device performance.

Prepare the real upstream test programs and their licensed fixtures:

```sh
sh probes/rtabmap/codecs/prepare-tests.sh "$new_cross_work" /usr/pkg "$new_tests"
```

Install the PNG and JPEG packages in EmberBSD AArch64. Copy the test directory
there, then run `sh run-tests.sh ABS_TESTS ABS_NEW_RESULTS`. The selected
checks cover PNG roundtrip and standard transforms, JPEG roundtrip, YUV,
16-bit lossless encoding, CLI encoding/decoding, and empty or truncated input.
The script rejects unexpected exit codes and records every executed case.

For native Memcheck, prepare a separate native test directory. Select the
native prefix in `LD_LIBRARY_PATH` and set `CODECS_MEMCHECK=1`. Every selected
executable runs with leak, uninitialized-value, and invalid-access checking.
Memcheck errors return 99 and fail the suite. The native tests and the actual
EmberBSD target run remain separate evidence.

The helpers are AI-assisted EmberBSD implementations under [MIT](LICENSE).
The upstream libraries retain their original licenses and authorship.
