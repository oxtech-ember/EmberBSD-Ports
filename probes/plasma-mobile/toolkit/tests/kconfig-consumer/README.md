# Generated KConfig consumer

This check exercises the native KConfig 6.31 generator, the installed target
CMake macros and generated C++ against common KConfig/Qt 6.12 libraries.
Build the [native generator](../../cross/frameworks.md) first.

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
PKG_CONFIG=/absolute/native/pkgconf \
sh build.sh /absolute/cross-tools /absolute/sysroot \
    /absolute/host-qt/qtbase /absolute/kconfig-host/tooling /absolute/new-build
```

On EmberBSD, install the ordinary KConfig package and run:

```sh
sh run.sh /absolute/kconfig-consumer /absolute/new-results
```

The isolated configuration first uses its generated default. A second process
saves a value and a fresh process reads it. A deliberately wrong expectation
must exit 3. Installed `kwriteconfig6` and `kreadconfig6` then share the same file
with the generated consumer. The runner does not modify desktop settings.

On 2026-10-12 the macOS/arm64 native generator and GCC16 AArch64 consumer built.
CMake rejects a nonmatching native generator before building and accepts\nrepeated imports through independent Frameworks dependencies. GCC `-fanalyzer`
object compilation and Cppcheck 2.22 using the real compile database pass.
CM5 runtime execution remains pending; no persistence or desktop pass is claimed.
