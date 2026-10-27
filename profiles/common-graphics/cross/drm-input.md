# Current wlroots DRM, input and color dependencies

This is the next package stage after the accepted
[headless GLES2 consumer](wlroots-package.md). It keeps the same canonical
MesaLib 26.2.4nb2, libdrm 2.4.134nb1, Wayland 1.26.0nb1 and LLVM23 ABI.
The installed package passes real DRM presentation with llvmpipe in an
EMBERGPU VM and [VirGL on the paired Metal host](wlroots-virgl.md) with
EMBERVIRGL. The separate [labwc session check](labwc-session.md) now verifies
EGL surfaces, screencopy and real QEMU USB input in two repeated sessions.

## Selected sources and providers

The five additional canonical recipes are pinned in [sources.tsv](../sources.tsv).
Upstream tags/releases were checked on 2026-10-08. Input headers and runtime
come from the same libopeninput commit, `10995219206280da0f1a3ba124abe4c8ef89e021`.
No older input runtime is pulled in alongside the current headers.

| Component | Version | Role | Primary source |
| --- | --- | --- | --- |
| hwdata | 0.412 | Native data generator input | [release](https://github.com/vcrhonek/hwdata/releases/tag/v0.412) |
| scdoc | 1.11.5 | Native seatd manual generator; pinned pkgsrc recipe | [tags](https://git.sr.ht/~sircmpwn/scdoc/refs) |
| libdisplay-info | 0.4.0 | EDID/DisplayID parsing | [release](https://gitlab.freedesktop.org/emersion/libdisplay-info/-/releases/0.4.0) |
| seatd/libseat | 0.9.3nb1 | Session and device access | [source](https://git.sr.ht/~kennylevinsen/seatd) |
| libopeninput | 1.31.3nb1 | NetBSD/OpenBSD wscons input runtime | [selected commit](https://github.com/sizeofvoid/libopeninput/tree/10995219206280da0f1a3ba124abe4c8ef89e021) |
| libliftoff | 0.5.0 | DRM plane allocation | [release](https://gitlab.freedesktop.org/emersion/libliftoff/-/releases/v0.5.0) |
| lcms2 | 2.19.1 | Color management; pinned pkgsrc recipe | [release](https://github.com/mm2/Little-CMS/releases/tag/lcms2.19.1) |

The lcms2 package retains its image tools and therefore requires TIFF 4.7.2,
libjpeg-turbo 3.2.0nb2, Lerc 4.2.0 and JBIG-KIT 2.1nb1. These current upstream
versions already exist in the pinned pkgsrc; no duplicate Ports recipe or
private library prefix is needed. Existing base zlib/liblzma providers are
reused through pkgsrc's normal builtin checks.

## Cross composition

Use the existing [common cross MAKECONF](profile.md), accepted compiler,
target sysroot and matching host Wayland scanner. First build/install native
hwdata and scdoc into the same `TOOLBASE` selected by that MAKECONF. Then build
the target dependencies with normal pkgsrc checks:

```sh
cd /absolute/prepared-pkgsrc/x11/libdisplay-info
bmake MAKECONF=/absolute/graphics-cross.mk package
cd ../../sysutils/seatd
bmake MAKECONF=/absolute/graphics-cross.mk package
cd ../../devel/libopeninput
bmake MAKECONF=/absolute/graphics-cross.mk package
cd ../../graphics/libliftoff
bmake MAKECONF=/absolute/graphics-cross.mk package
cd ../lcms2
bmake MAKECONF=/absolute/graphics-cross.mk package
cd ../../wayland/wlroots
bmake MAKECONF=/absolute/graphics-cross.mk \
    EMBERBSD_WLROOTS_PROFILE=drm-gles2 package
```

The explicit `drm-gles2` stage enables GLES2, DRM, libinput, libseat session,
color management and libliftoff. It rejects option overrides. The default
`full` profile still selects all eleven supported options, including Vulkan,
X11, Xwayland and examples. This staged package does not claim those omitted
consumers are migrated. Vulkan needs a separately accepted provider and a
real native glslang; labwc and its remaining desktop dependencies come later.

The native graphics metadata guard uses the genuine installed hwdata/scdoc
`.pc` files and the host pkg-config executable. It requires the exact selected
version and prefix. Meson's native search clears the inherited target sysroot
and uses only the selected host directories. When wlroots also needs the
scanner, its existing scanner native file supplies the same host directories
plus the receipt-verified scanner prefix. Target libraries still use buildlink.
Native package builds keep their original tool-selection path.

## Portability changes and affected consumers

libdisplay-info explicitly uses pkgsrc's host `TOOL_PYTHONBIN` for its upstream
search-table generator. Its version-script probe tests the actual linker flag
with the source file, retaining exported-symbol control on NetBSD. It obtains
`pnp.ids` through native hwdata metadata; an absent host provider cannot fall
back to an unrelated system directory.

seatd retains the pkgsrc BSD device changes and the existing EmberBSD wscons
keyboard restoration patch. Its scdoc lookup is native, including metadata;
cross builds do not try to execute a target-prefix manual generator.

libopeninput's explicit `epoll-dir` is the pkgsrc buildlink directory, rather
than a path derived from the target installation prefix. The existing hotplug
patch uses upstream 1.31.3's typed `usec_t` and `usec_from_timespec()` API.
The absolute-pointer patch retains raw wscons calibration, ordered axis/button
dispatch, signed/wide coordinate handling and relative-pointer behavior.
It explicitly includes the ioctl declaration used by that adaptation.

The selected upstream BSD fork itself excludes Linux-only libwacom, Lua,
debug GUI/tools and litest paths on NetBSD/OpenBSD. Their absence is not a
passing Linux input suite or a claim that these features work on EmberBSD.
The existing [wscons contract](../../../probes/wayland-utm/tests/wscons-absolute.c)
and [keyboard restoration contract](../../../probes/wayland-utm/tests/seatd-keyboard.c)
exercise the adapted source; physical device/session tests remain separate.

## Focused checks

The test helpers accept absolute paths and create a new evidence directory:

```sh
BMAKE=/absolute/host/bin/bmake ruby ../tests/native-graphics.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk /absolute/new-native-check
BMAKE=/absolute/host/bin/bmake ruby ../tests/input-cross.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk \
    /absolute/patched-libopeninput-source /absolute/cross/bin/aarch64--netbsd-gcc \
    /absolute/sysroot /absolute/host/bin/meson /absolute/new-input-check
/absolute/native-prefix/bin/python3.15 -B -I -S ../tests/wlroots-selection.py \
    --pkgsrc /absolute/prepared-pkgsrc --makeconf /absolute/graphics-cross.mk.conf \
    --host-prefix /absolute/native-prefix --utility-path /absolute/native-tools \
    --work /absolute/new-selection-check
```

`input-cross.rb` executes the actual upstream epoll Meson block. The original
target-prefix lookup fails; the selected buildlink root passes the real link
check. It also compiles the complete wscons translation unit against current
headers, with controlled reversions of the old timestamp API and missing
ioctl prototype. Both controls fail, while the adapted source compiles.
These checks do not substitute for target input events.

The exporter requires all 27 source pins, including the subsequent
[text/image dependencies](labwc-dependencies.md), each approved patch and the
native metadata helper. Its preflight-only mode exercises 67 refusals without
allocating a complete pkgsrc tree. The full mode additionally checks the six
profile compositions and cleans each disposable export before the next one.

## Package and target acceptance

The `drm-gles2` wlroots package and all listed dependencies cross-built on
macOS with GCC16 and passed normal pkgsrc checks. The installed target
configuration records exactly `color-management drm glesv2 libinput
libliftoff session`. The accepted headless nb4 archive is retained separately:
the package name is the same, but the feature payload and library hash differ.
When switching this leaf package in the cross sysroot, ordinary `pkg_add -u`
refused the already registered name. Removing that leaf with `pkg_delete`
and installing the new archive normally preserved package guards; no force
or unchecked replacement option was used.

[prepare-wlroots-drm.rb](prepare-wlroots-drm.rb) accepts the same tools/sysroot,
an accepted current Mesa bundle, a new work directory and seventeen exact
package archives. It verifies every supplied installed payload and link.
The set includes libudev-bsd 0.7.0.1 and libxcb 1.17.0: checking only the
consumer's direct ELF dependencies missed libudev and xkbcommon-x11's
libxcb-xkb provider. The builder now checks every unique recorded ELF's
`DT_NEEDED` entries and records all resolved edges in `recursive-needed.tsv`.
[drm-recursive-closure.rb](../tests/drm-recursive-closure.rb) executes that
actual guard with the complete manifest and with udev, xcb-xkb or LLVM removed.

In a dedicated target with real DRM and wscons devices, start the installed
seatd service and run:

```sh
sh /absolute/bundle/run-wlroots-drm.sh /absolute/bundle \
    /dev/dri/card0 /absolute/new-drm-logs
```

The runner requires the real DRM and libinput backends plus an active libseat
session. It selects llvmpipe by default, verifies package/library manifests,
and checks live loaded providers. Four rendered frames must pass 1024-pixel
GLES2 readback and matching DRM presentation events before cleanup. Timeout
is bounded; missing output/input prerequisites fail rather than selecting a
headless or pixman backend. This consumer does not receive application surfaces.

An explicit fourth argument selects the experimental VirGL path with the same
installed `drm-gles2` package and presentation/pixel checks:

```sh
sh /absolute/bundle/run-wlroots-drm.sh /absolute/bundle \
    /dev/dri/card0 /absolute/new-virgl-drm-logs virgl
```

This requires the separate EMBERVIRGL kernel and the accepted paired QEMU
classic profile with ANGLE Metal, as used by the [first guest draw](virgl-draw.md).
The consumer's own optional argument is `[llvmpipe|virgl]`; omission preserves
the CPU mode. CPU mode requires its two explicit software flags. VirGL mode
forbids them, and both modes reject loader/driver overrides. The actual GLES
renderer must match the selected name before allocator creation or modesetting.
There is no fallback to llvmpipe or pixman when VirGL is unavailable. The
runner retains its clean environment and 60-second limit plus five-second
forced-kill grace period; host supervision remains a separate 120+5-second
bound. `wlroots-drm-mode.rb` compiles the actual C admission/renderer predicates
and exercises the real shell invocation functions; its synthetic policy data
does not establish presentation. The separate [runtime acceptance](wlroots-virgl.md)
confirms four accelerated DRM frames. CPU regression uses the 2D EMBERGPU
device; on a VirGL-capable node Mesa can still select VirGL despite these
software flags, and the expected-renderer guard correctly refuses that run.

An isolated serial-console VM can use seatd's explicit `SEATD_VTBOUND=0` mode.
That does not prove virtual-terminal switching. Supply actual QEMU USB
keyboard/mouse devices and the corresponding kernel wscons nodes: upstream
libopeninput opens `wskbd0..9` and `wsmouse0..9`, and wlroots rejects zero
devices. Enumeration is reported separately from input-event acceptance.

[prepare-drm-dependency-tests.rb](prepare-drm-dependency-tests.rb) takes cross
tools, sysroot, host pkg-config, the verified DRM bundle, the four patched
seatd/libopeninput/libdisplay-info/libliftoff source roots and new work.
It prepares 131 invocations: two existing wscons contracts, three upstream
seatd tests, 68 upstream EDID golden checks and 58 upstream libliftoff tests.
Run `run-drm-dependency-tests.sh BUNDLE NEW_LOGS` on the target. EDID harnesses
also need the base `mktemp`, `cp`, `diff`, `patch` and `rm` utilities.

The wscons contracts replace only ioctl boundaries and use real upstream
dispatch/terminal source. libliftoff's upstream mock DRM is linked into its
test executables; the library under test is installed libliftoff. EDID tests
use the installed decoder and a freshly linked upstream printer. None needs
a private DSO or loader override. These algorithm/source contracts are not
hardware tests.

## Accepted target result

On 2026-10-08, the isolated AArch64 QEMU/HVF VM ran the `EMBERGPU` kernel
built that day, with its native 2D virtio DRM driver and QEMU USB keyboard/mouse.
The exact canonical packages used LLVM 23.1.2nb1 and wlroots 0.20.2nb4 with
the `drm-gles2` selection. Package payloads, links, recursive ELF dependencies
and live loaded providers passed their guards.

The consumer selected `Virtual-1` at 1280x800 and 59959 mHz through the real
DRM backend. All four frames passed 1024-pixel GLES2 checks and matching-sequence
DRM presentation events (`flags=0xf`). The libseat session was active; libinput
enumerated the actual `wskbd0` and `wsmouse0` devices. Cleanup completed and both
the runner and QEMU exited zero. Duplicate output in the serial log comes from
the outer log collector; it does not represent eight rendered frames.

The separate dependency run passed all 131 invocations with exit zero and
no unexecuted entries. It includes the two source contracts, three seatd tests,
68 EDID golden comparisons and 58 upstream libliftoff mock cases described above.
Missing base utilities were built from the unchanged current EmberBSD sources
for the isolated root; no package library was replaced to run these checks.

| Evidence | SHA256 |
| --- | --- |
| DRM bundle | `09b92aeb0f4366d1507818b066203b5eb95ef99e2cd759614c2042470ca7b659` |
| DRM serial log | `432754208023d5af17906bbd52109c50e9250ee1c53d2e2072cffd64027cb430` |
| Dependency bundle | `e6206b540be7934e8d4cc49d44c21dbacd1f2d62fd0cd4797e91355fc908ea06` |
| Dependency serial log | `2d184e3e8d464d8750b86cf822dcce782e16dffb3b9eb1417e71c83aef486497` |

This original run proves CPU llvmpipe rendering and DRM presentation in that
VM. The subsequent [VirGL result](wlroots-virgl.md) adds GPU rendering and
scanout on the paired host. Neither establishes input-event delivery,
virtual-terminal switching, application surfaces, a labwc desktop,
physical-board scanout or long-running compositor stability. The serial-console session explicitly used
`SEATD_VTBOUND=0`; no zero-device override or software pixman renderer was used.
