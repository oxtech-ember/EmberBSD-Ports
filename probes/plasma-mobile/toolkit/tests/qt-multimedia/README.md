# Installed Qt Multimedia player check

This is a finite software-decoding check of the complete Qt Multimedia 6.12
package on EmberBSD/AArch64. It uses the common FFmpeg 9.0.2 provider and the
installed FFmpeg plugin. No hardware codec or display-output claim follows.

Build with the same native generators and target sysroot as the other toolkit
consumers. All compilation takes place on the development host:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
PKG_CONFIG=/absolute/native/pkgconf \
sh build.sh CROSS_TOOLS SYSROOT HOST_QT NEW_BUILD
```

From the Ports root, prepare four changing YUV420 frames and a lossless movie
with a verified native FFmpeg:

```sh
ruby profiles/common-media/tests/x265-fixtures.rb prepare NEW_FIXTURES
ffmpeg -nostdin -hide_banner -v error -f rawvideo -pixel_format yuv420p \
  -video_size 64x64 -framerate 1 -i NEW_FIXTURES/frames.yuv \
  -frames:v 4 -an -c:v ffv1 NEW_FIXTURES/frames.mkv
```

Copy the consumer, frames and `run.sh` to a board with the complete package
and dependencies installed. Run there:

```sh
sh run.sh BINARY MOVIE YUV NEW_RESULTS
```

The runner selects FFmpeg, disables hardware decoder selection and uses the
Offscreen QPA. It creates a private runtime directory, caps process lifetime,
and compares the boot identity. The consumer reads actual `QVideoSink` frames
from `QMediaPlayer`, maps all three planes and checks every active pixel row
independently of stride. It requires four increasing timestamps and end of
media. The runner repeats the process, rejects one deliberately wrong pixel
and requires a missing file to produce a player error with zero frames.

`libraries.sha256` inventories actual loaded package files. Compare these hashes
with the selected sysroot after copying results back. No private address, target
path or binary result belongs in Git.

## Accepted CM5 result, 2026-10-12

The complete Qt Multimedia 6.12.0nb1 and Quick3D 6.12.0nb1 packages pass ordinary
pkgsrc checks and installation. Multimedia retains FFmpeg, GStreamer,
PulseAudio, Quick and spatial-audio modules. Its manifest follows Qt 6.12's
renamed internal modules and added headers. FFmpeg and DMA-BUF entries retain
feature/platform selection; no component was removed to pass packaging.

Quick3D requires native Timeline and the Assimp importer as described in the
[host guide](../../cross/README.md#native-generators). The target recipe keeps
canonical `lightmapviewer.qmltypes` metadata during cross builds and adds the
four new private headers. Its package is installed; target Quick3D scenes and
spatial audio have not been accepted by this player test.

On CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B, both processes check
all 24,576 YUV bytes in four 64×64 frames. Timestamps are 0, 1, 2 and 3 seconds.
Wrong pixels exit 3; a missing file yields `QMediaPlayer::ResourceError`.
All 111 loaded package-library hashes match the common sysroot. Package checks
cover 2,051 files across Multimedia, Quick3D, Timeline and Assimp 6.0.5.

The fan/V3D kernel remains `EMBERV3DRENDER #0`, source
`ab6f88f04ca73c6958adb39d0e1c717f629e7901`, SHA256
`c8600af1c6a31404fe6b3a3995196a910efda594c708194369925adb54ff1886`.
Boot identity is unchanged during the bounded run; firmware and carrier-board
revisions are unknown. Full Plasma, GPU video decoding, physical audio and
HDMI remain unaccepted.

Cppcheck 2.22 passes using the real CMake compilation database. One local
suppression preserves the required non-const `dl_iterate_phdr` callback type.
GCC16's analyzer compilation also passes. Direct analysis of fully preprocessed
Qt headers failed parsing and is not counted. Valgrind was unavailable.

| Artifact | SHA256 |
|---|---|
| Qt Multimedia 6.12.0nb1 | `8eb30d306a43f56300ae02b2122c1d3d2c6034c968e15dd75d0fc0a47bc723af` |
| Qt Quick3D 6.12.0nb1 | `fa5703ceff6a1e819cc360cf08703345d6d499849a417e99a1b65ef23399ca11` |
| Player results | `f1a3fe6c3e461ad2225395f15726fefbdba135dddd3d0082f406f065e9586d0c` |

API references: [QMediaPlayer](https://doc.qt.io/qt-6/qmediaplayer.html),
[QVideoSink](https://doc.qt.io/qt-6/qvideosink.html),
[QVideoFrame mapping](https://doc.qt.io/qt-6/qvideoframe.html#map).
