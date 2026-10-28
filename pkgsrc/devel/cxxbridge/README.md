# CXX bridge generator

This shared package installs `cxxbridge` and its matching `rust/cxx.h` from
CXX 1.0.205. The upstream command crate and every registry dependency are
checksum-pinned; `files/Cargo.lock` selects the current compatible versions.
The common Cargo adapter builds offline with the selected native Rust and
C/C++ tools and applies the common registry patch set. Generated bindings must
use the same CXX release as the Rust crate and installed C++ header.

Target builds produce a target executable; build-time users select a native
package. Do not run a target executable on the build host.
