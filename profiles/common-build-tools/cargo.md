# Cargo with separate host and package tools

The optional `lang/rust/emberbsd-cargo.mk` include is exported from
[cargo.mk](cargo.mk) with the stdlib-only [configuration helper](cargo-config.py).
A recipe includes it instead of `lang/rust/cargo.mk`. The upstream include still
owns crate downloads, checksums, vendoring, ordinary Cargo targets and job count.
No compiler or package is installed by the helper.

The include declares the shared `rust-bin` and Python 3.15 as native
`TOOL_DEPENDS`. It uses pkgsrc's `RUST_TYPE=native` routing so a cross package does
not acquire a target Rust compiler through buildlink. The actual `rustc` and
`cargo` paths are explicit members of `EMBER_CARGO_PREFIX/bin`. This routing is
not permission to use an unrelated compiler from the host PATH.

For native packages the prefix defaults to `TOOLBASE`, and CC, CXX, AR,
CPPFLAGS, CFLAGS, CXXFLAGS and LDFLAGS come from the selected pkgsrc configuration.
For cross packages the prefix defaults to `EMBERBSD_CROSS_HOST_PREFIX`; native
commands and flags come from `NATIVE_*`, while CC/CXX/AR and ordinary package
flags retain the target configuration. The platform profile selects Clang or an
explicit GCC alternative. The adapter does not change compiler family or retry
with another compiler.

Cross recipes must supply `EMBER_CARGO_TARGET` as the upstream Rust triple and
declare their matching target std component as a host tool/data dependency.
Native recipes may leave the target empty; configure reads it from the selected
`rustc -vV`. A supplied native target must match that host. Cross host and target
must differ. The caller still owns agreement between the Rust target, C/C++
driver, sysroot and runtime. This adapter does not qualify an arbitrary target
profile or install its standard library.

`EMBER_CARGO_HOST_CC`, `EMBER_CARGO_HOST_CXX`, `EMBER_CARGO_HOST_AR` and the four
`EMBER_CARGO_HOST_*FLAGS` variables allow a recipe to pass explicit native inputs.
`EMBER_CARGO_CONFIG` and `EMBER_CARGO_OUTPUT` default inside WRKDIR. Configuration
runs after ordinary build dependencies and wrappers have been prepared. Fetch
and checksum do not execute Rust, Python configuration or a C/C++ compiler.
Normal pkgsrc policy and source/license checks still apply.

The generated configuration uses an explicit package target even for native
builds. This preserves Cargo's separation between target Rust flags and native
build scripts/proc macros. Linker wrappers retain their command arguments and
only their side's LDFLAGS. Cargo's forced environment selects both exact and
underscore target spellings recognized by the `cc` crate, along with HOST/TARGET
and generic host variables. Since the `cc` crate ignores CPPFLAGS, those
arguments live in the C/C++ wrappers, before caller CFLAGS/CXXFLAGS. CPPFLAGS
environment entries are cleared to avoid applying options such as `-include`
twice in other build scripts. C/C++ flags retain shell quoting. The caller supplies
pkgsrc's explicit tool PATH; only the selected command is resolved, with no
fallback if it is missing. Wrapper symlinks retain their dispatch spelling.

The runner uses the generated configuration, an isolated CARGO_HOME and offline
mode. It removes the inherited RUSTFLAGS/CARGO_ENCODED_RUSTFLAGS variables after
the recipe's explicit RUSTFLAGS were captured in target configuration, because
those environment variables override Cargo's target flag tables. Undeclared
Rust compiler wrappers are rejected. `cargo install` receives an explicit target
because upstream ignores `build.target` for that command. Exit status and the
normal pkgsrc process group are preserved.

## Shared native library inputs

A recipe may pass `--build-script-overrides /absolute/links.toml` through
`EMBER_CARGO_CONFIGURE_ARGS`. This is Cargo's official
[build-script override](https://doc.rust-lang.org/cargo/reference/build-scripts.html#overriding-build-scripts),
not a replacement crate builder. The input contains tables keyed by the crate's
`links` value, for example:

```toml
[mimalloc_sys2]
rustc-link-lib = ["dylib=mimalloc"]
rustc-link-search = ["/absolute/selected-buildlink/lib"]
```

The helper places those entries under `target.<package-triple>.<links>`. Cargo
then skips that dependency's native build script. The recipe must declare the
shared library dependency and preserve its options, ABI, flags, notices and any
metadata normally produced by the skipped script. This does not itself prove
that a particular crate is compatible with the chosen shared library.

## Verification

```sh
python3 -B -I -S profiles/common-build-tools/tests/cargo-config.py
python3 -B -I -S profiles/common-build-tools/tests/cargo-pkgsrc.py \
  --pkgsrc /absolute/completed-pkgsrc --bmake /absolute/native/bin/bmake \
  --makeconf /absolute/native-mk.conf --shell /absolute/native/bin/mksh
python3 -B -I -S profiles/common-build-tools/tests/cargo-cppflags.py \
  --cc '/absolute/selected/clang -isysroot /absolute/SDK -mmacosx-version-min=26.0' \
  --cxx '/absolute/selected/clang++ -isysroot /absolute/SDK -mmacosx-version-min=26.0' \
  --ar /absolute/selected/llvm-ar --shell /absolute/selected/mksh \
  --tool-path /absolute/selected:/usr/bin:/bin
```

The first suite runs CLI and tool-wrapper fixtures for native/cross separation,
quoted arguments, explicit GCC selection, missing-input refusals, build-script
override tables and Cargo status/environment handling. The second executes the
include in a real pkgsrc view: fetch/checksum, native TOOL_DEPENDS, both configure
routes and refusal of the wrong Rust dependency role. Its cross case uses a
minimal metadata fixture because a native bootstrap profile correctly refuses
cross targets. Neither test compiles crates: Rust identity and tool execution are
explicit fixtures. The third test executes the selected C/C++ preprocessors for
both tool roles using a header directory with spaces and defines supplied only
through CPPFLAGS, with a later CFLAGS/CXXFLAGS override. Removing CPPFLAGS or its
required define must fail. It passed with the explicitly declared initial Apple
Clang, SDK and deployment inputs; only preprocessing runs, with a fixture Rust
identity. It does not execute the Rust `cc` crate or qualify a target binary.

With an installed native Rust/Clang prefix and a checksum-verified pkgsrc vendor
directory containing `cc` 1.4.6 and its dependency closure, run the actual crate
regression:

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S \
  profiles/common-build-tools/tests/cargo-cc.py \
  --host-prefix "$HOST_PREFIX" --vendor "$PREPARED_VENDOR" \
  --work "$NEW_WORK_DIRECTORY" --sdk-root "$MACOS_SDK" \
  --utility-path "$SELECTED_TOOL_PATH" --deployment-target 26.0
```

This offline, single-job check compiles the real `cc` build script, C and C++
archives, then links and runs a native Rust executable. Both languages need an
include path and define supplied only by CPPFLAGS; CFLAGS/CXXFLAGS supply the
later value of a shared define. Removing the include path or required define must
fail. Inherited compiler/archive variables are deliberately invalid, so success
also exercises Cargo's forced tool selection. The current checked route is
native Darwin with Rust 1.99.1 and Clang 23. Cross Rust execution, Cargo's skipping
of a real shared-library build script, and Rollup/mimalloc ABI and loader behavior
still require their own consumer checks.
