# Plasma game controller SDL3 regression

This test compiles the patched Plasma Desktop 6.7.5 device implementation.
It uses Qt 6.12, KI18n 6.31, SDL3 3.4.18, and libudev.
It does not use SDL2 or an SDL2 compatibility library.
The test and compatibility patch were prepared with AI assistance.

Apply the Plasma Desktop recipe patches first.
Set `source` to its `kcms/gamecontroller` directory.
Build outside the source and Ports checkout.

For an AArch64 EmberBSD cross build, run:

```sh
sh build-cross.sh "$source" "$build" "$sysroot" "$toolchain" "$qt_host"
```

All five paths must be absolute. The toolchain contains
`bin/aarch64--netbsd-gcc` and `bin/aarch64--netbsd-g++`.
The sysroot must contain the common GCC16 runtime and target packages.
The Qt host prefix must contain the matching native `moc` and CMake files.
The runner defaults to two build jobs. Set `MAKE_JOBS` to override this.
It selects `/usr/pkg/gcc16/lib` before the base compiler runtime.
The output must require only the common `libstdc++` SONAME.

For a native build with those current dependencies, run:

```sh
cmake -S . -B "$build" -G Ninja -DGAMECONTROLLER_SOURCE="$source"
cmake --build "$build" --parallel 2
ctest --test-dir "$build" --output-on-failure
```

Install the common target packages before transferring a cross-built test.
Run as an ordinary user in an isolated test process:

```sh
LC_ALL=C.UTF-8 QT_LOGGING_RULES='kcm_gamecontroller.debug=false' \
    ./device-test -v1
```

The test creates and removes SDL virtual devices. It checks:

- Instance IDs, failed opens, and missing OS device paths.
- Button bounds, sparse button maps, new SDL3 buttons, and reopen counts.
- Gamepad types, axes, hats, and Qt property signals.
- Real SDL button, axis, and removal event dispatch.
- Virtual-device rejection and balanced SDL subsystem ownership.

The event-dispatch test admits a virtual fixture into the internal model.
The separate policy test confirms production still rejects virtual devices.
This does not prove physical controller hotplug, USB, Bluetooth, or the KCM UI.
Virtual-device support is required. Missing support fails the test.
Expected invalid-device and virtual-filter warnings are kept in the log.

The cross build uses the production `TRANSLATION_DOMAIN` definition.
The emitted `compile_commands.json` records the actual compilation parameters.
Run Cppcheck and Clang Static Analyzer with those target headers and definitions.
Do not treat a parser failure or a missing header as a clean analysis result.
Valgrind execution requires a supported platform. No Valgrind pass is implied.

For an independent UBSan run, select the current native Clang frontend.
Use a separate output directory. The cross linker and runtime remain GCC16.

```sh
EMBER_TEST_CLANG="$clang" EMBER_TEST_UBSAN=ON \
    sh build-cross.sh "$source" "$ubsan_build" "$sysroot" "$toolchain" "$qt_host"
```

`clang` is the absolute path to native `clang++` 23.1.3.
The toolchain selects its AArch64 EmberBSD target and the common GCC16 headers.
The test compiles with `-fsanitize=undefined -fsanitize-trap=undefined`.
Undefined behavior terminates the process through a trap; no sanitizer DSO is needed.
Run the output on EmberBSD with the same command as the ordinary test.
This covers the executable and inline code, not the uninstrumented Qt or SDL DSOs.
It does not detect all invalid memory accesses or leaks and is not a Valgrind result.
