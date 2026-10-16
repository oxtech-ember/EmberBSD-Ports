# Generated KConfig consumer

This check exercises the native KConfig 6.31 generator, the installed target
CMake macros and generated C++ against common KConfig/Qt 6.12 libraries.
Build the [native generator](../../cross/frameworks.md) first.
The default target is AArch64. Select `--target amd64` for NetBSD/x86_64:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
PKG_CONFIG=/absolute/native/pkgconf \
sh build.sh --target amd64 /absolute/cross-tools /absolute/sysroot \
    /absolute/host-qt/qtbase /absolute/kconfig-host/tooling /absolute/new-build
```

The selected cross tools must include GCC 16.2.0 `g++` and `readelf`.
The builder checks the compiler triple and version, the seed libc ELF and
the resulting executable ELF64 machine. CMake processor, compiler and CRT
paths use the same target. Unknown targets and mixed inputs fail.
`target.txt` and `inputs-output.sha256` record the selected target and tools.
No target executable runs during this host build.

The shared entrypoint fixture is
`profiles/common-graphics/tests/acceptance-entrypoints.rb`. Set `READELF` to a
real host cross readelf. Optionally set `CROSS_TEST_TOOLS` to an actual amd64
GCC16 prefix for compiler identity checks. CMake, native generator and target
query responses are controlled boundaries; synthetic ELF headers are inspected
by real readelf. These fixtures do not build Qt/KConfig or establish target
runtime acceptance. The amd64 consumer still needs a genuine application
cross build and the following target run.

On EmberBSD, install the ordinary KConfig package and run:

```sh
sh run.sh /absolute/kconfig-consumer /absolute/new-results
```

The isolated configuration first uses its generated default. A second process
saves a value and a fresh process reads it. A deliberately wrong expectation
must exit 3. Installed `kwriteconfig6` and `kreadconfig6` then share the same file
with the generated consumer. The runner does not modify desktop settings.

On 2026-10-12 the macOS/arm64 native generator and GCC16 AArch64 consumer built.
CMake rejects a nonmatching native generator before building and accepts
repeated imports through independent Frameworks dependencies. GCC `-fanalyzer`
object compilation and Cppcheck 2.22 using the real compile database pass.
The installed consumer passes on physical CM5, including fresh-process
persistence and interoperability with the packaged command-line utilities.
This is a configuration API check, not a desktop session.
