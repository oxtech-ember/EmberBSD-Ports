# Qt Multimedia CPU cross build

This profile builds Qt 6.12.0 for the EmberBSD amd64 ABI with GCC 16.2.
It uses the common FFmpeg 9 provider. The display backend is the Qt VNC
platform plugin. The application renders decoded video with QWidget and
QPainter. It does not require a GPU, X server, or a low-level audio backend.

The matching example is
[`media/qt-four-streams`](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/media/qt-four-streams).
It starts four QMediaPlayer instances and checks actual decoded pixels,
timestamps, window exposure, distinct paints, and process CPU time.
Its RFB client independently reads the window framebuffer.

## Inputs

Use a coherent EmberBSD amd64 base and development sysroot. Use its matching
GCC 16 runtime and cross compiler. Do not replace the EmberBSD kernel, libc,
or headers with another operating system's files.

Install the current common FFmpeg 9, x265, GLib, PCRE2, and libffi providers
in that sysroot first. Keep their package receipts and inventories.
The source pins are in the existing common graphics, common media, and
Plasma toolkit `sources.tsv` files. `native-sources.tsv` adds the current
libsndfile source for the native Linux PulseAudio control.

The build host needs CMake, Ninja, Meson, pkg-config, GCC 16, Ruby, GNU patch,
tar, and the upstream build prerequisites. Meson and the upstream GLib code
generators use Python. The profile's own programs and scripts use C, C++,
Ruby, and shell.

## Build

All paths passed to `build-sdk.rb` must be absolute. The following variables
name caller-selected directories:

```sh
# Native Linux dependencies and matching Qt host generators.
COMPONENTS=png,freetype,harfbuzz,sndfile,pulse,qtbase,qtshadertools,qtmultimedia \
NATIVE_MEDIA_PREFIX="$native_media" \
NATIVE_PKG_CONFIG_LIBDIR="$native_pkgconfig_dirs" \
MESON="$native_meson" JOBS=2 \
ruby ./build-sdk.rb native "$distfiles" "$work" "$native_prefix"

# Target code is never run on the build host.
GCC_PREFIX="$cross_gcc" HOST_GLIB_PREFIX="$native_media" \
MESON="$native_meson" JOBS=2 \
ruby ./build-sdk.rb amd64 "$distfiles" "$work" "$stage" \
  "$sysroot" "$native_prefix/qt6"
```

`NATIVE_PKG_CONFIG_LIBDIR` must include the native profile, current common
media, FFmpeg 9, and required host system pkg-config directories.
`HOST_GLIB_PREFIX` provides the matching native `glib-mkenums` and
`glib-genmarshal`. `GCC_PREFIX` contains `bin/x86_64--netbsd-gcc` and G++.
`COMPONENTS` selects an ordered subset for a resumed build. The default
contains the six target components. The `pulse` component is native only.

The builder checks archive SHA256 and canonical recipe patch SHA1 values.
It applies patches with zero fuzz. A source fingerprint prevents reuse
after an input patch changes. Use a new work directory for changed inputs.
Each component retains the complete command log, source fingerprint, and
installation receipt. The target stage is also copied to the caller's
development sysroot. Use a private snapshot until target acceptance passes.

This is an explicit CPU and raster selection. It does not replace the full
desktop Qt package configuration or its package list. Audio, GStreamer,
OpenGL, QML, hardware decoding, and physical display drivers need separate
acceptance. Upstream Qt licenses apply to Qt. Keep upstream license and
notice files with redistributed binaries.
