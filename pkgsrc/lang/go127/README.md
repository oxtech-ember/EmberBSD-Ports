# Common Go 1.27 provider

This recipe builds Go 1.27.3 from the official source archive and retains the
pkgsrc-2026Q3 Go127 recipe, installation layout, and portability patches.
The version selection in `files/pkgsrc-version.patch` applies to every export,
including the `lang/go` metapackage and consumers using `go-module.mk`.
Source: [Go downloads](https://go.dev/dl/),
[release history](https://go.dev/doc/devel/release#go1.27.3).
The source SHA256 is
`6e7749035cf360f06b2575d162ea79df9fda8ef671889e5c375f8e50777f26bb`.
Go retains its upstream BSD license. The recipe changes and regression are
local, AI-assisted EmberBSD work; they have not been submitted upstream.

## Native bootstrap and compiler selection

Pass `GOROOT_BOOTSTRAP=/absolute/native-go-tree` to the ordinary pkgsrc build.
An installed `${TOOLBASE}/go127` is reused by default. Otherwise the recipe
adds a tool dependency on `lang/go-bin` and builds with `${TOOLBASE}/go-bin`.
That recipe installs the official upstream binary release of the same Go
version for the build host. Its `distinfo` records each supported host
platform, so the seed is fetched and verified through the ordinary pkgsrc
fetch. The SHA-256 values published at https://go.dev/dl/ were compared with
the fetched archives. The seed must execute on the build host; Go 1.27 requires
at least 1.24.6. No older `go-bin` or compiler chain is selected.

The recipe passes pkgsrc's `MAKE_ENV` and `TEST_ENV` to upstream build/test
scripts, preserving the selected `SDKROOT`. Native builds use `CC` and `CXX`;
cross builds use `NATIVE_CC` and `NATIVE_CXX` for host programs and `CC`/`CXX`
for `CC_FOR_TARGET`/`CXX_FOR_TARGET`. These are full commands, preserving
explicit compiler, linker, ABI, and sysroot arguments. Select native and target
inputs independently through the existing pkgsrc configuration. `GOENV=off`
and `GOTOOLCHAIN=local` prevent persistent user settings or automatic Go
toolchain downloads from changing the build.

`MAKE_JOBS` controls the upstream `GOMAXPROCS` budget for both build and test.
Use the ordinary `build`, `test`, and `package` targets. Native cgo tests need
the selected host C/C++ compiler and ABI SDK. Cross-built Go still requires
execution tests on its target before it can be accepted for that target.

## Regression

`tests/native-routing.py` executes the real pkgsrc `do-build` and `do-test`
targets with an environment capture in place of the upstream script. It checks
native compiler commands, SDKROOT, bootstrap identity, and toolchain policy.
It evaluates the same build-environment fragment with distinct host/target
commands and checks missing, wrong-architecture, and too-old seed refusals.
Source metadata, fetch, and checksum work without a seed; cross test execution
is explicitly refused on the build host. This is a routing regression; it does not compile Go or establish runtime
behavior. Pass an exported tree, its native make configuration, and explicit
`--bmake`, `--shell`, `--seed`, and `--pkg-admin` paths:

```sh
python3 -B pkgsrc/lang/go127/tests/native-routing.py \
    --pkgsrc /absolute/export --makeconf /absolute/native.mk.conf \
    --bmake /absolute/prefix/bin/bmake --shell /absolute/prefix/bin/mksh \
    --seed /absolute/native-go-tree --pkg-admin /absolute/prefix/sbin/pkg_admin
```

Consumers compile Go source against this common provider. Version updates
require rebuilding affected Go programs; this provider alone does not prove
Dawn generators, TypeScript, or target applications work.

The Darwin arm64 validation built the source package with Ports Clang/LLD
23.1.4 and macOS SDK 27.0. A staged Go module linked a C++ `std::string`
consumer and returned the independently expected result `42`; missing C++
compiler and linker inputs failed. That consumer excluded the package work
wrappers and used permanent native compiler commands plus the shared utility
mapping. The default `go env CC CXX` values contained no temporary paths.
`go test -json -short -count=1 runtime runtime/cgo cmd/cgo/internal/test
cmd/cgo/internal/testcarchive cmd/cgo/internal/testcshared` completed with
1,342 passing and 124 skipped test events. The short mode and platform skips
remain limits; this is not the complete upstream suite or target execution.
