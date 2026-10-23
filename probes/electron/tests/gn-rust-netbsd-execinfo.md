## NetBSD Rust standard-library link dependency

Chromium's pinned Rust standard library declares `execinfo` for NetBSD.
`build/rust/std/BUILD.gn` must pass that library to C++ final links that depend
on Rust targets. Apply `gn-rust-netbsd-execinfo.patch` after
`gn-rust-version-netbsd.patch` in the Electron source patch sequence.

Run the bounded regression with host CPython 3.15 and SDK API 1:

```sh
python3.15 -B -I -S probes/electron/tests/gn-rust-netbsd-execinfo.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --ports-root /absolute/Ports \
  --source /absolute/chromium/src \
  --patch /absolute/Ports/probes/electron/patches/gn-rust-netbsd-execinfo.patch \
  --workspace /absolute/amd64-sdk-workspace \
  --sysroot /absolute/amd64-sdk-workspace/sysroot \
  --target-cxx /absolute/GCC16-x86_64--netbsd-g++ \
  --cppcheck /absolute/cppcheck \
  --clang /absolute/pinned-host-clang \
  /absolute/NEW_RUST_EXECINFO_WORK
```

The test checks the production GN library list, strict patch application,
and a GCC16 NetBSD x86_64 C++ final-link probe with and without `libexecinfo`.
It holds a shared SDK sysroot read lease and records an SDK JSON receipt.
Cppcheck and Clang Static Analyzer inspect the bounded fixture with target
headers. This test does not build Chromium's Rust standard library, link the
full Electron target, or execute target code.
