# Pixman OpenMP test configuration

The common graphics profile carries the complete canonical pkgsrc pixman 0.46.4
recipe. It preserves the six-entry installed interface and `libpixman-1.so.0` ABI.
The recipe restores upstream's automatic OpenMP detection for tests and benchmarks.
It keeps the existing architecture guards, GNU assembly and AArch64 NEON paths.
The rendering library itself does not acquire an OpenMP dependency.

The recipe originates in pkgsrc commit
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
Only its unconditional `-Dopenmp=disabled` workaround and obsolete missing-spec
comment are removed. The other six recipe files retain their canonical bytes.
The [manifest](../sources.tsv) pins the official X.Org archive and SHA-256.
Upstream's license remains in the archive's `COPYING` file.

## Validation

Two normal AArch64 pkgsrc configurations use the same GCC 16.2.0 toolchain and
registered GCC runtime revision 3. The canonical recipe skips OpenMP detection;
the profile recipe detects OpenMP 5.2 with the default `auto` option.
Both retain GNU inline assembly, AArch64 NEON, all 43 build targets and all
35 registered upstream tests. All 224 archived source entries remain unchanged.

One complete ordinary target build produces all 43 targets. Its 77 compiler
commands include 42 test commands with `-fopenmp`. Thirty-five resulting
executables require the actual `libgomp.so.1`. Normal package checks pass,
including PLIST, permissions, PIE, RELRO, runtime paths and work-path checks.
An independent archive/stage comparison verifies all six installed entries,
AArch64 identity, SONAME and installed pkg-config metadata.
The library's runtime path is `/usr/pkg/gcc16/lib:/usr/pkg/lib`.

The canonical recipe does not declare GTK, GLib or libpng build dependencies.
Those optional dependencies remain undiscovered in both configurations; their
demos and optional test support are not part of the accepted graph.
Target execution of these 35 tests, native pixman acceptance and full KiCad
application integration remain separate checks.

## Reproduction

Export the common graphics profile and use its normal GCC16 cross configuration.
Build `x11/pixman` with the ordinary `bmake package` target and an isolated
`WRKOBJDIR`. All declared native tools and target runtime dependencies must already
be installed when package database writes are reserved for another builder.
No additional Meson options or restricted build target are needed.

To compare an unchanged canonical configuration with the completed profile build:

```sh
ruby profiles/common-graphics/tests/pixman-openmp.rb \
  /cache/pixman-0.46.4.tar.xz \
  /baseline/work/pixman-0.46.4/output \
  /current/work/pixman-0.46.4/output \
  /toolchain/bin/aarch64--netbsd-readelf /results/pixman-openmp
```

The results directory must be new, with an existing parent outside both sources.
The helper verifies archived source bytes, actual Meson options, compiler identity,
unchanged test/target graphs, compiler arguments and every default output.
It retains ELF reports and input hashes. It does not run target programs or install
packages. The source exporter also rejects missing recipes, builtin guards,
architecture hacks and altered archive pins.
