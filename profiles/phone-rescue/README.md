# Phone rescue profile

Host tools that give unsupported Apple phones a second life with EmberBSD.
The entry point is checkm8: the boot ROM exploit puts an A5-A11 device into
PwnedDFU over USB, and the host then loads alternative boot images in RAM.
Device storage stays untouched during exploitation.

## Contents

- `pkgsrc/local-phone/gaster` — the checkm8 PwnedDFU helper (Apache-2.0,
  upstream pinned by commit `7fffffff38a1bed1cdc1c5bae0df70f14395129b`).
  The boot ROM payload headers are pre-generated under `files/`, so builds
  need no vim/xxd tool. The recipe builds the portable libusb backend
  against `devel/libusb1` (upstream `netbsd_usb.c` backend) and base
  OpenSSL.

## Status (2026-10-11)

- Host Libtool gap closed on 2026-10-12: the macOS bootstrap owns native
  `libtool-base-2.6.2` and `m4-1.4.21` built from the same pinned export.
  `devel/libusb1` builds and packages through its standard recipe with
  `autoreconf -fi`; `pkgsrc/local-phone/gaster` builds and packages the
  same way against the sysroot-installed libusb1. `tests/host-libtool.sh`
  in common-build-tools gates the host side. GCC16 `-fanalyzer` and
  cppcheck report no findings for gaster sources.
- The packaged `gaster-20230202` and `libusb1-1.0.30nb1` install with the
  stock `pkg_add` in the EmberBSD Tools VM; `gaster` prints its usage from
  `/usr/pkg/bin`. This closes packaging acceptance; it does not verify a
  device.
- Next step: validate PwnedDFU against iPhone 5S hardware
  (iPhone6,2, CPID 0x8960) with the device passed through to the VM.
