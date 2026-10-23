# Cross-build Breeze with native SVG generators

Breeze Icons 6.31 needs two C++ generators on the build host. Its upstream
cross path imports those executables; it cannot execute target AArch64 tools
on macOS. The complete target package keeps both icon themes, generated 24px
icons, resource data and the shared Breeze Icons library.

## Build the tools

Use matching native Qt 6.12, ECM 6.31 and a native Python with lxml.
Python remains an existing upstream dependency for 24px icon generation.
The EmberBSD builder is a shell script. It verifies the source archive and
recipe patch hashes, applies patches with zero fuzz, then builds only the
two native C++ executables.

```sh
CMAKE=/absolute/cmake NINJA=/absolute/ninja \
HOST_CC=/absolute/cc HOST_CXX=/absolute/c++ \
HOST_PYTHON=/absolute/native-python3.14 JOBS=2 \
    sh build-breeze-host.sh /absolute/distfiles /absolute/native-qt \
    /absolute/native-prefix /absolute/native-ecm/cmake /absolute/new-work
```

Set `EMBERBSD_KF6_BREEZE_HOST=/absolute/new-work/prefix` in the private cross
MAKECONF. Keep the shared `EMBERBSD_KF6_HOST_TOOLING` setting from the
[KConfig workflow](frameworks.md). The recipe supplies explicit generator
paths to upstream CMake. Missing executables and old version markers fail.
Build a fresh native prefix after any generator patch changes.

The recipe also removes an inherited GCC14 workaround that discarded
`-fno-lto`. GCC16 accepts the upstream option. Breeze disables LTO because
its large Qt resources need that setting; the cross recipe preserves it.

## Two upstream generator errors

The [source patch](../../../../pkgsrc/graphics/breeze-icons/patches/patch-tools_generate-symbolic-dark.cpp)
fixes two independently reproduced errors:

- The generator assumed an input directory named `icons`. With another name,
  the computed output stayed absolute and could overwrite the input SVG.
  The output now uses the path relative to the selected input root.
- XML conversion errors only produced warnings. A partial write still returned
  success. Recorded file-open and XML errors now make the command fail.

Original KDE authorship and LGPL licensing remain in the source. This
AI-assisted EmberBSD patch has not been submitted to or accepted by upstream.

```sh
sh ../tests/breeze-generators.sh /absolute/new-work/prefix /absolute/new-check
BMAKE=/absolute/bmake MAKECONF=/absolute/cross.mk \
    sh ../tests/breeze-inputs.sh /absolute/prepared-pkgsrc \
    /absolute/new-work/prefix /absolute/new-input-check
```

The regression uses synthetic SVG files. It checks unchanged input bytes,
dark theme colours, symbolic aliases in a real QRC file and invalid XML
failures. Upstream reproduced both source overwrite and exit zero for malformed
XML. The corrected executables pass. `qrcAlias` intentionally aborts on invalid
XML; the test disables core files and verifies its diagnostic.

On 2026-10-12, the same regression passed with Apple Clang 21 ASan and UBSan
on macOS ARM64. Build the tools in a new directory with
`CXXFLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'` and
`LDFLAGS='-fsanitize=address,undefined'` to reproduce that instrumented build.
Run with `ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`.
This covers the generators, not uninstrumented Qt libraries or leak detection.
Valgrind Memcheck is not supported on this macOS ARM64 host; see the
[upstream platform list](https://valgrind.org/info/platforms.html).

Cppcheck 2.22.0 and Apple Clang 21 Static Analyzer also checked both original
and patched generator translation units. Both produced no diagnostics;
the functional regression found errors that static analysis did not report.
Use the builder's `build/compile_commands.json` and retain its actual Qt
headers, definitions and native platform. Cppcheck used the Qt model,
`--platform=unix64 --enable=warning,style,performance,portability --error-exitcode=1`.
Static Analyzer replayed those compiler commands with compile/output arguments
removed and `--analyze -Xanalyzer -analyzer-output=text` added.
These two native units are the analysis boundary, not the whole desktop.

The full `breeze-icons-6.31.0nb1` target package also passes normal package checks
and installation into the build sysroot. Its manifest includes all 70 new icons
from the release. SHA256:
`bb41f6915d0e0e4c97699df67052730e42a723ee535d4d84ef686caa31189307`.
On 2026-10-12 the installed package also passed the original KDE resource
test on CM5 running EmberBSD: 3 passed, no failures or skips. The test checks
the embedded theme index and selected icon bytes against the installed theme.
A second run without reference files exited 1 at `fsFile.open`, confirming
that missing data cannot produce a false pass. Boot time stayed unchanged.
This does not establish GUI rendering or an accelerated Plasma session.

Reproduce with the verified, patched Breeze source and the completed sysroot:

```sh
CMAKE=/absolute/cmake CXX=/absolute/aarch64--netbsd-g++ \
QT_HOST_PATH=/absolute/native-qt \
    ruby ../tests/build-breeze-resource.rb /absolute/breeze-source \
    /absolute/target-sysroot /absolute/new-test-build
# Install the normal Breeze package and its dependencies on the target.
sh breeze-resource-runtime.sh /absolute/resource /absolute/new-results
```

The builder copies `resourcetest.cpp` and `testhelpers.h` unchanged, records
source/output SHA256 and only redirects generated test-data paths to a runtime
reference directory. The runner uses the installed library and icons, checks
linkage, applies a timeout and runs the missing-reference negative case.
