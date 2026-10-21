# Current COSMIC cross-build boundary

This probe selects [COSMIC Epoch 1.11.0](https://github.com/pop-os/cosmic-epoch/releases/tag/epoch-1.11.0),
released on 2026-10-20 at tag commit `e98f8289a22f9e612feee7d4c6ba197782db154b`.
Its gitlinks select cosmic-comp `8cb1802caada438bb5cc7670dfabdaca5fad0502`
and cosmic-session `4b0a0a24e98b9e755b6a7146e4cb29539cacda0a`.
The [manifest](sources.tsv) records the official source archives and SHA256 values.

Use the common stable Rust 1.99.1 host package and its matching
source-built NetBSD standard library. Target C and the Rust linker use
the common GCC 16.2.0 cross facade. The probe does not install a compiler
on the target. It does not use a nightly compiler or a target Clang.

`build.py` validates the source archive and both compilers. It extracts a
new source tree, applies the checked-in lockfile update, records both the
upstream and effective lockfile hashes, and keeps complete Cargo diagnostics.
Use a task-local copy of the Cargo home that contains the locked crates and
Git checkouts with Ports patches. `--mode fetch` adds the remaining locked
dependencies, including both the NetBSD target and native procedural-macro
host closures. Cargo writes downloads to that task-local home. Use separate
new work paths for fetch, check and build. Check and build make a task-local
Cargo-home overlay. It reads the downloaded caches, then applies the Ports
patches to private copies of the crates and Git checkouts. It does not modify
the supplied Cargo cache or source archives.

```sh
python3 probes/cosmic/build.py --component cosmic-session \
  --archive /absolute/distfiles/cosmic-session.tar.gz \
  --host-prefix /absolute/common-host --cross-tools /absolute/common-cross \
  --sysroot /absolute/common-sysroot --cargo-home /absolute/task-cargo-cache \
  --work /absolute/build/cosmic-session-check --mode check --jobs 1
```

The session selects upstream's supported `autostart` feature without its
optional systemd/logind features. The compositor also omits its optional
systemd feature. All unconditional Smithay DRM, GBM, EGL, libinput, libseat,
udev, winit, Vulkan, X11, Pixman and Xwayland features remain selected.
This is not a reduced replacement compositor or a claimed working session.

The Ports patches enable Rustix 1.1.5 `eventfd` through NetBSD's existing libc
interface, fix Smithay's `rand 0.10` trait import, and let `libdisplay-info-sys
0.3.0` use the ABI-compatible system `libdisplay-info` 0.4.0. The Rustix
NetBSD backend binds current `kevent` and `statvfs` layouts and symbols, and
fixes its `f_favail` conversion. `gettext-sys` `setlocale` uses the symbol
selected by the target header. The compositor patch also replaces the
deprecated atomic `fetch_update` name with its stable `try_update` alias on
Rust 1.99.1.

The target build links the shared gettext installation in the EmberBSD sysroot.
This avoids `gettext-sys`'s unsupported fallback that cross-builds bundled GNU
gettext for NetBSD while attempting to link host utilities with the target toolchain.

The upstream compositor lock pins libc `0.2.182`, Rustix `1.1.4`, and the
COSMIC softbuffer fork `0.4.1`. The checked-in lock patch updates libc to
`0.2.191`, Rustix to `1.1.5`, and softbuffer to upstream `0.4.8`. The lock
graph no longer includes Rustix `0.38.44`, DRM `0.11.1`, or `drm-ffi 0.7.1`.
The Ports patch updates DRM `0.14.1` to Rustix 1.1.5 through a local Cargo
patch override and makes its returned lifetime explicit. The session lock
already uses libc `0.2.191` and Rustix `1.1.5`. Cargo tree and offline builds
verify that the selected target graph uses only Rustix `1.1.5`. The selected
COSMIC graph has no GTK or GDK dependency.

Both 1.11.0 components cross-build for AArch64 NetBSD with the common GCC
16.2.0 and Rust 1.99.1 providers. The resulting binaries use the NetBSD
dynamic loader. The compositor build still reports a future-compatibility
warning for `proc-macro-error2 2.0.1`. The session reports two unused
callback parameters that are used only by its disabled systemd feature. No
diagnostic category is suppressed.
No package install, graphical session, DRM device, or runtime compositor
result is claimed. No successful no-op syscall replacement is provided.

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
Valgrind result.

`tests/netbsd-abi.c` checks the current NetBSD header sizes and offsets for
`struct kevent` and `struct statvfs`, then records the selected current symbols.
Rustix's target-only FFI structures have compile-time AArch64 layout checks.
Its `f_favail` conversion test uses distinct free and available inode counts.
These source and link checks do not replace a target kqueue or filesystem run.

This probe is an initial port, with AI assistance. A dependency fetch or a
successful compiler check does not prove a working desktop session.
