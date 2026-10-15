# Local AI CPU packages

This profile provides **llama.cpp 0.6.0nb1** and **whisper.cpp 1.9.5**
execution tools through ordinary pkgsrc recipes. Models are separate assets.

The [GCC16 cross profile](cross/README.md) builds llama.cpp on Linux for an
EmberBSD AArch64 sysroot. Target installation, removal, reinstallation, text
generation and loopback HTTP completion passed on 2026-10-14 in QEMU TCG.
The package checks two GGML metadata allocations before dereference.
See the [validation record](cross/validation.md) for source hashes, tests,
memory checks and the exact VM boundary.

The [Whisper cross path](cross/whisper.md) uses GCC16 and whisper.cpp 1.9.5.
Its [2026-10-15 validation](cross/whisper-validation.md) covers an installed
tiny-model transcription, parsed JSON timestamps, output failures and the
package removal/reinstallation cycle in EmberBSD AArch64 QEMU. It includes
fixed-header, allocator and CLI memory regressions.

Historical native validation of llama.cpp 0.6.0 and whisper.cpp 1.9.4 on 2026-10-06: EmberBSD/NetBSD 11.0, AArch64, UTM VM, 4 virtual CPUs,
4 GiB guest RAM, GCC 12.5.0, CMake 4.3.3, Ninja 1.13.2. Both packages were
built, installed together, exercised with real models, removed, reinstalled,
and checked with `pkg_admin`. Those historical releases required no upstream source patches.

| Package | Executables |
| --- | --- |
| `llama-cpp-0.6.0nb1` | `llama-cli`, `llama-completion`, `llama-server`, `llama-bench`, `llama-quantize` |
| `whisper-cpp-1.9.5` | `whisper-cli`, `whisper-bench`, `whisper-quantize` |

The initial recipes intentionally install execution tools, not a public C/C++
development ABI. Each executable contains its engine's bundled GGML. They do
not install competing `libggml` files. On the tested system, runtime linkage
requires libc, libm, libpthread, libstdc++, and libgcc_s. The GCC16 build uses
`/usr/pkg/gcc16/lib/libstdc++.so.7` and `libgcc_s.so.1` from the matching toolchain.

Both current engines report bundled GGML 0.26.0, with identical public GGML
headers. The executable-only recipes retain their private static engine
archives. A shared development ABI and common shared GGML provider have not
been validated. No parallel shared GGML libraries enter the installation.

## Build with pkgsrc

Build natively on the target OS/architecture. Install the C/C++ toolchain,
Git, CMake, Ninja, and pkg_tools first. Git is needed to prepare the source
tree; curl is needed for the separate model example. Both recipes require GCC 16.2.
Use the [development toolchain profile](../development-toolchain/README.md)
to prepare that compiler. pkgsrc resolves other
build dependencies normally and may request administrator access to install
them. Keep enough disk space for the full pkgsrc checkout and working copy.

```sh
git clone --recurse-submodules --shallow-submodules \
  https://github.com/oxtech-ember/EmberBSD-Ports.git
cd EmberBSD-Ports
work=/var/tmp/emberbsd-ai-build
mkdir "$work"
sh scripts/prepare-pkgsrc.sh "$work/pkgsrc" development-toolchain
mkdir "$work/work" "$work/distfiles" "$work/packages"
cat > "$work/mk.conf" <<EOF
.if defined(BSD_PKG_MK)
WRKOBJDIR= $work/work
DISTDIR= $work/distfiles
PACKAGES= $work/packages
MAKE_JOBS= 2
CMAKE_GENERATOR= ninja
.endif
EOF
make -C "$work/pkgsrc/local-ai/llama-cpp" MAKECONF="$work/mk.conf" package
make -C "$work/pkgsrc/local-ai/whisper-cpp" MAKECONF="$work/mk.conf" package
```

