# Plasma Desktop XKB path regression

This test runs the XKB lookup from Plasma Desktop 6.7.5's
`ConfigureChecks.cmake`. It applies the shipped Ports patch to a fresh copy.
It uses real CMake `FindPkgConfig` and pkgconf. It also generates the actual
`config-workspace.h` template and checks its runtime `XKBDIR` value.

The original configure logic prepends `CMAKE_SYSROOT` to `xkb_base`.
Current pkgconf can already prefix this absolute variable with its sysroot.
This creates a double prefix and stops the cross build. The value is also
compiled into the keyboard preview, so it must exclude the host sysroot.

Run the test with unmodified upstream `ConfigureChecks.cmake` and
`config-workspace.h.cmake` files. Use an absolute, new output directory.
Use pkgconf with `PKG_CONFIG_SYSROOT_DIR` variable prefixing enabled.

```sh
CMAKE=/absolute/native/cmake PKG_CONFIG=/absolute/native/pkgconf \
    sh probes/plasma-mobile/toolkit/tests/plasma-xkb-paths.sh \
    /absolute/plasma-desktop-6.7.5 /absolute/new-results
```

The 14 cases reproduce the original failure and verify native, plain cross,
already prefixed cross, normalized sysroot and root-directory lookups.
Negative cases reject missing target data, host fallback, a matching sibling
path prefix, an empty cross sysroot, relative paths and regular files.
A generated header must contain the target path for every successful lookup.
The directory check does not validate the contents of the keyboard database.

The patch retains the upstream CMake 3.16 API floor. This regression was run
with CMake 4.4.4 and pkgconf 3.0.7 on a macOS development host.
It does not compile or execute the keyboard preview. Full packaging and target
keyboard behavior require separate acceptance. No C/C++ source is changed;
Cppcheck, compiler path analysis and Valgrind do not analyze this CMake logic.

Origin: EmberBSD (AI-assisted). This patch has not been submitted upstream.
