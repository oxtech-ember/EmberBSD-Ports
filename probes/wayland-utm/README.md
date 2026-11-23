# Native Wayland and VirGL build probe

This experimental probe stages the common libdrm, Mesa, wlroots and labwc
stack on EmberBSD/NetBSD 11 AArch64. It preserves the installed X11 libraries
and login session. Kernel DRM/KMS and an accelerated host VirtIO-GPU are
separate prerequisites; a build does not prove GPU acceleration.

## Selected source and acceptance level

| Component | Version | Upstream license |
|---|---|---|
| libdrm | 2.4.134 | MIT and source-file notices |
| Mesa | 26.2.4 | MIT and source-file notices |
| wlroots | 0.19.3 | MIT |
| labwc | 0.9.7 | GPL-2.0-only |

[`sources.tsv`](sources.tsv) pins original archive URLs and SHA256, checked
before extraction. Mesa 26.2.4 replaces the former 21.3.9 source selection.
The current source recipe and portability regressions are prepared. A
[temporary headless cross build](../../profiles/common-graphics/cross/README.md#temporary-headless-mesa-diagnostic)
passes software GLES shader/pixel checks and 30 selected upstream test runs on
Orange Pi Zero 3W (A733). It excludes LLVM, X11/Wayland and package installation.
**The complete common Mesa/LLVM profile and guest accelerated runtime remain
pending.** Configuration alone does not establish a validated graphics stack.

The [common graphics package profile](../../profiles/common-graphics/README.md)
now owns canonical MesaLib/libdrm recipes for the final `/usr/pkg` transition.
It preserves this probe's accepted source patches and adds package/dependency
selection. Its source-derived package contents still require native validation;
this private probe remains the owner of the focused source regressions.

The [Mesa patch inventory](mesa-patches.md) explains all retained, replaced
and removed adaptations, including original pkgsrc identifiers. Non-Mesa
patches retain their imports from
[pkgsrc 0491f5e57e8fba00998bf1a6c0958ef421fefaa1](https://github.com/NetBSD/pkgsrc/tree/0491f5e57e8fba00998bf1a6c0958ef421fefaa1):
x11/libdrm, wayland/wlroots, wayland/labwc and sysutils/seatd.
Local AI-assisted fixes are not submitted upstream. Original source
copyright and licenses remain unchanged. Our shell/C/C++ probes use the
included BSD-2-Clause license.

## Common toolchain and private build

Use common GCC 16.2.0 C/C++ runtime, LLVM 23.1.2 shared library,
Meson 1.12.1 and Python 3.14.8. Absolute `CC`, `CXX`, `LLVM_CONFIG`,
`PYTHON` and `PKG_CONFIG` paths may select their common staging location.
The helper verifies versions and records tool hashes and metadata. It refuses
older installed LLVM instead of disabling llvmpipe. Python/Mako remain
upstream build dependencies; no project helper is Python.

The package environment supplies Ninja, Bison, Flex, Mako, seatd,
libdisplay-info, libsfdo, hwdata, Wayland/protocols, libxkbcommon, pixman,
libudev-bsd, expat, zlib/zstd, libepoll-shim, glib2, cairo, pango, librsvg,
libxml2 and X11/XCB development metadata. This source probe is not a package
dependency resolver. Complete the common toolchain transition first.

Build as an ordinary user into a new absolute directory. Set `INPUT_PREFIX`
to the accepted private absolute-pointer libopeninput build described below.
The helper preserves that selection while rebuilding wlroots/labwc.

```sh
INPUT_PREFIX="$HOME/.cache/emberbsd-libopeninput-build/install" \
    sh build.sh "$HOME/.cache/emberbsd-wayland-current"
```

The optional second argument supplies the four archives locally, with the
same hash checks. `JOBS` defaults to one; this also bounds Meson's implicit
Ninja test-target rebuilds. Artifacts go into `install/`; source receipts,
tool/library metadata and stage logs remain under `log/`. Failures preserve
their status. Nothing overwrites package-owned shared libraries.

The Mesa profile enables classic VirGL, softpipe, llvmpipe with LLVM ORC JIT,
EGL, GBM, GLES and X11/Wayland GLX. Current Meson options replace the obsolete
Mesa 21 options. Vulkan, Rusticl, video frontends and unrelated physical
drivers/tools are disabled. This does not enable the kernel VirGL feature.

## Regression and integration checks

The helper runs upstream Meson tests plus actual-source DSO lifetime,
half conversion and symbol-policy regressions under `tests/`.
The DSO regression checks two owner-local copies, 64 unload cycles, an unused
DSO, mixed C++/C registration order, normal exit and injected allocation/
registration failures. A plain-atexit control must reproduce cleanup failure.
The half regression checks all 65536 encodings with FP flush off and on.

On 2026-10-06 these narrow checks passed on NetBSD 11/AArch64 using base
GCC 12.5: 64 two-DSO unload cycles, mixed C++/C order, ordinary exit, local
ELF bindings and injected failures. Plain atexit fails the same cleanup
contract. Patched half conversion has zero failures; pristine Mesa has 2046.
The upstream symbol-policy check passes with the existing Python 3.13.
The DSO and half-conversion checks also pass with the installed GCC 16.2
candidate on NetBSD 11/AArch64. The DSO process loads exactly one candidate
libstdc++ and libgcc runtime, checked by canonical file identity. This
establishes those narrow helpers with the selected compiler; complete Mesa,
LLVM 23 JIT, actual util_queue/ORC lifetime and consumer migration remain
unverified.

[`audit-libraries.sh`](audit-libraries.sh) records ELF dynamic dependencies,
hashes and native loaded paths for staged graphics and compositors. It rejects
mixed Mesa/libdrm/input/LLVM/C++ runtimes and legacy shared-libglapi links.
Supply affected Qt, GNOME and Xorg consumer objects as further arguments for
their separate migration audit. Never add fake SONAME compatibility links.

After building, run the [Examples EGL/session checks](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/desktop/wayland-utm):
64 allocation/render/destruction cycles checking every pixel with both softpipe
and llvmpipe, normal exit/unload, GLX, native input and client sharing.
Record actual paths again in live processes. A staged loader audit does not
prove dynamically opened drivers or compositor runtime.

The former Mesa 21.3.9 build passed 81 Mesa tests and 64 software EGL pixel
cycles on 2026-10-06. Its 2D KMS session and physical keyboard/pointer checks
passed with the matched experimental kernel and input library. Those results
are **not transferred to Mesa 26**. Keep the old prefix only for comparison/
recovery; remove it after current Mesa and the rebuilt compositor pass the
same lifecycle/input/native-session checks. Further retention requires a
named consumer incompatibility and a removal condition.

## Native render identity prerequisite

The [libdrm identity probe](native-identity.md) uses matched kernel metadata
without primary master or global PCI access. Host/native contracts and the
isolated library build pass; full matched kernel builds and runtime remain
pending. The original recovery kernel cannot prove render-node discovery,
KMS or dma-buf sharing. Software EGL on it establishes CPU plumbing only.

## seatd keyboard restoration probe

The separate `build-seatd.sh` stages seatd 0.9.3 (MIT) without modifying the
installed package. Its original archive URL and SHA256 are in
[`seatd-source.tsv`](seatd-source.tsv), and its SHA512 was checked against
the same pinned pkgsrc revision. Two pkgsrc patches are retained unchanged;
`patch-wscons-keyboard-restore` is a local AI-assisted follow-up, not submitted
upstream.

The pkgsrc terminal patch selects `WSKBD_RAW` when restoring the text
console. For NetBSD USB keyboards that mode emits compatibility PC/AT
bytes, bypassing wscons key events. libopeninput consumes wscons events,
so both its active input and restored console need `WSKBD_TRANSLATED`.
Exclusive access to `/dev/wskbd*` suppresses normal console delivery while
the compositor owns input. Simply swapping RAW and TRANSLATED would break
the active compositor's keyboard path.

```sh
sh build-seatd.sh "$HOME/.cache/emberbsd-seatd-build"
```

The test compiles the real patched `terminal.c`, replacing only its ioctl
boundary, and checks both mode transitions and error propagation. It failed
against the pkgsrc-only source and passed with the local patch. All three
upstream seatd tests also passed on NetBSD/aarch64. Physical keyboard/pointer input passed in the matched native session.
VT switching and visible exit/crash recovery remain pending.

The staged prefix is `stage/usr/pkg`; no binary is made setuid. For the
experimental runtime installation, an administrator should retain the
packaged `/usr/pkg/bin/seatd` and install only the staged `bin/seatd` there,
owned by root with mode 0755. The existing packaged `seatd-launch` already
starts that path and drops privileges before launching the compositor.
Keep the packaged libseat and launcher. Restore the saved daemon to undo
this local package-file change; a package upgrade may overwrite it.

## NetBSD absolute pointer input

The packaged libopeninput 1.30.2 wscons backend ignores absolute X/Y events,
and its four absolute coordinate accessors return -1. QEMU's USB Tablet
therefore produces clicks while the Wayland cursor remains at its origin.
The separate `build-libopeninput.sh` builds a private library with the same
`libinput.so.10` ABI; it does not replace the packaged library.

[`libopeninput-source.tsv`](libopeninput-source.tsv) pins the original
sizeofvoid/libopeninput archive at `dcf8584ec3f5cde2a2098de25276242d2d815cc7`,
including its URL and SHA256. Its bytes also match the pinned pkgsrc SHA512.
The original MIT/Expat license and source notices are retained. The two
`patch-src_wscons.*` patches are unchanged imports from the same pkgsrc
revision as the graphics probe. `patch-wscons-absolute-pointer` is a local
AI-assisted adaptation, not submitted upstream.

```sh
sh build-libopeninput.sh "$HOME/.cache/emberbsd-libopeninput-build"
```

Dependencies come from the existing pkgsrc environment: meson, ninja-build,
libudev-bsd, input-headers and libepoll-shim. Meson and upstream generators
require Python; the recipe and regression helper use shell and C. An optional
second argument supplies the original archive locally, with the same hash
check. Builds require a new absolute directory and an ordinary user.

The patch obtains raw HID bounds through `WSMOUSEIO_GCALIBCOORDS`. It supports
uncalibrated absolute devices with valid X/Y bounds and
`WSMOUSE_CALIBCOORDS_RESET`; calibrated touchscreens are outside this probe.
Adjacent axes are combined before a button event or at the end of each read.
Transformed accessors scale the coordinates to the compositor's output.
Wscons supplies no physical resolution: untransformed accessors use a
one-unit fallback, so their values are not measured physical millimetres.
Relative mouse events keep their existing acceleration path.

On 2026-10-06 the complete native build and the production-code regression
passed on NetBSD 11/aarch64. The regression failed against the pkgsrc-only
source because no absolute motion was emitted. It links actual upstream
objects, substitutes the calibration ioctl and feeds wscons events through
the real dispatch function. It checks all four accessors, nonzero minima,
axis retention, endpoints, motion before buttons, invalid or unsupported
calibration and relative fallback. Wide positive and INT_MIN..INT_MAX bounds
verify that coordinate arithmetic occurs in double before subtraction and
output scaling. The upstream Linux input tests are
disabled, as in pkgsrc; this is not a claim that their suite passed.

For the native session, prepend this build's `install/lib` to the existing
private graphics `LD_LIBRARY_PATH`. Confirm the compositor's loaded library
path and test motion, clicking and input in a fresh session separately.
The keyboard mapping is unchanged: a live trace showed correct press and
release events for ordinary letters, Shift and Return.

## Validation boundary

The helper runs the available upstream test suites. libdrm's `drmdevice`
test can legitimately skip when no DRM device is attached; a skip is not
a successful GPU test. The accepted Mesa 21 native input/2D checks must be repeated after this
transition. VT recovery, VirGL pixels and reboot recovery remain pending.

Xwayland and Vulkan are initially disabled to isolate native Wayland and
classic VirGL. Optional libliftoff is disabled: the available binary links
base libdrm.so.3 while this private build provides libdrm.so.2. Loading both
would mix the DRM stacks. wlroots retains its built-in KMS plane handling.
This probe does not provide a GNOME Wayland port or a new
display manager. See the OS's
[VirtIO-GPU design](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/external/bsd/drm2/virtio/docs/utm-virgl-design.md)
for the staged runtime acceptance checks.