Use an absolute, unused work directory without whitespace. Keep paths in
`mk.conf`: command-line-only settings can be lost when pkgsrc invokes `su` for
dependency installation. The helper refuses an existing destination or a
submodule revision that differs from the recorded Git link. It exports the
pinned upstream tree and adds every local category, including `local-ai/`; it does not resolve dependencies,
download application sources, or maintain an installed-package database.

The pkgsrc pin is `fff4deb639a1a640476203c80f752fb77b6cb14b` on
`pkgsrc-2026Q3`. Its unrelated `databases/py-whisper` package is not whisper.cpp.
The two new recipes are absent from this pinned upstream tree.

## Install and remove

For an isolated test installation, use a separate prefix and package database:

```sh
mkdir "$work/runtime" "$work/pkgdb"
pkg_add -K "$work/pkgdb" -p "$work/runtime" \
  "$work/packages/All/llama-cpp-0.6.0nb1.tgz" \
  "$work/packages/All/whisper-cpp-1.9.5.tgz"
pkg_admin -K "$work/pkgdb" check llama-cpp whisper-cpp
```

Use `$work/runtime/bin` as `AI_BIN` in the
[independent model example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/ai/local-inference).
Remove this installation with:

```sh
pkg_delete -K "$work/pkgdb" llama-cpp-0.6.0nb1 whisper-cpp-1.9.5
```

For a normal system installation, an administrator uses `pkg_add` without
the isolated prefix/database flags. The package installs under `/usr/pkg`.
No service starts automatically. Binary packages must match the target OS
and architecture. This profile does not configure a pkgin repository or
establish a signed binary release channel.

## Source and build policy

- llama.cpp revision: `8345f333951c661d166b00e6f9362e553768f292`.
- This retained 0.6.0 snapshot is one commit after the stable `v0.6.0` tag
  (`d81235049384534c167caea52b85a694f6103d14`). The additional commit changes
  the disabled Hexagon backend; this CPU profile keeps its existing installation.
- whisper.cpp revision: `d1be6fde11ac6e0407606b4e42fe72d34add8037`.
- Upstream GitHub archives are checked by pkgsrc `distinfo`; SHA256 and source
  identity are also recorded in each package's installed `SOURCE` file.
- `GGML_NATIVE=OFF`; AArch64 targets `armv8-a`. OpenMP, GPU backends, external
  BLAS, KleidiAI, and runtime backend loading are disabled in this baseline.
- llama's UI build/download, HTTPS support, and subprocess features are
  disabled. The demonstrated HTTP service binds to loopback.
- whisper's model download, FFmpeg, SDL2, Core ML, and OpenVINO options are
  disabled. The example uses a local 16-bit, 16 kHz mono WAV fixture.
- These build targets required no Python or JavaScript build step. Upstream
  conversion scripts and optional features can have different dependencies.
- Engine and bundled component notices are installed under
  `share/licenses/{llama-cpp,whisper-cpp}/`.

## Validation boundary

With two inference threads, SmolLM2-135M-Instruct Q4_K_M generated text and
served a loopback completion; multilingual Whisper tiny transcribed the
upstream JFK sample. Both executables ran from an isolated pkg_tools install.
See the example for exact asset identities, commands, and observed timings.

This establishes CPU execution in the specified VM. Physical ARM64 boards,
RISC-V, GPU/NPU acceleration, microphone capture, image analysis, speech
synthesis, and a C+Lua agent have not been validated by this profile.
The VM's network remained available; the inference commands used local model
files and a loopback HTTP connection. A physical disconnected-device trial
is a separate acceptance step.

The [local-document example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/ai/local-knowledge)
extends this same installed engine with SQLite FTS5 retrieval and a model-selected
verbatim quotation. On 2026-10-07 the AArch64 VM produced an actual grounded
answer using one CPU thread. The application rejects missing evidence, forged
source IDs and quotes absent from retrieved documents. This is extractive QA,
not a general quality benchmark or a separate engine package.
