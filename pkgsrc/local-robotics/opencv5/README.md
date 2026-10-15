# Shared OpenCV 5

This package provides OpenCV 5.0.0 for recorded RGB-D mapping with GCC 16.2.0.
It uses the common Eigen 5.0.1, PNG 1.6.59 and libjpeg-turbo 3.2.0 providers.
It installs shared libraries, headers, CMake targets, pkg-config metadata and
upstream license notices. OpenCV owns the algorithms.

The [feature profile](features.cmake) requests core, imgproc, imgcodecs,
features, geometry, stereo, calib, video, stitching, photo and videoio.
Upstream dependency resolution also selects flann and objdetect. The resulting
package has thirteen shared libraries. OpenCV's internal flann module keeps
its upstream namespace; PCL uses the separate common FLANN package.

PNG and JPEG use external shared providers. The profile disables GUI,
FFmpeg/GStreamer, V4L/OBSENSOR capture, OpenCL, CUDA and optional accelerator
backends. Videoio retains recorded-image and built-in file interfaces.
Hardware capture, video codec coverage and accelerated execution need their
own configuration and acceptance.

Use the ordinary [package recipe](Makefile) and its [buildlink interface](buildlink3.mk).
The [cross helper](../../../probes/media/cross-opencv.sh) takes four absolute paths:

```sh
CROSS_JOBS=2 sh probes/media/cross-opencv.sh \
  /absolute/gcc16-prefix /absolute/emberbsd-sysroot \
  /absolute/opencv-5.0.0.tar.gz /absolute/new-opencv-output
```

The sysroot must contain the coherent EmberBSD base, GCC16 runtime, Eigen,
PNG and JPEG providers. The helper checks the source archive before extraction,
applies canonical recipe patches and creates a staged install. Keep the stage,
compile commands and logs for package creation and installed-consumer checks.
A pre-existing output directory is rejected.

When reconfiguring an existing OpenCV build, pass `-DWITH_OBSENSOR=OFF`
explicitly. CMake initial-cache defaults do not replace an existing cached ON.
Check regenerated compiler commands before accepting the rebuilt libraries.

See [provenance](PROVENANCE.md) for source pins and adaptation ownership.
The [recorded-map acceptance](../../../probes/rtabmap/README.md) uses this shared
provider. Its [validation](../../../probes/rtabmap/VALIDATION.md) states which
cross, native and target checks completed. A successful library build alone
does not establish runtime or physical-device behavior.
