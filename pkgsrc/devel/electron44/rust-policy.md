# Chromium's Rust capability policy

The Electron build uses the shared stable `lang/rust-bin` 1.99.1 compiler. Its
reported release and host identity are retained; it is not relabeled as nightly.
Chromium's pinned source requires unstable compiler flags and allocator
attributes even when using a custom toolchain. Rust documents
[`RUSTC_BOOTSTRAP`](https://doc.rust-lang.org/unstable-book/compiler-environment-variables/RUSTC_BOOTSTRAP.html)
for consumers including Chromium. This is an unstable compatibility contract,
not a guarantee that future stable releases accept the same inputs.

The recipe's [policy function](files/rust-policy.py) consumes the selected
`rustc -vV` output and returns a separate producer environment with
`RUSTC_BOOTSTRAP=1`. The current supported release is exactly 1.99.1. It does
not modify the invoking environment, package recipes, compiler installation,
or other builds. The controller passes this environment only to its GN/Ninja
producer and sets `emberbsd_rust_unstable_features=true`.

The ordered source patch requires that explicit GN choice, matching stable
version and scoped environment. The GN capability boolean reflects the enabled
features; the compiler version string remains unchanged. With the option off,
custom stable compilers are not identified as nightly simply because their
minor version is newer than 1.85. Upstream nightly/dev suffixes retain their
normal capability selection.

Ordinary Chromium crates retain `-Zallow-features=`. The allocator explicitly
allows only its existing `linkage` and `rustc_attrs` features. Other upstream
exceptions retain their individual feature lists, as specified in
[`docs/rust/unstable_rust_feature_usage.md`](https://chromium.googlesource.com/chromium/src/+/dd78960ccd8a03a2fe1f629543d27783885b78e9/docs/rust/unstable_rust_feature_usage.md).
No warning, sanitizer, feature dependency check or ordinary crate restriction
is removed. Building the target Rust standard library against the selected
EmberBSD ABI remains a separate required input; the native standard library
does not substitute for it.

The regression uses actual GN with the prepared production `rust.gni` and
allocator target scope. It runs the selected stable compiler with Chromium's
real unconditional `-Z` flags, generates the allocator's FFI from its actual
C++ header using the shared bindgen, and compiles the unchanged allocator
source to a native object. Controls reject a different release, absent scoped
environment, an ordinary crate feature, an unlisted allocator feature, and
an allocator with the exception list removed. It preserves the stable version
report and caller environment. It does not link or execute Electron, build the
target standard library, or establish target runtime support.

```sh
/absolute/native-prefix/bin/python3.15 -B -I -S \
  probes/electron/tests/electron-rust-policy.py \
  --source /absolute/prepared-electron/src --work /absolute/new-rust-check \
  --git /absolute/control-git --gn /absolute/native-prefix/bin/gn \
  --rustc /absolute/native-prefix/bin/rustc \
  --bindgen /absolute/native-prefix/bin/bindgen \
  --host-prefix /absolute/native-prefix --macos-sdk /absolute/MacOSX.sdk \
  --utility-path /absolute/native-prefix/bin:/absolute/native-prefix/gnu/bin
```

This native regression currently selects Darwin ABI inputs explicitly. Run it
against the prepared source before `gn-chromium-rust-policy.patch`.
