# Open CASCADE 8 for KiCad

This probe prepares OCCT 8.0.1 for EmberBSD AArch64 and the common GCC16 toolchain.
OCCT 8.0.1 is the current stable upstream release, checked on 2026-10-18.
The official release date is 2026-07-30.
`source.json` records the upstream archive, commit, SHA256, and patch hashes.
Source preparation and focused contracts do not establish a complete target package.

The patches retain upstream copyright and the LGPL-2.1 OCCT exception.
New test and preparation files use BSD-2-Clause.
The patches are AI-assisted EmberBSD work. They have not been submitted upstream.

## Runtime changes

- Use NetBSD's `newlocale` and explicit `*_l` conversion functions.
  Do not assume that `_GNU_SOURCE` implies an available `uselocale` API.
- Recognize NetBSD paths as Unix paths and initialize the path object's UNC flag.
- Link the base `libexecinfo` and select dynamic-loader libraries through CMake.
- Regenerate package scripts without reading an existing installation.
  Keep Linux allocator headers conditional.
- Bound exception trace buffer arithmetic before multiplying the frame count.
- Validate stack-trace buffer termination and frame-count arithmetic.
  Reject an exhausted frame skip before calling `backtrace_symbols`.
  Allocate caller-sized frame storage on the heap and free it on every return path.

NetBSD's explicit locale conversion functions do not change the process locale.
The separate `Standard_CLocaleSentry` retains upstream's process-global fallback on NetBSD.
It does not gain a thread-local locale API from this patch.
The build recipe keeps release range and exception checks enabled.
It does not define `No_Exception`.

## Prepare and build

Use a verified download of the URL recorded in `source.json`:

```sh
ruby probes/kicad/occt/prepare.rb /absolute/OCCT-V8.0.1.tar.gz /absolute/new-source

sh probes/kicad/occt/build.sh cross-full /absolute/new-source \
    /absolute/new-build /absolute/new-stage /usr/pkg /absolute/aarch64-gcc16.cmake
```

Supply a coherent EmberBSD sysroot through the CMake toolchain file.
Use the common GCC16 compiler and runtime.
The script requires GCC16 in every mode and checks the cross target identity.
It keeps FreeType, Eigen, RapidJSON, Xlib, OpenGL, FreeImage and Draw enabled.
Prepare those common dependencies first.
The full modes require the common Tcl/Tk dependency for Draw.
Each build and stage path must be new. Logs remain in the build directory.
`JOBS` defaults to one and accepts one or two jobs.

`native-core` builds the Foundation Classes module for focused host diagnostics.
It is not a substitute for the complete KiCad dependency.
`native-full` builds the same library modules as `cross-full` with a native compiler.
Both native modes omit the final toolchain argument.
The prefix remains an explicit argument in every mode.
The earlier restored native core used GCC 14.2.0. New builds require GCC16.

## Checks

The core consumers use the installed CMake package:

```sh
cmake -S probes/kicad/occt/tests -B /absolute/new-consumer \
    -DCMAKE_PREFIX_PATH=/absolute/installed-prefix
cmake --build /absolute/new-consumer
/absolute/new-consumer/occt-core C
/absolute/new-consumer/occt-core de_DE.UTF-8
```

Use an installed non-C locale for the second check.
The core check verifies C-locale conversion, process-locale restoration, path round trips,
`Standard_Failure::what()`, and a range exception that disappears with `No_Exception`.
Add the GCC16 toolchain file when cross-compiling these consumers.
Execute target binaries only in an EmberBSD acceptance guest or on a target board.

The causal stack-trace test compiles the actual upstream C++ module twice:

```sh
ruby probes/kicad/occt/tests/check-stacktrace.rb \
    /absolute/original-source /absolute/patched-source \
    /absolute/configured-build/include/opencascade /absolute/new-regression
```

This test needs a native compiler with AddressSanitizer and UndefinedBehaviorSanitizer.
It checks five failures before the patch and six successful cases after the patch.
The standalone module also passes all six cases under strict native Memcheck.
See [analysis.md](analysis.md) for the exact validation boundary.

The application [source preparation](../application/README.md) applies
`../application/patches/occt8-api.patch` to KiCad 10.0.7.
It replaces 12 deprecated `GetMessageString()` calls with `what()`.
KiCad 10.0.7 contains no `Standard_Failure::Raise` call to replace.
The core consumer uses OCCT8's ordinary C++ `throw` and `what()` API.

Full target compilation, installed STEP geometry, and the KiCad interface remain acceptance work.
The fixture's independent STEP reader checks solid and shell closure, volume, bounds, and meshing.
Its successful source review is not a runtime result.

The additional actual-source tests use GCC16 and the installed native helper library:

```sh
ruby probes/kicad/occt/tests/check-failure-stack.rb \
    /absolute/original-source /absolute/patched-source \
    /absolute/generated-headers /absolute/native-prefix /absolute/new-check
ruby probes/kicad/occt/tests/check-install.rb \
    /absolute/original-source /absolute/patched-source /absolute/new-install-check
```

The exception test rebuilds the actual `Standard_Failure` module. It records
its helper DSO hash and does not claim that the helper library was rebuilt.
The installation test executes actual upstream CMake fragments and macros.
See the [canonical package audit](pkgsrc-audit.md) for retained and retired
pkgsrc fixes, dependency requirements and the static packing-list boundary.
