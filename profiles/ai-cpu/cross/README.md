# GCC16 cross build of llama.cpp

Build the CPU executables on Linux. Install and run the package on EmberBSD
AArch64. The native recipe and cross build share the feature caches in
`pkgsrc/local-ai/cpu.cmake` and `pkgsrc/local-ai/llama-cpp/package.cmake`.
The cross build adds upstream test executables. It retains the target ABI
name `aarch64--netbsd` and the kernel's `NetBSD` identity.

## Inputs

Use GCC and G++ 16.2.0 from the
[host cross compiler profile](../../development-toolchain/cross/README.md).
Prepare a sysroot from one recorded EmberBSD source revision. It must contain
the target headers, base libraries, loader, GCC16 C++ headers, start files,
`libstdc++.so.7` and `libgcc_s.so.1`. Do not mix a NetBSD release sysroot with
EmberBSD. The compiler prefix has `bin/aarch64--netbsd-{gcc,g++,readelf}`.

The host needs POSIX shell, CMake, Ninja, patch, tar, sha256sum and sha1sum.
Use absolute paths without spaces or shell metacharacters. The output path
must not exist. The source archive and recipe patches are checked before build.
All five installed programs use `armv8-a` and the GCC16 runtime path.

```sh
curl --fail --location --output /var/tmp/llama.cpp-0.6.0.tar.gz \
  https://github.com/ggml-org/llama.cpp/archive/8345f333951c661d166b00e6f9362e553768f292.tar.gz
sh profiles/ai-cpu/cross/build-llama.sh \
  /var/tmp/ember-cross /var/tmp/ember-sysroot \
  /var/tmp/llama.cpp-0.6.0.tar.gz /var/tmp/llama-cross
```

`CROSS_JOBS` sets the build parallelism; the default is four jobs. The output
contains `stage/usr/pkg`, `build/bin/test-*`, logs, a compilation database,
the generated toolchain file and ELF dependency checks. Only native `PLIST`
files enter the staging tree. The helper uses mode 755 for executables and
ordinary readable data. It rejects host paths in ELF runtime dependencies.

## Target package and acceptance

Transfer the staging tree and the canonical `llama-cpp` recipe to the target.
Use the fork's `pkg_create`, `pkg_add`, `pkg_info` and `pkg_admin`. The target
must already provide the matching GCC16 runtime libraries. Create a build
information file for the actual target. Repeat `REQUIRES` for each library;
do not register an invented compiler package.

For the validated EmberBSD 11 AArch64 sysroot:

```text
OPSYS=NetBSD
OS_VERSION=11.0
MACHINE_ARCH=aarch64
PKGTOOLS_VERSION=20260227
PKGPATH=local-ai/llama-cpp
CC_VERSION=gcc-16.2.0
CXX_VERSION=gcc-16.2.0
REQUIRES=/usr/pkg/gcc16/lib/libstdc++.so.7
REQUIRES=/usr/pkg/gcc16/lib/libgcc_s.so.1
REQUIRES=/usr/lib/libc.so.12
REQUIRES=/usr/lib/libm.so.0
REQUIRES=/usr/lib/libpthread.so.1
BUILD_OPTIONS=cpu armv8-a private-ggml
```

On the target, create the package with the actual staging prefix and the
recorded `/usr/pkg` installation prefix:

```sh
sh package-llama.sh /stage/usr/pkg /recipes/llama-cpp \
  /packages/llama-cpp-0.6.0nb1.tgz /recipes/build-info.txt
```

Fetch the small model with the
[model example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/ai/local-inference).
Select `smollm2-135m`; its manifest checks the immutable revision and SHA256.
Copy the resulting GGUF file to the target. Run as an administrator in a
disposable test system with no installed `llama-cpp` and free loopback port 18080:

```sh
sh run-llama-tests.sh /packages/llama-cpp-0.6.0nb1.tgz \
  /models/SmolLM2-135M-Instruct-Q4_K_M.gguf /results/llama
```

This check installs the package, checks integrity and GCC16 linkage, generates
24 tokens, rejects an invalid GGUF, removes and reinstalls the package, and
requests 16 tokens from its own loopback server. It leaves the package
installed. It stops its server and saves the responses and timing data.

Run the selected upstream tests from `build/bin` separately on the target:
`test-sampling`, `test-grammar-parser`, `test-grammar-integration`,
`test-json-schema-to-grammar` and `test-gguf`. The host also builds
`test-quantize-fns`; its Memcheck run belongs on a supported host platform.
Use [the allocator regression](../tests/check-ggml-alloc-oom.sh) on a native
configured build to compare the unpatched and patched source with `NDEBUG`.

This is a bounded cross delivery path. It does not cross-build the full
pkgsrc dependency graph or an installable Canadian-cross GCC package. Normal
pkgsrc compiler dependency resolution remains in the native recipe. The
[validation record](validation.md) identifies the accepted build and limits.
