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
- Find the genuine Unix shared Tk 9 library paired with the selected Tcl version.
  Tcl/Tk 9.1 uses `libtcl9tk9.1.so`; CMake's older `tk9.1` search misses it.
  Refuse a missing paired library instead of silently disabling requested Tk.

NetBSD's explicit locale conversion functions do not change the process locale.
The separate `Standard_CLocaleSentry` retains upstream's process-global fallback on NetBSD.
It does not gain a thread-local locale API from this patch.
The build recipe keeps release range and exception checks enabled.
It does not define `No_Exception`.

## Prepare and build

Use a verified download of the URL recorded in `source.json`:

```sh
python3.15 probes/kicad/occt/prepare.py --sdk-source /absolute/EmberBSD-SDK \
    /absolute/OCCT-V8.0.1.tar.gz /absolute/new-source

sh probes/kicad/occt/build.sh cross-full /absolute/new-source \
    /absolute/new-build /absolute/new-stage /usr/pkg /absolute/aarch64-gcc16.cmake
```

Supply a coherent EmberBSD sysroot through the CMake toolchain file.
Source preparation requires the native Python 3.15 interpreter and a clean,
fully materialized SDK checkout providing host API 1. It records the selected
SDK commit, interpreter, helper hash, and every extraction/patch status.
Archive and patch hashes are checked before creating the new source directory.
Failed commands retain their logs and partial source for inspection.
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

The [canonical recipe candidate](recipe/README.md) retains the normal `cad/occt`
provider and full default Draw/X11 features. It is a source checkpoint without
a packing list or common-export registration. Complete installed-stage inventory,
ordinary package checks and target STEP acceptance are still required.

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

## Tcl/Tk 9.1 source compatibility

Six actual Draw translation units that call Tcl pass GCC16.2 C++17 syntax checks
with the genuine Tcl/Tk 9.1 headers and installed native X11 headers. This includes
`Draw_Main`, `Draw_Interpretor`, `Draw`, `Draw_VariableCommands`, `Draw_Window`
and `ViewerTest_ViewerCommands`. The last retains an upstream unused-variable
warning; no diagnostic is suppressed. OCCT already calls `Tcl_FindExecutable`
before creating its interpreter. Tcl 9.1 retains the `int argc` callback used by
`Tcl_CreateCommand`, so no callback cast or C++ API adaptation is needed here.
These are native header-compatibility checks, not linked Draw or target execution.

The discovery contract runs the real OCCT CMake modules and real Tcl provider:

```sh
cmake -S probes/kicad/occt/tests/tk-discovery -B /absolute/new-discovery \
    -DOCCT_SOURCE=/absolute/patched-source -DTCL_PREFIX=/absolute/tcl-prefix \
    -DTK_PREFIX=/absolute/tk-prefix
```

With an empty Tk prefix containing `include` and `lib`, original OCCT succeeds
and silently turns Tk off (`-DEXPECT_MISSING=ON` records that baseline).
The patched module fails with the matching-library diagnostic. This negative
case passed with CMake 4.4.4 and installed Tcl 9.1. Positive discovery and linking
await a genuine Tk 9.1 stage. The patch changes Unix shared automatic discovery;
explicit user library overrides and static/Windows paths retain upstream behavior.
