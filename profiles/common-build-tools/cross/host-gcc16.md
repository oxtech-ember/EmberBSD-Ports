# Native GCC16 for standalone host helpers

Cross builds also compile programs that run on the build host: generators,
configuration probes and native helper tools. Build them with the native
GCC 16 for the build host. Do not use Clang, `/usr/bin/cc`, Xcode, Command
Line Tools, Homebrew or MacPorts compilers for these programs.
On macOS, build that compiler from the Ports `lang/gcc16` recipe.

The cross profile and the native LLVM controller take their native drivers
from the qualified SDK toolset. See [native-toolset.md](native-toolset.md).
This file covers only standalone helpers that the SDK toolset does not
select yet.

## Standalone helpers

These helpers and source checks require `HOST_CC`, and where C++ is used
`HOST_CXX`, as absolute native GCC16 drivers. There is no default.

- [build-wayland-scanner.sh](../../common-graphics/cross/build-wayland-scanner.sh)
- [build-ffmpeg-cpu.sh](../../common-media/cross/build-ffmpeg-cpu.sh) native mode
- [build-x265.sh](../../common-media/rtp/build-x265.sh) native mode
- [gdb cross-build.sh](../../development-toolchain/gdb/cross-build.sh)
- the `host-cmake.sh`, `host-msgfmt.sh`, `llvm-package-split.py` and
  graphics cross source checks

Shell helpers source [host-gcc16.sh](host-gcc16.sh). It refuses a missing
or relative selection, system and package-manager locations, a `__clang__`
macro set, a version banner naming Clang, LLVM or Apple, and any `__GNUC__`
other than 16. Use the drivers that the qualified SDK toolset records.

On Darwin, the native GCC 16 driver uses the host SDK assembler and linker.
These are not compilers; the selection does not replace them.

## Regression check

Run [tests/host-gcc16.sh](../tests/host-gcc16.sh) with a new work directory.
It uses driver doubles and needs no compiler.
