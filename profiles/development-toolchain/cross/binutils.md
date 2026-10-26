# Common Binutils and host BFD

`build-binutils.py` builds the common `devel/binutils` 2.47 source and its
complete Ports patch set. It supports the application targets `aarch64` and
`amd64`, and the existing kernel-only `earmv7hf` target. The host libraries
and programs execute on the development host; the BFD target vector describes
the EmberBSD objects they read. No application sysroot or target runtime is needed.

Select the installed native Ports prefix explicitly. Clang is the default;
`--host-compiler-family gcc` selects the GCC alternative. Run the controller
with that prefix's Python. Tool paths, executable architecture, compiler
components and script interpreters use the shared SDK native-prefix API.
The controller sets a prefix-only `PATH` and selects its shell, GNU make,
archive tools and patch tool. Optional `HOST_CC`, `HOST_CXX` and `GMAKE`
aliases must agree with that selection.
The Ports-owned `binutils-native-tools` roster uses the shared SDK command
mapping publisher. Nested configure and make commands resolve names such as
`awk`, `make` and `tar` to the selected `nawk`, GNU make and `bsdtar` paths.
The mapping precedes the prefix-only PATH and does not modify the prefix.
Archive extraction selects the common libarchive `bsdtar` frontend explicitly:
the producer needs `--strip-components`, which the generic NetBSD `nbtar`
frontend does not provide.

```sh
EMBER_BINUTILS_ARCHIVE=/absolute/distfiles/binutils-2.47.tar.xz \
CROSS_JOBS=4 /absolute/native-prefix/bin/python3.15 -B \
  profiles/development-toolchain/cross/build-binutils.py \
  --sdk-source /absolute/EmberBSD-SDK --host-prefix /absolute/native-prefix \
  --target amd64 /absolute/binutils-amd64
```

The archive selector is optional; otherwise the existing producer downloads
the pinned source. SHA256, SHA512, size and recipe patch checks remain required.
The producer keeps its existing `src`, `build` and `prefix` directories.
Use a new output directory and keep the whole result unchanged while consumers
use it. Native dependency headers, libraries and pkg-config metadata come from
the selected prefix. Install common native zlib headers and libraries there;
`--with-system-zlib` excludes the bundled copy. Optional zstd support remains
available; the producer does not disable compression to simplify linking.

The enclosing explicit GCC cross-compiler and firmware producers retain their
existing host selection, GNU make argument and output contract. They call the
same Binutils producer and source preparation, without requiring the new BFD
output. There is no second recipe.

## Native OS helper inputs

For the explicitly selected native-prefix route, after build and installation,
`host-bfd.mk` supplies ordinary make variables
for native OS `dbsym` and `mdsetimage` consumers:

| Variable suffix, under `EMBER_HOST_BFD_` | Meaning |
| --- | --- |
| `TRIPLET` | The selected BFD target triplet |
| `SOURCE`, `BUILD` | The prepared common source and matching native object directory |
| `CPPFLAGS` | The generated `bfd.h` and common Binutils ELF interface headers |
| `LDADD` | The actual static BFD link inputs and transitive dependency flags |
| `DPADD` | The static archives used by those link inputs |

The producer checks the generated header version and the configured source
and target. It executes the installed target-prefixed `objdump -i` and requires
the selected ELF vector. Libtool metadata is read as data, never sourced as
shell code. Nested `.la` dependencies become their actual static archives;
zlib, zstd, dl, framework and runtime-path flags are preserved. `libsframe`
is required only when the actual BFD dependencies use it. Missing inputs,
mixed source/target paths, unsupported arguments and cyclic dependencies fail
before the make input is written. `host-bfd.mk` is build configuration, not a
toolset qualification or an independent admission receipt.

An OS adapter must consume the common source and libraries together and remove
its old local Binutils provider from that external-toolchain graph. Merely
overriding `BFDDIR` leaves the old private ELF headers in the include path.
The native OS helper sources and their behavior remain owned by the OS.
The producer does not establish an OS build or target execution result.

## Checks

```sh
python3 -B profiles/development-toolchain/cross/tests/binutils-host.py \
  --sdk-source /absolute/EmberBSD-SDK -v
python3 -B profiles/development-toolchain/cross/tests/firmware-host.py \
  --sdk-source /absolute/EmberBSD-SDK
```

These synthetic checks run the real controller with intercepted build commands,
check Clang/GCC selection, existing caller behavior and generated BFD inputs,
and exercise dependency and mismatch refusals. They do not compile Binutils
or prove that the OS helpers link. Run those builds with the selected native
prefix before claiming native execution support.
