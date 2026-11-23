# labwc EGL, screencopy and USB input on VirGL

The packaged labwc 0.20.2nb2 passes two consecutive Wayland sessions in an
isolated EmberBSD AArch64 QEMU/HVF guest. Both compositor and native xdg-shell
EGL client use Mesa `virgl` on the paired ANGLE Metal host. EmberBSD Ports owns
this package acceptance harness. This is a bounded application-surface/input
check, not a general desktop release or physical-board GPU qualification.

## Inputs and preparation

Use the [accepted labwc package](labwc.md), shared MesaLib 26.2.4nb2,
wlroots 0.20.2nb4 and the [matched VirGL trial/QEMU pair](wlroots-virgl.md).
Keep the kernel's matched recovery bundle. The target base and rescue tools
must come from the recorded EmberBSD test root. The helper verifies the known
fork shared-libc repair, but does not certify the complete base as an SDK.
Do not fill missing base components from upstream sets.

Build the [host renderer](../../../probes/utm-virgl-host/host/README.md) and
run its native acceptance with the exact ANGLE frameworks being used. A changed
framework hash invalidates the previous native receipt. The 2026-10-09 run
used freshly built renderer/epoxy and frameworks extracted from the official
[UTM 4.7.5 DMG](https://github.com/utmapp/UTM/releases/tag/v4.7.5).
It did not install UTM. ANGLE reports 2.1.22612 / `40dfb3a8bd65`, Metal on Apple M4.
The earlier M3 result remains historical evidence for its own input hashes.

From `profiles/common-graphics`, with new absolute work directories:

```sh
ruby cross/build-labwc-client.rb /path/to/cross-tools /path/to/sysroot \
  /path/to/native/wayland-scanner \
  /path/to/wlroots-0.20.2/protocol/wlr-screencopy-unstable-v1.xml \
  /path/to/new-client
ruby cross/prepare-labwc-root.rb /path/to/sysroot /path/to/recorded-base-root \
  /path/to/new-client/labwc-session /path/to/cross-tools/bin/aarch64--netbsd-readelf \
  /path/to/labwc-0.20.2nb2.tgz /path/to/new-root
/path/to/nbmakefs -t ffs -s 768m -F cross/labwc-root.mtree \
  /path/to/new-root/root.ffs /path/to/new-root/root
ruby cross/run-labwc-session.rb /path/to/accepted-qemu-work \
  /path/to/accepted-renderer-work /path/to/netbsd-VIRGL_TRIAL.img \
  /path/to/new-root/root.ffs /path/to/ANGLE-frameworks /path/to/new-evidence
ruby tests/labwc-session-oracle.rb /path/to/new-evidence/guest.log
```

The supplied base root must contain `/rescue` including init, shell, mount,
halt and ordinary file tools; the dynamic loader and their shared dependencies;
`/usr/bin/sha256`, `/usr/bin/timeout`, `/usr/pkg/bin/seatd`; the accepted Mesa
DRI/GBM modules and wlroots DRM/input closure. Reuse the root prepared for
[the DRM scenario](drm-input.md). The root builder copies it with hard links
preserved, overlays the verified compositor/font/SVG payload and resolves
additional ELF dependencies from the explicit sysroot. It records base,
input and final-root hashes. No private account or application is required.

The guest creates tmpfs at `/tmp`, `/var/run` and `/var/shm`. The last must have
mode 1777: EmberBSD's POSIX shared-memory implementation checks both the
filesystem type and permissions. Omitting it caused the first experimental
labwc startup to fail during keymap/format-table allocation. The corrected
boot script prepares it before starting seatd or labwc.

## What is checked

The client first maps a 640x400 normal window to establish restore geometry,
then requests fullscreen and renders four different
EGL colors, checks its framebuffer and waits for each frame callback. It then
uses the compositor's screencopy protocol and checks 1024 central pixels in
each 1280x800 output. Both RGB and BGR byte orders are handled explicitly.
The capture excludes the cursor. A framebuffer check alone is not counted
as output capture.

After all four captures, the host sends relative pointer movement, left-button
press/release and K press/release through QMP to actual QEMU USB mouse/keyboard
devices. The client must receive the corresponding Wayland motion, button and
key events. Device enumeration alone does not pass. QMP uses a private Unix
socket; no network or user disk is connected. `SEATD_VTBOUND=0` is explicit.

After the baseline USB input, the host sends F11, F10, F10 and F11 through
the virtual USB keyboard. The isolated labwc configuration binds these to
ToggleFullscreen and ToggleMaximize. The client makes no state requests
during this cycle; it waits for normal, maximized, restored and fullscreen
configures in sequence. Each configure must carry the expected
maximized/fullscreen flags. Normal and restored content must be 640x400;
fullscreen must be 1280x800. The accepted maximized content is also 1280x800:
this client does not negotiate server decorations. Protocol state distinguishes
maximized from fullscreen. Server decorations and resize handles remain
outside this check.

Each state renders 15 changing-color frames with a one-second delay between
captures. Each capture checks 1024 output-center pixels and the client checks
its own EGL center pixel. The host checks all 60 added captures and cumulative
monotonic durations of at least 14/28/42/56 seconds. This is paced rendering,
not a throughput benchmark or a sustained-stability qualification.

After the four-state cycle, F11 restores the normal window. The client draws
magenta and scans the whole screencopy image for its exact 640x400 rectangle:
all 256000 pixels must match. The host moves the USB mouse until the client
reports a pointer position safely inside the restored window, then holds Alt and the left mouse button,
sends ten relative mouse movements of +5,+3, then releases both. A final USB K
release acknowledges the end of injection. The client captures the magenta
rectangle again. Its size and area must be unchanged and its screen position
must move right and down by 1..200 pixels. The bound allows input acceleration;
it does not substitute the requested pointer delta for measured window motion.
Screencopy Y-inversion is handled for the rectangle coordinates. The capture
excludes the cursor. An unchanged rectangle fails even if input was delivered.
The host also requires all ten shortcut and both drag injections across the
two sessions. This tests the explicitly supplied F10/F11 and Alt-drag bindings,
not every shortcut or the compositor's default configuration.

The client destroys its EGL and Wayland objects and exits. labwc's session
mode then terminates the compositor. The guest starts the same scenario again
and finally stops seatd and halts. It checks 142 staged runtime ELF hashes
before and after the sessions. The host checks both client and compositor
renderers, per-session frame/color/input sequences, result markers, clean QEMU
exit, host loaded-library paths and unchanged input FFS. A zero compositor
exit without the client's success marker is rejected.

The host limit is 340+5 seconds; each compositor has a 155+5 second limit and
the client has a 140-second alarm. The log oracle regression rejects twenty-nine
mutations, including software renderers, wrong pixels, missing release events,
failed cleanup, missing runtime-integrity evidence, wrong window states,
geometry, capture sequences and duration.
Serial input is read as bytes: polling can split UTF-8 debug glyphs between
writes. The regression also accepts incomplete UTF-8 in unrelated debug text.
Acceptance markers remain exact ASCII matches.

## Result and boundaries

The interactive 2026-10-09 cycle passed twice on the same matched host.
Each session produced 66 captures and completed all five keyboard shortcuts.
Both drag captures measured a move from (320,200) to (411,254), or +91,+54,
with unchanged 640x400 dimensions and 256000 matching magenta pixels.
Runtime ELF hashes and input FFS integrity passed; the guest halted at 144.4
seconds. The log regression rejected 29 false-success mutations, including
missing pointer entry, an unmoved rectangle, wrong area and missing shortcuts.
An earlier exploratory run injected the drag outside the restored window;
the unchanged rectangle correctly failed. The accepted runner requires
Wayland pointer-position feedback before pressing the drag button.

| Interactive evidence | SHA256 |
| --- | --- |
| Client | `de35ece2f50312ec39d5ddcb3960b26fcdbe33c72e4aa4b56248d27acc563888` |
| Test FFS | `2bf97250b0f8fbc61c4769bd81cfc11194bb85e8de08e36ccd36996ee625aad1` |
| Guest log | `968886cb9312decfb66288c7d77d839051a1a479af622c1ebcf6dd7dff83dbbd` |
| Host log | `1b90b1a0dbb74226593c8e36fdfcc5eaf3e1dcf2fa55660b11b25e1d29eb37cc` |
| Output manifest | `3e04198e8e0cdaebbb3a889c8771740de672a853e598f4f620b4a7b62f4f2614` |

The preceding client-requested window cycle passed twice on 2026-10-09.
Each session produced the original four fullscreen captures plus 60 paced
captures across normal 640x400, maximized 1280x800, restored 640x400 and
fullscreen 1280x800 states. Each window cycle took 61 monotonic seconds.
The guest halted at 140.9 seconds; both runtime checks and unchanged-input
checks passed. The oracle accepted the log and rejected 21 false-success
mutations; incomplete UTF-8 debug text was also accepted without losing checks.

| Extended evidence | SHA256 |
| --- | --- |
| Client | `f321c6501f0c68737bda698fc3647665471341de118b894d18f1d55684b371f1` |
| Test FFS | `f6e389ebdbb5d943ad8dcecc1d79e3640cb695043a7005770850bcd508cde5b5` |
| Guest log | `558131f1cad5c53533f02a2ea41d0c5078c02fd513f17dbfc081bed2a66b1f07` |
| Host log | `0d91dfc3110823dd0a5dd4e0b1a43c1eae5f05a2b6743f27b1d6353bc42c48f5` |
| Output manifest | `4042e3d2919b7d31be8103c5740823c1cf942b6e335a7969b3fff7124a88bfa1` |

The original 2026-10-09 four-frame harness passed on Apple M4 / ANGLE Metal.
Its historical inputs and receipts are listed below.
Each of two sessions delivered four 1280x800 captures, keyboard and pointer
events, then exited cleanly. Runtime hashes passed twice; the guest halted
at approximately 13.9 guest seconds. The unchanged prior wlroots DRM workload
also passed with this rebuilt host before the labwc run.

| Evidence | SHA256 |
| --- | --- |
| Client | `adfe95840e273f6a67e59204fbb1bd59a1f6a78d570454e3e743eec59cdc7b82` |
| Test FFS | `ed160c85cf8ec18a11131970209889d952e704477d19b0699f091e91e7088278` |
| Guest log | `d046b40f258bd1e6da2d8e563d2394246bfd2c35cecea8172177a16050c72399` |
| Host log | `74933816fb87d14b784e72df043529a205630b840cfeb3a75c36b8c3ed60a8f4` |
| Output manifest | `902cc91c580968c940402f9622d27312f6122a6f0a2e3c05cb3256a14f8a5124` |
| UTM DMG | `a8435c93cfb5f8bbfeea4b134cfad1ac66b67632b75e438c63b1a8ae043bef0e` |
| EGL framework | `3d099577b2dad45bedc55d25971c9725e5acffa130745720ab6da052dfa2c616` |
| GLESv2 framework | `e146b9185ed7b8a1bf45d7ec9977f38d60d6c6d286f4b3373c33d40297e8afb0` |

This does not cover VT switching, Xwayland, clipboard, a desktop application
suite, resize handles, sustained use, GPU reset/fault recovery,
or A733/CM5 physical GPU acceleration. It does not exercise SVG window
ornaments merely because SVG is included in the package. Fonts, SVG rendering
and package contents retain their separate acceptance records.
