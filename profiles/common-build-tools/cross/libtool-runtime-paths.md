# Cross Libtool runtime paths

The ordinary pkgsrc C wrappers retain SDK compiler-runtime paths for headers
and link-time libraries. Installed ELF files must use the corresponding target
runtime paths. Libtool metadata must also refer to installed target paths.

The [buildlink patch](../patches/pkgsrc-cross-passthrough-rpath.patch) converts
only explicitly permitted directories below `CROSS_DESTDIR`. It preserves
native builds, unrelated paths and the compiler's `I`, `L` and `P` mappings.
The directory boundary excludes a sibling such as `/sdk-other` for `/sdk`.
An empty sysroot or `/` does not trigger conversion. The existing shell-wrapper
path remains unchanged; this repair covers the normal C wrapper implementation.

The common framework requires `cwrappers>=20220403nb1`. Its archive-path
boundary repair also preserves sibling directories during `.la` unwrapping.
An older installed wrapper is not an accepted provider for this mapping.

Run the [regression](../tests/cross-passthrough-rpath.rb) with prepared native
and cross configurations. Both need their real pkgsrc host tools. The cross
configuration requires the complete AArch64 GCC16 runtime in its SDK.

```sh
BMAKE=/absolute/host/bin/bmake ruby \
  profiles/common-build-tools/tests/cross-passthrough-rpath.rb \
  /absolute/prepared-pkgsrc /absolute/cross.mk.conf \
  /absolute/native.mk.conf /absolute/new-check-directory
```

The check copies only framework and consumer recipe files. It generates real
pkgsrc wrappers in private directories and uses GCC16.2.0 to compile a C++
vector consumer. Ordinary Libtool links and installs its shared library.
The baseline ELF reproduces the private SDK RPATH. The repaired ELF retains
`libstdc++.so.7`, `libgomp.so.1` and only the target runtime paths.
Installed `.la` metadata uses `/usr/pkg/gcc16/lib`. Native and prefix-sibling
mapping checks preserve their previous behavior. Inputs and commands have hashes
and receipts. This check does not install packages or execute target code.

The ngspice 47 shared package exposed this defect during independent installed
ELF inspection. Ordinary pkgsrc stage checks did not reject the SDK path.
Package and application acceptance must therefore inspect actual ELF RPATH
and installed metadata, in addition to the standard package checks.
