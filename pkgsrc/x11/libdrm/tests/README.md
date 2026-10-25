# AMDGPU ASIC-ID parser regression

libdrm 2.4.134 passes a plain `char` to `isblank`. NetBSD's ctype declarations
make GCC16 reject this call under `-Werror=char-subscripts`. The recipe passes
an `unsigned char` value and preserves the parser's whitespace behavior.

Run the source regression with native GCC16 on a supported NetBSD host:

```sh
python3 -B tests/amdgpu-asic-id-ctype.py \
    --archive /absolute/libdrm-2.4.134.tar.xz \
    --cc /absolute/path/to/gcc16 \
    --patch-tool /absolute/path/to/patch \
    --work /absolute/private/diagnostics/libdrm-amdgpu-ctype
```

The check verifies the distfile and patch checksums, applies the recipe patch
with zero fuzz, and extracts the real `parse_one_line` function from the pinned
upstream source. GCC16 must target NetBSD in both native and cross modes, so
the upstream control uses NetBSD ctype headers. The upstream control must fail
compilation for `char-subscripts`. The patched function must compile and pass
four cases for space/tab trimming, a high-bit name byte, vertical-tab
preservation, and an empty name containing only spaces and tabs. A second
actual-source fixture forces `strdup` to fail inside
`amdgpu_parse_asic_ids()`. The upstream control must fail because it passes the
NULL path to `fopen`. The patched function must log the allocation error,
skip `fopen`, release the NULL path safely, and retain the existing fusion
fallback through `/proc/cpuinfo`. The OOM fixture also checks that the
non-fusion path does not call that fallback. Neither fixture accesses a DRM
device or GPU.

For a cross run, pass a GCC16 cross compiler that targets NetBSD and repeat
`--runner-arg` for each target-runner argument. The test binary is appended to
that argument vector. The runner applies to both source fixtures. Without
`--runner-arg`, the script executes the binaries directly on the native NetBSD
host. The exact runner prefix and runtime invocations are stored in
`result.json` and the per-run command records.

```sh
python3 -B tests/amdgpu-asic-id-ctype.py \
    --archive /absolute/libdrm-2.4.134.tar.xz \
    --cc /absolute/path/to/netbsd-cross-gcc16 \
    --patch-tool /absolute/path/to/patch \
    --work /absolute/private/diagnostics/libdrm-amdgpu-ctype-cross \
    --runner-arg /absolute/path/to/target-runner \
    --runner-arg=-L \
    --runner-arg /absolute/path/to/target-sysroot
```

Use the runner's documented argv. Replace the example runner options with its
actual arguments. Pass each token separately. If an option starts with `-`,
use the `--runner-arg=VALUE` form shown above.

Run GCC's `-fanalyzer` and Cppcheck separately on the full upstream and patched
translation unit with the package's generated configuration and include paths.
Those results are distinct from this focused parser execution and from the
normal native or cross package build.

# Skip-list allocation regression

`skiplist-oom.py` compiles the supplied, patched `xf86drmSL.c` with an actual
C fixture. The fixture forces list, head, random-state, and node allocation
failures. It checks the API return values, head cleanup, insertion recovery,
duplicate return value `1`, and the final allocation/free counts. It does not
open a DRM device or submit GPU work.

Pass the patched source from the prepared libdrm 2.4.134 source tree, its
generated `config.h`, GCC16 for NetBSD, and a new diagnostic output directory.
The compiler command and runtime command, source hashes, toolchain identity,
and output streams are written into that directory.

```sh
python3 -B tests/skiplist-oom.py \
    --source /absolute/libdrm-2.4.134/xf86drmSL.c \
    --compiler /absolute/path/to/netbsd-gcc16 \
    --config-header /absolute/libdrm-build/config.h \
    --include-dir /absolute/libdrm-2.4.134 \
    --include-dir /absolute/libdrm-2.4.134/include/drm \
    --output /absolute/private/diagnostics/libdrm-skiplist
```

The output directory must not exist. Its parent directory must exist. Without
a runner, execute only on a NetBSD host whose architecture matches GCC16's
target. For cross compilation, repeat `--runner-arg` for each token in the
target runner command. The script appends the built binary path as the final
argument. The runner must be able to access that output path or stage the
binary before execution.

```sh
python3 -B tests/skiplist-oom.py \
    --source /absolute/libdrm-2.4.134/xf86drmSL.c \
    --compiler /absolute/path/to/netbsd-cross-gcc16 \
    --config-header /absolute/libdrm-build/config.h \
    --include-dir /absolute/libdrm-2.4.134 \
    --include-dir /absolute/libdrm-2.4.134/include/drm \
    --output /absolute/private/diagnostics/libdrm-skiplist-cross \
    --runner-arg /absolute/path/to/target-runner \
    --runner-arg=--target-option
```

The selected compiler must report GCC 16 and a NetBSD target. The script does
not select a compiler from `PATH`. Use the runner's documented argument
syntax. Pass each option as a separate `--runner-arg` value.
