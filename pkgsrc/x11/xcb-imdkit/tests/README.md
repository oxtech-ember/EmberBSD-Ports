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

## Relocatable CMake package

The 1.0.9nb1 recipe exports `${CMAKE_INSTALL_INCLUDEDIR}` through `INSTALL_INTERFACE`.
Upstream 1.0.9 used the absolute `CMAKE_INSTALL_FULL_INCLUDEDIR` value.
That export made Fcitx5 search the build host's `/usr/pkg/include` during a cross build.
The relative path follows [CMake's install-interface contract](https://cmake.org/cmake/help/latest/command/target_include_directories.html#creating-relocatable-packages).
It preserves the header layout, X11 dependencies, C API and library ABI.

Prepare the original archive and a separate copy with all recipe patches applied.
Use the package's dependency environment and CMake toolchain options:

```sh
sh tests/check-relocation.sh \
    /path/to/xcb-imdkit-upstream \
    /path/to/xcb-imdkit-patched \
    /path/to/new-relocation-results \
    -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE=/path/to/toolchain.cmake \
    -DECM_DIR=/path/to/native/share/ECM/cmake \
    -DUSE_SYSTEM_UTHASH=ON \
    -DUTHash_INCLUDE_DIR=/path/to/sysroot/usr/pkg/include \
    -DCMAKE_INSTALL_RPATH=/usr/pkg/lib
```

The regression configures and builds both complete upstream projects, including their test targets.
It installs each project into a private `DESTDIR`, then moves the installed prefix.
The original prefix remains absent. The original exported target must fail CMake generation with that missing include path.
The patched target must use the moved prefix and link a consumer of the installed public headers and library.
The checker does not edit the exported target or add include-directory workarounds to the consumer.

GCC 16.2 and CMake 4.4.4 passed this cross regression for EmberBSD/AArch64.
The installed original and patched shared libraries were byte-identical; only the package metadata changed.
Target binaries are not executed by this test. Normal package checks, upstream target tests and an input session remain separate gates.
The new CMake patch and regression are AI-assisted EmberBSD changes; they have not been accepted upstream.
