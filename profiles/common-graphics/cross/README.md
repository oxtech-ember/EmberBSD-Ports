# Cross-build the graphics payload

The common tools and language packages own the compiler, sysroot and build
tools. This graphics-specific step consumes them without rebuilding LLVM,
Python or Meson. It builds the complete core-only libdrm 2.4.134nb1 payload
selected by the [canonical recipe](../recipes/x11/libdrm/Makefile).
Package creation/registration and the common Mesa/consumer transition remain
separate acceptance steps.

The [LLVM metadata helper](llvm-config.md) compiles upstream `llvm-config` for
the build host using the target build's actual metadata. The separate
[complete cross composition](profile.md) selects host tools and target
dependencies without changing the native profile.

KiCad 10.0.7 requires `protobuf>=36.2nb1` only for NetBSD cross builds; the
native package remains compatible with `protobuf-36.2`. The actual pkgsrc
dependency regression check is `tests/kicad-protobuf.rb`. Run it against the
prepared tree and cross make configuration:

```sh
BMAKE=/absolute/bmake ruby ../tests/kicad-protobuf.rb \
    /absolute/prepared-pkgsrc /absolute/cross-makeconf /absolute/new-work
```

The package path accepts EmberBSD 11/AArch64 and amd64. The amd64 selection
keeps Iris, VirGL, softpipe, llvmpipe and Zink, with the Intel libdrm module.
Its LLVM metadata must bind `x86_64-unknown-netbsd`, native component `x86`
and ELF machine 62 together. AArch64 keeps its V3D selection and native
`aarch64` component. Both reject foreign or mixed target metadata.
The host tests `tests/amd64-targets.rb` and `tests/llvm-targets.py` cover these
selection guards. They do not establish an amd64 package build or GPU support.
The older diagnostic and device-specific runners below retain their recorded
AArch64 scope; this recipe extension does not qualify those runners on amd64.
The [upstream Iris source](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.2.4/src/gallium/drivers/iris/meson.build)
builds the Gen11 path, and [Intel device metadata](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.2.4/src/intel/dev/intel_device_info.c)
identifies `jsl` (Jasper Lake). This supports the userspace source selection;
it does not establish an installed driver, kernel compatibility or GPU execution.

The full Mesa package now passes normal cross packaging and sysroot installation.
[Installed package acceptance](mesa-package.md) prepares the EGL/GLES consumer
and 37 upstream target invocations against its canonical runtime libraries.
Its [libepoxy consumer](epoxy.md) passes installed EGL/GLES dynamic dispatch,
four llvmpipe rendering lifecycles and four pure upstream tests on Zero 3W.
The separate [CM5 checks](mesa-cm5.md) cover hardware V3D rendering and a visible
Plasma capture. A sustained complete desktop and native HDMI hotplug remain
unverified. These CM5 results do not establish PowerVR graphics on Zero 3W.

[Wayland 1.26 and protocols 1.49](wayland.md) use a matching host scanner,
separate native metadata and the installed target libraries. Their target
tests are independent of the temporary Mesa diagnostic described below.

Use the [GCC16 cross compiler](../../development-toolchain/cross/README.md),
an AArch64 NetBSD 11 sysroot with its GCC16 CRT and base libpci, host Python
3.15 and the fully prepared common Meson 1.12.1 source. The sysroot must
contain real target libraries, headers and preserved SONAME links. Do not
substitute host libraries. The original libdrm URL and SHA256 are recorded
in [sources.tsv](../sources.tsv).

```sh
PYTHON=/absolute/python3.15 JOBS=4 sh build-libdrm.sh \
    /absolute/libdrm-2.4.134.tar.xz /absolute/cross-prefix \
    /absolute/target-sysroot /absolute/prepared-meson /absolute/new-work
```

The helper verifies the original archive and every recipe patch, applies
the full series with zero fuzz, selects native NetBSD atomics and retains
the recipe's core-only options, upstream tests and warning policy. Cross
compiler/linker inputs name only the target sysroot. The disabled pkg-config
lookup cannot import host optional libraries: this profile uses compiler
atomics and has no required external pkg-config dependency. A future module
requiring one needs a real target metadata path and a reviewed profile change.

