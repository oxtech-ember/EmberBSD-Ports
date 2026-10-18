# GCC16 atomic runtime component

This recipe supplies missing `libatomic` files in an incomplete GCC16 cross
SDK. It uses the same GCC 16.2.0 archive as the common compiler. It builds no
compiler frontend and introduces no alternate compiler or runtime version.

Full `gcc16` and `gcc16-libs` packages already provide this component. The
component package conflicts with both. Native PCL recipes must use the normal
GCC16 runtime provider instead of requiring this component unconditionally.

Use the [cross helper](../../../profiles/development-toolchain/cross/build-libatomic.py):

```sh
CROSS_JOBS=2 python3 -B profiles/development-toolchain/cross/build-libatomic.py \
    /absolute/gcc16-prefix /absolute/emberbsd-sysroot \
    /absolute/gcc-16.2.0.tar.xz /absolute/new-output
```

The helper verifies the archive before extraction. It retains source, configure,
build, install and ELF records under the new output. It stages the shared and
static library under `stage/usr/pkg/gcc16/lib`, with original license texts.
It does not change the input sysroot. GCC's bundled Libtool requires `-Wc`
options to preserve the explicit sysroot and startup paths during linking.
The real linker trace records the selected inputs.

The NetBSD target retains upstream's `libatomic.so.3` SONAME and POSIX pthread
fallback. The helper cross-builds the shared-library consumer from
[the generic atomic contract](../../../profiles/development-toolchain/tests/libatomic.cpp).
Run `atomic-contract` after installing the component package on EmberBSD. It
checks 256-byte load, store, exchange and compare/exchange operations, then
verifies 2,000 concurrent updates across all 64 integer fields.

Cross compilation is separate from target execution. The PCL profile records
package lifecycle and runtime acceptance. A native pkgsrc package build and
the full upstream DejaGNU suite require separate evidence.
