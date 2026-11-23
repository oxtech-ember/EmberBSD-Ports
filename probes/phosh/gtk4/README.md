# GTK4 Wayland shared-memory compatibility

**2026-10-06: the private GTK 4.22.4 build passes shared-memory regressions
and renders GTK4 Demo and Widget Factory through Phoc/Cairo.**
It does not replace the system GTK package. The patch addresses NetBSD's
memfd mapping constraint; choosing Cairo alone does not avoid that code.

## Cause and adaptation

On NetBSD 11/aarch64 with the tested EmberBSD VirtGPU trial kernel,
GTK4 Demo calls `memfd_create`, adds `F_SEAL_SHRINK`, then sizes its
backing file to 801360 bytes. These operations succeed. Mapping those
bytes with `PROT_READ | PROT_WRITE` and `MAP_SHARED` returns `EINVAL`.
An isolated Xvfb/Phoc run reproduced the original crash with `ktrace`.

The native page size is 4096 bytes. A direct syscall probe rejects sizes
1, 4095, 4097 and 801360, but accepts 4096 and 802816. It behaves the same
with and without the shrink seal. This matches
[NetBSD kern/57622](https://mail-index.netbsd.org/netbsd-bugs/2023/09/20/msg079781.html):
memfd checks a page-rounded mapping against an unrounded file length.
This is a kernel compatibility limitation, not a renderer permission error.

The local [patch](patches/wayland-shm-page-size.patch) rounds only the
backing file length on NetBSD. It retains the requested Wayland pool
length and buffer geometry. Arithmetic uses `off_t` to avoid overflow
of GTK's signed 32-bit pool length. The patch also replaces unsupported
`%m` diagnostics with `g_strerror(errno)` so future failures report their
actual cause. It does not change kernel behavior or disable sealing.

## Build and regression

Copy the complete parent `phosh` directory to the development machine;
its native pkg-config wrapper selects the installed GLib gettext ABI.
Use a new absolute directory, with an existing parent, as an ordinary user:

```sh
sh gtk4/build.sh "$HOME/.cache/phosh-gtk4"
```

An optional second argument supplies the pinned source archive locally.
`JOBS` defaults to 2. `PYTHON` can select the installed upstream Python 3
interpreter; the default is `/usr/pkg/bin/python3.13`. Meson and GTK's
upstream generators require Python. Project-owned helpers use shell/C.
The builder verifies SHA256 and disables Meson automatic downloads.
It leaves sources, logs, regression output and installed files in the
chosen directory.

Dependencies are the pkgsrc GTK4 development stack: GLib, Cairo, Pango,
GdkPixbuf, HarfBuzz, Graphene, image libraries, epoxy, xkbcommon, X11,
Wayland, Wayland protocols, CUPS, gettext, Meson, Ninja and a C compiler.
This experimental profile enables X11, Wayland and CUPS, and disables
Vulkan, introspection generation and GStreamer media. The tested system
lacks `gstreamer-gl-1.0`; this prefix does not claim video playback support.
Cairo is the tested renderer. GPU renderers and printing are unverified.

The builder runs [test-shm.sh](test-shm.sh) against the patched source.
The test extracts GTK's actual allocation functions, then uses native
memfd and shm_open implementations. A small test-only Wayland seam
duplicates the descriptor and records the pool length; no runtime library
is substituted. Both mappings must see each other's writes, and newly
allocated bytes must be zero. Sizes cover one byte, both sides of a page
boundary, an aligned page, and actual demo/window buffers.

```sh
sh gtk4/test-shm.sh /absolute/gtk-4.22.4 /absolute/new-regression-directory
```

The original source fails five of six memfd cases on the tested kernel.
The patched source passes all six memfd and six shm_open cases.
[memfd-probe.c](memfd-probe.c) separately exposes the kernel constraint:
compile it with `cc -Wall -Wextra -O2`, then run as an ordinary user.
Its nonzero result means at least one valid byte-length mapping failed;
it is diagnostic evidence, not an expected-success GTK regression.

## Runtime check

After building, pass the GTK and Phoc prefixes to the isolated check:

```sh
sh gtk4/test-runtime.sh "$HOME/.cache/phosh-gtk4/install" \
  "$HOME/.cache/phoc-native/prefix" "$HOME/.cache/gtk4-runtime-check"
```

It starts its own Xvfb and Phoc, uses private XDG directories and D-Bus,
and checks that the loaded GTK library comes from the requested prefix.
The C client requires a mapped surface and at least two `after-paint`
signals, including a changed label. Both GTK4 Demo and Widget Factory
must exit successfully after their built-in delays and submit a Wayland
buffer. The original installed GTK4 crashes during the C client's first paint.
The helper leaves logs and removes its own X server when it finishes.
It does not connect to the user's desktop or replace its compositor.
The default X display is `:88`; it refuses an occupied socket or lock.
Set `GTK4_TEST_DISPLAY_NUMBER` to another free number when needed.
An atomic helper lock prevents concurrent use by another copy. Readiness
also requires the live X server PID to match the X display's lock owner.
No shared X11 socket or lock files are manually removed. The helper runs
Xvfb and the D-Bus/compositor tree in separate process groups. Cancellation
preserves HUP/INT/TERM exit status and bounds cleanup before escalating
from TERM to KILL. The temporary `setsid(2)` launcher is written in C.

[test-cancel.sh](test-cancel.sh) verifies cancellation while the helper's
own compositor process group is stopped. It expects status 143 and checks
that the test groups and display have disappeared within ten seconds:

```sh
sh gtk4/test-cancel.sh "$HOME/.cache/phosh-gtk4/install" \
  "$HOME/.cache/phoc-native/prefix" "$HOME/.cache/gtk4-cancel-check"
```

Its default display is `:89`; the same display-number variable can override
it. The native regression passed with the deliberately stopped group.

The fresh build and runtime check used NetBSD 11/aarch64, EmberBSD
VirtGPU trial, GCC 12.5.0 and Meson 1.11.1 on 2026-10-06. The client produced
four `after-paint` signals on a mapped 360x540 surface and reported
`GskCairoRenderer`. Both demos submitted buffers and exited normally.
The installed GTK library loaded native `libintl.so.1`, without the
conflicting pkgsrc `libintl.so.8`. These checks establish the nested
software-rendered GTK4 path, not GPU acceleration or hardware support.
The complete upstream GTK test suite was not run.

## Provenance

GTK's original archive URL and SHA256 are pinned in [sources.tsv](sources.tsv).
The copied [COPYING](LICENSES/COPYING) is unchanged from GTK 4.22.4.
GTK's original copyright and license notices remain in its sources.

The two unmodified pkgsrc patches retain their NetBSD RCS identifiers.
[provenance.tsv](provenance.tsv) pins their original URLs to pkgsrc commit
`1d0b4bfd1560971538e8ab1f3cb4648c43960c32` and records their full SHA256:

- `patch-meson.build`: NetBSD GCC 12 partial RELRO compatibility; skip
  bash completion lookup and installation, as the original patch specifies.
- `patch-gdk_wayland_gdkseat-wayland.c`: protocol button constants when
  Linux/evdev input headers are unavailable.

The page-size patch, native regression and builder are local AI-assisted
work. They have not been submitted to or accepted by GTK or NetBSD upstream.
The kernel bug link explains the compatibility issue; it does not establish
upstream acceptance of this userspace adaptation.
