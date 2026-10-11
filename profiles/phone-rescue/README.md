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

- The gaster recipe inside a pkgsrc cross export is pending: the macOS
  host bootstrap lacks a libtool/libtoolize host package, and recipes
  that run `autoreconf` (such as `devel/libusb1`) require libtoolize on
  the wrapped tool PATH. The gap is tracked in the knowledge base.
- The same gaster source cross-compiled directly with the GCC16 cross
  toolchain (libusb 1.0.30 netbsd backend, libusb linked statically,
  base libcrypto, `-pthread`) and the aarch64 binary runs in the
  EmberBSD Tools VM: usage output confirmed on 2026-10-11.
- Next steps: add the host libtool package, finish pkgsrc packaging for
  both recipes, then validate PwnedDFU against iPhone 5S hardware
  (iPhone6,2, CPID 0x8960) with the device passed through to the VM.