`stage/usr/pkg` is compared with the complete canonical PLIST, including
symlinks. ELF metadata must not contain host work/compiler/sysroot paths.
`tests` contains the cross-built upstream hash, skip-list and device probes,
the upstream symbol checker and the same staged libdrm. Logs remain in the
work directory. Neither the helper nor the target test runner installs a
package, changes a desktop or restarts a VM.

Transfer `tests` into a new private directory on the target, preserving its
symlink. On macOS use `COPYFILE_DISABLE=1 tar --no-xattrs` to avoid carrying
Apple extended attributes into NetBSD. Verify SHA256 after transfer, then:

```sh
PATH=/sbin:/usr/sbin:/bin:/usr/bin:/usr/pkg/bin \
    PYTHON=/path/to/existing/python sh run-libdrm-tests.sh
```

The runner checks the resolved libdrm path for all three ELF programs before
executing any of them. Missing, ambiguous or foreign loader resolutions fail;
the SONAME symlink must resolve to the staged DSO. Loader closures are retained.
`sh test-runner.sh` checks these refusals with mocked loader output; it does not
replace the actual target run.
The Python executable only runs upstream's symbol inspection; Python is not
a libdrm runtime dependency. A device-test status of 77 is reported as SKIP,
never rendering success. Host `meson test` skips target executables without
an execution wrapper; its symbol checker also assumes the running OS's
object format. Use the target checker until that upstream cross-test boundary
is adapted. A zero host test failure count is insufficient acceptance.

## Verified boundary

On 2026-10-07, Apple Silicon macOS/GCC16.2 cross-built the selected shared
library and all enabled test programs with normal `-Werror` and only the
existing unsupported-bus `-Wno-error=cpp` exception. All 26 staged files and
links matched PLIST. The target DSO needs only NetBSD libpci.so.2 and libc.so.12;
its SONAME is libdrm.so.2. No build-host path appears in its dynamic metadata.

In the AArch64 NetBSD 11 UTM guest, hash, drmsl and the actual exported-symbol
check passed. Device enumeration returned 77 with no attached DRM device on
the ordinary EMBER64 kernel. That check used the existing Python 3.13.14 only
for upstream's inspection script; it did not install or select an older
interpreter for the common stack. Package registration, a booted matched
EMBERGPU kernel, DRM identity/permissions, Mesa26/LLVM23 and an accelerated
Wayland session are not established by this result.

The same cross-built libdrm subsequently passed hash, drmsl and actual PCI
device enumeration in an isolated QEMU 11.1.2/HVF VM booting the complete
`EMBERGPU` kernel at `c6aba7d1e240`. GCC16 also cross-built the existing
Examples GEM/PRIME probe, which passed malformed requests and 32 process
lifetime cycles. The [kernel receipt](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/external/bsd/drm2/virtio/kernel-boot.md)
records this separate serial-only boot. It does not establish a visible
console, accelerated rendering, the UTM desktop or package registration.

On 2026-10-08 the normal libdrm 2.4.134nb1 package was installed on physical
Zero 3W with the full Mesa/LLVM23 closure. The actual pkgsrc-built `hash`,
`drmsl` and exported-symbol tests passed against `/usr/pkg/lib/libdrm.so.2.134.0`,
without loader overrides. `drmdevice` returned 77 because `EMBER64 #4` has
no attached DRM device. This is installed-library acceptance, not GPU execution.

To repeat that installed check, copy `output/tests/{hash,drmsl,drmdevice}`,
`symbols-check.py` and `core-symbols.txt` from the same verified pkgsrc build
into a private target directory. Record and verify their hashes after transfer.
In that directory, use the installed package's recorded DSO hash and run:

```sh
unset LD_LIBRARY_PATH LD_PRELOAD
for program in hash drmsl drmdevice; do
    ldd "./$program" > "$program.ldd.log"
    loaded=$(awk '$1 == "-ldrm.2" && $2 == "=>" { p=$3; n++ }
        END { if (n != 1) exit 1; print p }' "$program.ldd.log") || exit 1
    test "$(realpath "$loaded")" = /usr/pkg/lib/libdrm.so.2.134.0 || exit 1
done
timeout 30 ./hash
timeout 30 ./drmsl
timeout 30 /usr/pkg/bin/python3.15 ./symbols-check.py \
    --lib /usr/pkg/lib/libdrm.so.2.134.0 \
    --symbols-file ./core-symbols.txt --nm /usr/bin/nm
# Preserve drmdevice's result: 77 means no device, not rendering success.
timeout 30 ./drmdevice
```

