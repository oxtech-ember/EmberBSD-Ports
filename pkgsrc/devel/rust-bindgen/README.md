# Native and cross bindgen provider

The shared recipe builds bindgen 0.73.2 from its upstream release source and
unchanged Cargo.lock. Every registry crate is declared and checksum-verified
by pkgsrc; build and install use Cargo `--locked --offline` through the shared
[Cargo adapter](../../../profiles/common-build-tools/cargo.mk).

The adapter selects the native Rust compiler and host C/C++ tools separately
from target C/C++ tools. A cross profile supplies `EMBER_CARGO_TARGET` and the
normal native/target compiler inputs. Cargo install uses the same configured
target directory and target as the build. No target binary runs during install.

The installed CLI loads libclang at runtime and defaults to rustfmt. Consumers
select the provider explicitly with `LIBCLANG_PATH` pointing to the chosen
prefix's `lib`, `CLANG_PATH` to its `bin/clang`, and `RUSTFMT` to its
`bin/rustfmt`. Set the native tool PATH and pass the intended target and sysroot
after `--`; the parser's target can differ from the host executing bindgen.
On Darwin, pass the selected SDK as `-isysroot` (or through
`BINDGEN_EXTRA_CLANG_ARGS`). This recipe does not embed build wrappers into
those runtime defaults.

`bmake test` runs the native CLI against C and C++ headers, compiles and runs a
Rust/C FFI consumer with the selected compiler/linker, and checks that an
explicit missing libclang fails. Cross test invocation refuses to execute a
target CLI on the host; cross target runtime validation remains separate.
The package preserves upstream and crate license notices and crate metadata.
