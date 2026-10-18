# Current COSMIC cross-build boundary

This probe selects [COSMIC Epoch 1.10.0](https://github.com/pop-os/cosmic-epoch/releases/tag/epoch-1.10.0),
released on 2026-10-08. Its gitlinks select cosmic-comp
`41497b42d9744d9963c4c6d17e8add49489b45ee` and cosmic-session
`8093b59bb1262b0612d814e6540ba936303f735a`. The [manifest](sources.tsv)
records the original archives and SHA256 values.

Use the common stable Rust 1.99.1 host package and its matching
source-built NetBSD standard library. Target C and the Rust linker use
the common GCC 16.2.0 cross facade. The probe does not install a compiler
on the target. It does not use a nightly compiler or a target Clang.

`build.py` validates the source archive and both compilers. It extracts a
new source tree, preserves `Cargo.lock`, records the exact command and
status, and keeps complete Cargo diagnostics. Use `--mode fetch` once to
obtain the locked dependency closure. Later checks and builds are offline.
Fetch covers both the NetBSD target and the native procedural-macro host.
Use separate new work paths for fetch, check and build.

```sh
python3 probes/cosmic/build.py --component cosmic-session \
  --archive /absolute/distfiles/cosmic-session.tar.gz \
  --host-prefix /absolute/common-host --cross-tools /absolute/common-cross \
  --sysroot /absolute/common-sysroot --cargo-home /absolute/cargo-cache \
  --work /absolute/build/cosmic-session-check --mode check --jobs 1
```

The session selects upstream's supported `autostart` feature without its
optional systemd/logind features. The compositor also omits its optional
systemd feature. All unconditional Smithay DRM, GBM, EGL, libinput, libseat,
udev, winit, Vulkan, X11, Pixman and Xwayland features remain selected.
This is not a reduced replacement compositor or a claimed working session.

The locked Smithay revision starts with `e3d461a`. Its DRM sync-object code
uses Rustix `eventfd`, whose 1.1.5 platform gates omit NetBSD. The current
libc crate already declares NetBSD's real eventfd API and flags. This is a
concrete portability boundary to test after the common std is available.
Other device, udev, DRM-ioctl and session contracts require actual compile
and runtime checks. No successful no-op syscall replacement is provided.

`eventfd.c` checks the existing target kernel and libc interface. All 15
counter, nonblocking, close-on-exec flag, polling, invalid-write and
semaphore contracts pass on the AArch64 VM. The test uses the real
`sys/eventfd.h` API; it does not provide replacement calls or flag values.
Compile it with the common GCC16, target sysroot, GCC16 startup/runtime
paths, `-std=c11 -Wall -Wextra -Werror -fanalyzer`, and the usual target
RPATH. Execute the ELF on an explicit EmberBSD target.

GCC 16.2.0 path analysis passes. Cppcheck 2.22.0 checks the actual
preprocessed target source with all categories enabled. Its visible
findings treat `errno` as unchanged by the external `eventfd_read` and
`eventfd_write` calls, plus unused inline functions from system headers.
The runtime checks confirm the expected errno changes. No category is
suppressed, and this is not a clean Cppcheck result. Darwin has no native
eventfd interface, so this target-only probe has no native ASan/UBSan or
Valgrind result. The test does not qualify Rustix, Smithay or COSMIC yet.

This probe is an initial port, with AI assistance. It has no accepted
COSMIC package or compositor runtime result yet. A dependency fetch or a
successful compiler check does not prove a desktop session.
