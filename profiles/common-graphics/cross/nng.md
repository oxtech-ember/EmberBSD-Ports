# NNG for KiCad IPC

The `net/nng` port builds NNG 2.1.0, its C headers and `nngcat`. The default shared library has SONAME `libnng.so.2`. Select the `static` package option for a static library.

The default `doc` option installs the offline upstream HTML reference and man pages. The build-host Python processes the symbol index distributed with the release. Lowdown from `textproc/lowdown` formats each chapter. Function and type names link to their chapter, so queries such as `man 3 nng_init` and `man 1 nngcat` work after installation. Set `PKG_OPTIONS.nng=-doc` to omit the reference and its build-only tools.

KiCad pairs each successful `nng_init()` with `nng_fini()`, receives owned `nng_msg` messages and closes sockets through `nng_socket_close()`. The AArch64 runtime check sent a schematic request to the actual KiCad server class over a local IPC socket, received its reply and stopped the server. [IPC check](../../../probes/kicad/nng/README.md)
