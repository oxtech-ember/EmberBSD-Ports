# System uthash checks

The recipe selects the common uthash package.
Two patches make the system selection strict and export the detected include directory.
Neither patch changes the C sources or the XIM API.

Prepare unmodified xcb-imdkit 1.0.9, a separate patched copy, and uthash 2.4.0.
Run the configuration regression with the same CMake toolchain and dependency options as the package:

```sh
sh tests/check-system-uthash.sh \
    /path/to/xcb-imdkit-upstream \
    /path/to/xcb-imdkit-patched \
    /path/to/uthash-source \
    /path/to/new-work-dir \
    -DCMAKE_TOOLCHAIN_FILE=/path/to/toolchain.cmake \
    -DECM_DIR=/path/to/native/share/ECM/cmake
```

Set the package's pkg-config environment before a cross run.
The work directory must not exist.
The script exercises the real project and `FindUTHash.cmake` files.
It proves that the original project permits the old bundled fallback.
It then verifies that the patched project rejects a disabled system package.
A separate import check verifies the exact include-directory property before and after the patch.

Run `bmake test` in a native package build to execute upstream `test_encoding`.
For a cross build, execute that binary on EmberBSD with the built package installed.
The configuration check and successful linking do not prove an X11 or Wayland input session.
