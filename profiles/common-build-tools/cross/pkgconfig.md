# Target pkg-config paths

With the GCC16 override, CMake also searches the selected SDK's
`usr/pkg/gcc16/lib` before the base
C++ runtime. `FindPkgConfig` converts explicit `-lstdc++` entries into absolute
library paths; the compiler's `-B` runtime selection cannot change such a path.
The common target-only `CMAKE_LIBRARY_PATH` setting keeps these imported targets
on the installed GCC16 ABI. With the Clang default, `CMAKE_LIBRARY_PATH` lists
the target runtime library paths instead. It does not alter native CMake discovery.

The common cross profile supplies `PKG_CONFIG_SYSROOT_DIR` in both configure
and build environments. The value is the selected `CROSS_DESTDIR`.
The ordinary pkgsrc wrapper still restricts discovery to buildlink metadata.
Native tool builds do not acquire this setting.

Target `.pc` files contain their installed `/usr/pkg` prefix. Without the
sysroot setting, CMake's `PkgConfig::` imported targets receive host paths
such as `/usr/pkg/include`. CMake rejects the missing include directory.
pkg-config's sysroot support maps compile and link search paths to the SDK;
the installed runtime search paths remain `/usr/pkg/lib`.

Run the regression after ordinary OpenEXR configure has prepared real native
and target tool wrappers and buildlink trees. The configuration file must
include the common cross profile directly, exactly once.

```sh
ruby profiles/common-build-tools/tests/pkgconfig-sysroot.rb \
    /absolute/exported-pkgsrc /absolute/cross.mk.conf \
    /absolute/target-objects /absolute/native-objects /absolute/new-results
```

The check queries actual pkgsrc configure/build metadata. It reproduces the
unrooted CMake import failure, then builds and stages a zstd DSO and executable
with GCC16. It verifies AArch64 ELF linkage, the real installed zstd provider
and an explicit target runtime-path allowlist. Native metadata and provider
selection must remain identical. It writes no package database or SDK files.
This check establishes target linkage; it does not execute target binaries.

After ordinary FreeImage configure has prepared its real native and target
wrappers, check explicit C++ provider selection with installed LibRaw 0.22.2:

```sh
BMAKE=/absolute/native-bmake \
  ruby profiles/common-build-tools/tests/pkgconfig-cxx-runtime.rb \
    /absolute/exported-pkgsrc /absolute/cross.mk.conf \
    /absolute/target-objects /absolute/native-objects /absolute/new-results
```

The AArch64 regression observes the original `libstdc++.so.9` and `.7` link,
then requires only the installed GCC16 `libstdc++.so.7`. It checks real CMake
imported paths, unchanged provider hashes and target runtime paths. Both native
variants execute and retain identical discovery metadata. This is a compiler
and link contract; target execution and complete FreeImage acceptance are separate.