## Temporary headless Mesa diagnostic

`build-mesa-diagnostic.sh` builds Mesa 26.2.4 with all canonical source patches,
EGL/GLES/GBM, classic VirGL and softpipe. This temporary, uninstalled diagnostic
isolates graphics portability while shared LLVM23 is prepared. It deliberately
omits llvmpipe, X11/Wayland, XML configuration and zlib. It must not replace the
full common profile or become a second installed Mesa provider.

Supply the existing GCC16 cross compiler/sysroot, accepted libdrm prefix,
target zstd headers and library, prepared Meson, and host Bison 3.8.2. Python
3.14.8 needs Mako, packaging and PyYAML; existing verified source modules can
be supplied through `PYTHONPATH`. Host pkg-config reads only the two supplied
target providers. Ninja, Flex, Ruby, shasum and tar are also build-host tools.
The helper does not build or install common tools or target dependencies.
Keep the whole profile snapshot unchanged while the build runs and use a
fresh output directory. A running shell can reread edited script text.

```sh
PYTHON=/absolute/python3.15 JOBS=3 sh build-mesa-diagnostic.sh \
    /absolute/mesa-26.2.4.tar.xz /absolute/cross-prefix \
    /absolute/target-sysroot /absolute/libdrm-stage/usr/pkg \
    /absolute/target-zstd-prefix /absolute/prepared-meson \
    /absolute/host-bison /absolute/new-work
```

Archive URLs and SHA256 remain in [sources.tsv](../sources.tsv). The recipe
checks archive and patch hashes, rejects patch context drift and emits the
exact cross file, logs, tool versions and input hashes. ELF RPATH checks reject
build paths. Seven host tests inspect source data and actual target ELF API
exports; they do not execute target code. Undefined weak imports are excluded
from exports, while defined weak exports remain checked.

`mesa-diagnostic.tar.gz` contains private runtime libraries, the pixel test,
and 30 upstream target-test cases. Verify `bundle.sha256` after transfer and
extract into a new private directory. No package is installed. Inside `bundle`:

```sh
sh run-mesa-diagnostic.sh surfaceless softpipe
sh run-mesa-upstream.sh
# Only with a matched, enabled VirGL kernel/host and its actual render node:
sh run-mesa-diagnostic.sh /dev/dri/renderD128 virgl
```

Both runners check the complete artifact hash manifest before `ldd` or tests.
The host regression `../tests/mesa-bundle-integrity.sh NEW_WORK` confirms that
modified executables and libraries are rejected before loader execution.
The render runner checks loader paths, bounds rendering
to 60 seconds, rejects an unexpected renderer and verifies shader compilation,
clear/triangle pixels and four EGL lifecycles. `TIMEOUT` may name an alternative
target timeout executable. The upstream runner bounds each case to 120 seconds
and records failures and skips separately. It preserves the user's HOME;
the diagnostic's XML configuration is disabled. Runner `SKIP` means process
exit 77. Internal GTest skips and disabled cases remain in the per-case logs.

On 2026-10-08 the cross-built Mesa26 softpipe diagnostic passed all four render
lifecycles on Orange Pi Zero 3W (Allwinner A733), with EGL1.5 and GLES3.1 reported by the
driver. All 30 selected upstream target test runs exited 0. Within those
runs, `util_tests` passed 253 cases and skipped `Cache.List` because dynamic
Foz database lists are unsupported. NIR passed 6197 cases and reported nine
upstream-disabled cases. The process-name cases use an absolute executable
path matching `BUILD_FULL_PATH`.
The strict C11/C++17 stack-allocation regression also passed four target cases.
The complete diagnostic cross-build and seven host checks passed using the
[current GCC16 cross compiler](../../development-toolchain/cross/README.md),
whose host prerequisites are GMP 6.3.0, MPFR 4.2.2 and MPC 1.4.1.
This does not establish VirGL acceleration, LLVM/ORC, the complete graphics
package, X11/Wayland consumers or long-running stability.
