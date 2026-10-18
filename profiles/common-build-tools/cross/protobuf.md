# Common protobuf and Abseil packages

The common profile selects protobuf 36.2 and Abseil 20260817.0nb2.
Both recipes replace the pinned pkgsrc provider at its canonical path.
[Source pins](../sources.tsv) identify the official archives. Recipe `distinfo`
files record the archive and patch checksums.

The protobuf recipe keeps the existing single package boundary. It owns the
headers, shared libraries, static UPB archive, CMake/pkg-config files and target
`protoc`. It depends on the common Abseil and zlib 1.3.2 providers. Gzip stream
support stays enabled. This SDK package is not a runtime-only VM package.
Do not register a reduced payload as the complete package.

Four reviewed [source repairs](../../../probes/kicad/protobuf/README.md) release
the CLI descriptor registry after it exits and propagate UPB allocation failure
for the message, repeated field and scalar string clone paths. The recipe reuses
those public patch files through checked relative links. The exporter verifies
their origins and checksums before materializing normal pkgsrc patches.
It also keeps the two canonical pkgsrc portability patches.

Abseil keeps the five canonical pkgsrc C++ patches. Its additional CMake repair
preserves the `execinfo` dependency without embedding the build sysroot in
installed metadata. For cross NetBSD, it accepts a found `libexecinfo` only in
one of the compiler's real implicit library directories. It compares canonical
directory paths, then uses `-lexecinfo` in both the option and its generator
expression condition. A found nonstandard provider fails explicitly. Missing
`execinfo` and native builds retain the upstream optional behavior.

The next Abseil source repair selects its existing generic `backtrace`
implementation on NetBSD. Upstream otherwise selects the empty implementation
on this platform. Thread-local recursion and early-initialization guards stay
upstream-owned. The installed consumer in `tests/abseil-consumer` requires a
known string result and a nonempty bounded stack trace. This additional source
repair still requires its own before/after target execution; the earlier
protobuf consumer results did not cover stack traces.

The [common cross profile](README.md) supplies the target identity, sysroot and
CMake search modes. Build programs stay native. Headers, libraries and package
configuration files stay inside the target search roots. Native dependency
recursion receives none of these cross settings.

## Native generator for a cross consumer

Include `../../devel/protobuf/host-protoc.mk` only in consumers that generate
source files. Keep their normal protobuf buildlink dependency. The fragment
uses a genuine native `protobuf-36.2` package by default. It does not add a host
generator dependency to library-only consumers or to protobuf itself.

An already built native generator can be selected explicitly:

```make
EMBERBSD_BUILD_PROTOC=/absolute/native/bin/protoc
EMBERBSD_BUILD_PROTOC_SHA256=<verified SHA256 of that executable>
```

The pre-configure check verifies the exact hash before execution and requires
`libprotoc 36.2`. It creates no package metadata for an external executable.
The fragment sets `PROTOC_FOR_BUILD`, `PROTOC` in the build environments and
CMake's `Protobuf_PROTOC_EXECUTABLE`. A consumer that calls config-mode
`protobuf_generate()` must also pass `PROTOC_EXE` with that native executable.
Do not execute the imported target `protobuf::protoc` during a cross build.

## Checks and acceptance boundary

Run these checks with the current native Ruby, CMake and GCC16 tools:

```sh
ruby profiles/common-build-tools/tests/protobuf-export.rb NEW_PREFLIGHT_WORK
BMAKE=/absolute/bmake ruby profiles/common-build-tools/tests/protobuf-source.rb \
    EXPORTED_PKGSRC MAKECONF DISTFILES HOST_PROTOC NEW_SOURCE_WORK
BMAKE=/absolute/bmake ruby profiles/common-build-tools/tests/cmake-cross.rb \
    EXPORTED_PKGSRC MAKECONF NEW_CMAKE_WORK
ruby profiles/common-build-tools/tests/abseil-metadata.rb \
    ABSEIL_ARCHIVE TARGET_TOOLCHAIN NATIVE_GXX NEW_ABSEIL_WORK
```

The target toolchain must use the common GCC16 compiler and the audited target
sysroot. Supply any environment inputs that its toolchain file requires.
The source test needs both pinned probe archive names in `DISTFILES`.
Each helper requires a new output directory and retains commands and diagnostics.

The checks cover ordinary protobuf checksum and patch preparation, comparison
of all 3515 release files with the accepted probe, real host generator selection
and rejection cases. Abseil's actual CMake regression preserves all 216 native
pkg-config files byte for byte. The target `absl_stacktrace.pc` uses `-lexecinfo`,
and its static CMake export retains the dependency without the sysroot path.
The nonstandard-library fixture fails configuration. Common-profile checks use
real pkgsrc metadata and compiler-free CMake configuration for AArch64 and
amd64; they do not establish an amd64 compiler or runtime result.

The ordinary AArch64 Abseil configure also identifies NetBSD/AArch64 and enables
CMake cross mode with the actual GCC16 compiler. The initial unadapted package
exposed the metadata problem and is not accepted. Repaired package creation,
installed SDK consumers and target execution remain separate gates here.

The [source probe](../../../probes/kicad/protobuf/README.md) already has native
memory checks and actual AArch64 VM consumer results. Those results do not
establish acceptance of these ordinary packages. The recipes keep the original
upstream licenses and ownership. Local adaptations and tests are AI-assisted
EmberBSD work; they have not been accepted upstream.
