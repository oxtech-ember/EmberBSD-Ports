# EGL platform header ownership

The source is pinned to the official KhronosGroup/EGL-Registry commit
`8e56e86e65687697ef54114cdb1afabdfac756bf`. It installs only
`api/EGL/eglplatform.h` and `api/KHR/khrplatform.h`; their embedded licenses
are Apache-2.0 and Khronos' three-clause BSD terms, respectively.

The two installed files were byte-compared with the corresponding headers in
the pinned Glad 2.0.8 source and Mesa 26.2.6 source. Both consumers copy these
provider files into their expected source/generator locations only when bytes
differ, so unchanged inputs keep their timestamps. Their public buildlink
interfaces depend on this package because those headers remain required by
installed public headers.

The pinned upstream `misc/raspberrypi-userland` package has its own copies as
part of a separate vendor SDK. This change does not claim that package can be
co-installed with the shared EGL header provider.
