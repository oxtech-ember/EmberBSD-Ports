# OpenCV Python module and numpy

This probe records native packages of the OpenCV 5 Python module (`cv2`)
and numpy for EmberBSD amd64. A stereo camera calibration tool set uses
them: ChArUco detection (`cv2.aruco`), `calibrateCamera`, `stereoCalibrate`,
`stereoRectify`, `undistortPoints`, `remap`, image files and numpy linear
algebra. It needs no GUI and no video I/O. The record is AI-assisted
(Claude Code, Claude Opus 5.5).

## Recipes

- `graphics/opencv` and `graphics/opencv-contrib` 5.0.0. The one `cv2` comes
  from `graphics/opencv-contrib`. ArUco is in `objdetect`, so no extra
  contrib module is necessary for it.
- OpenCV 5.0.0 removed `opencv-caffe.proto`, but `modules/dnn` still
  includes the old generated `opencv-caffe.pb.h`. With the external protobuf
  (`PROTOBUF_UPDATE_FILES=ON`), nothing generates that header and `dnn`
  does not compile. `patch-modules_dnn_protobuf__io` backports upstream
  commit [f7ad23157f](https://github.com/opencv/opencv/commit/f7ad23157f1b99b59bc9a706e9c7e4c8394947ac);
  the `pre-patch` target removes the deleted Caffe files. Both packages
  use this patch. `profiles/common-build-tools/tests/opencv-dnn-protobuf.sh`
  checks the recipe and a patched `WRKSRC`; it fails on the 5.0.0 source.
- The `graphics/opencv` PLIST adds the `ptcloud` module. `cv2.so` needs
  `libopencv_ptcloud.so.500`, so users require `opencv>=5.0.0nb3`. The
  bundled clapack licence is listed except on Darwin, where OpenCV uses
  Accelerate. A Darwin build was not run for this change.
- `math/py-numpy` 2.5.3 replaces the upstream recipe to add the `blas`
  option. The option is on by default and keeps the upstream behavior:
  numpy links a BLAS and LAPACK package and needs a Fortran compiler.
  Without the option, numpy uses its internal `lapack_lite` routines. They
  are slower, but they need no BLAS package and no Fortran compiler. The
  numpy `buildlink3.mk` gives BLAS to numpy users only when the installed
  numpy (or, before installation, the recipe) has the option.
  `profiles/common-build-tools/tests/numpy-blas-option.py` checks the
  default, `blas` and `-blas` with the real pkgsrc graph. It fails on the
  upstream recipe and on a lookup that ignores the installed package.

## amd64 native GCC16 packages

Built on 28 October 2026 in the shared native amd64 GCC16 package root of
the development host (24 CPUs). That root has no Fortran compiler, so numpy
is built without BLAS. The GUI is not necessary:

```make
PKG_OPTIONS.opencv=	-gtk
PKG_OPTIONS.py-numpy=	-blas
```

The root keeps its pkgsrc export from 21 October. The recipes of this
change and their changed dependencies (`devel/abseil`, `devel/protobuf`,
`graphics/openexr`, `graphics/OpenJPH`) came from Ports main. OpenEXR
requires CMake 4.4.4, so the root's CMake was updated to 4.4.4 with
`profiles/common-build-tools/patches/pkgsrc-cmake-current.patch`. Python is
the root's 3.15.0.

| Package | Build time | SHA256 |
| --- | --- | --- |
| `py315-numpy-2.5.3nb1` | 89 s | `7a769662263952145e8ee250a609f2b7baf577dc44c72626f958ef5f16c64fd2` |
| `opencv-5.0.0nb3` | 273 s | `192794d0c7afa978342887aa955683870a91238400e3364013df1800e1b942bf` |
| `opencv-contrib-5.0.0nb3` | 343 s | `eacaaef37f135adefe47e4b5e14f8e910efb4bddd286dad9891616c304347649` |
| `protobuf-36.2` | | `ab4ae17e491a59c549a1a96ff687cfd75a3dffd96fe16f79ba47f643a00179d4` |
| `abseil-20260817.0nb2` | | `10bcab5600db0dd776032c6c402de6e68fefef4fd22aca82885691d4bebf5eb6` |
| `openexr-3.5.2` | | `c1ff10622ee12d8c7faadcfb8162c5e4b0984c87468eff2d9016064d9c5d2f5d` |

The PLIST checks of all packages pass with `PKG_DEVELOPER=yes`. The
three recipe tests above and `opencv-cv2.sh` with the installed `cv2`
pass in the root.

## Calibration tool run

The tool set rendered 30 synthetic ChArUco frames per camera and 40 stereo
pairs from a seeded model, then calibrated the cameras and the pair. The
same tool revision ran on macOS arm64 with the OpenCV 5.0.0 and numpy 2.5.4
Python wheels:

| Result | EmberBSD amd64 | macOS arm64 wheels |
| --- | --- | --- |
| Camera RMS, left and right | 0.278 px, 0.317 px | 0.278 px, 0.317 px |
| Stereo RMS, pairs | 0.363 px, 37 | 0.363 px, 37 |
| Vertical error after rectification, 95 % | 0.344 px | 0.345 px |
| Disparity spread over the frame | 5.624 px | 5.597 px |
| Rotation error | 604 µrad | 617 µrad |
| Wall time | 58 s | 8.4 s |

The board image (5905 x 5905 px) has the same pixels on both hosts.
The development host CPU runs at 2.3 GHz. Most of the extra time is system
time; one or four OpenCV threads do not change it.

## Remaining

- AArch64 packages: a cross build of numpy and `cv2` with the common Clang
  profile, and a run on a target.
- numpy with BLAS when the native set has a Fortran compiler (Flang).
- Upstream tests: the numpy test dependencies need Rust, which this root
  cannot build; the OpenCV tests need the `opencv_extra` data.
- A Darwin build of the changed OpenCV PLIST.
