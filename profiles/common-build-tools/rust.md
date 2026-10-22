# Shared Rust 1.99 build-host provider

The common profiles export `lang/rust-bin` 1.99.1nb2 for the build-host compiler
needed by current cargo-c and librsvg. The archive is the official Rust release;
this step does not compile another rustc or LLVM. Native and target components
remain distinct: a macOS compiler needs a compatible NetBSD target std before
it can build NetBSD Rust consumers.

## Recipe provenance and adaptation

The binary recipe is based on pinned pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b` and
[pkgsrc-wip rust199-bin at 7d3133f](https://github.com/NetBSD/pkgsrc-wip/tree/7d3133f21d6d918d9f2e62b708f3583c40120343/rust199-bin).
The upstream installer is unchanged. `distinfo` preserves the published
BLAKE2s/SHA512 checksums and sizes; the tested Apple Silicon archive has an
additional official SHA256 pin in [sources.tsv](sources.tsv).
The recipe does not advertise NetBSD i386/mipsel or SunOS, for which this
import has no active archive selection and matching checksum.

Revision nb2 gives the two bundled Darwin LLVM providers the private basename
`librustLLVM.dylib`. It changes their install IDs and every actual import from
`@rpath/libLLVM.dylib` to `@rpath/librustLLVM.dylib`. The upstream runpaths and
their order stay unchanged. The shared LLVM package keeps its own names.
The helper checks all Mach-O slices in `bin`, `lib` and `libexec`. It refuses
unexpected provider layouts, differing provider bytes, existing private names
and shared hard links before it writes. Each changed image gets an ad hoc
signature and a strict signature check. No compiler is rebuilt.

The inherited post-install script expanded `@rpath` into an absolute package
prefix. This can exceed a prebuilt library's load-command space. Revision nb1
removed that expansion. It retained a second problem: the Rust distribution
and the common LLVM package both owned `lib/libLLVM.dylib`, so normal package
installation refused their collision. The private basename fixes that ownership
conflict without replacing common LLVM. Non-Darwin `patchelf` behavior remains
unchanged. Python is a Darwin build-only dependency for this helper.

The recipe also opts into `MACHO_USE_LOAD_COMMANDS=yes` in the exported pkgsrc
infrastructure. The old `otool -L` metadata includes a dylib's own install ID
and leaves `@rpath` unresolved. Consequently `pkg_add` rejects an otherwise
working staged Rust installation as missing its own libraries.
The opt-in checker reads actual imports with `otool -l`, separately for each
architecture, and resolves the image's local runpaths in order. A candidate
must exist and contain the importing architecture. The same code supplies
both package requirements and explicit shared-library checks. Staged providers
remain package-owned; external pkgsrc providers must be runtime dependencies.
The default checker remains unchanged for recipes that do not opt in.

This static check does not reconstruct inherited loader runpath chains.
Unresolved paths fail explicitly. It covers the official Rust distribution's
own runpaths, including its universal sanitizer libraries. The ordering follows
[Apple's runpath documentation](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/RunpathDependentLibraries.html).

This is an EmberBSD adaptation with AI assistance, not an upstream-accepted
change. Re-evaluate it when the upstream recipe changes. The helper preserves
loader-relative paths and checks each rewritten signature.
It does not claim that a native compiler check validates target execution.

## Build and verify

Prepare a common profile with [the normal exporter](README.md#prepare-and-select).
Use the existing native macOS pkgsrc configuration and shared host prefix,
with a separate work directory and the verified distfile cache. Do not include
the native NetBSD compiler-selection profile in this host build.

```sh
MAKECONF=/absolute/native-mk.conf bmake -C /absolute/pkgsrc/lang/rust-bin \
  WRKOBJDIR=/absolute/work DISTDIR=/absolute/distfiles MAKE_JOBS=2 \
  CHECK_SHLIBS=yes package
```

Keep normal pkgsrc checks enabled. For post-install changes, use a clean
staging directory: this recipe intentionally removes installer manifests after
staging, so invoking upstream's install script over that previous staging tree
cannot uninstall its old components. Preserve the failing log and package.
A package revision change can also invalidate pkgsrc's existing work state.
When changing pkgsrc infrastructure in a retained work tree, invalidate its
cached `+BUILD_INFO` and `+BUILD_VERSION` before packaging again. `repackage`
alone can retain those old records. Inspect both the package metadata and a
normal installation; a successful staged compiler alone is insufficient.

Run the regression against a verified upstream component installation and the
new package's staged prefix before installing it:

```sh
python3 -B tests/rust-darwin.py /absolute/original-rust \
  /absolute/staged-prefix /absolute/pkgsrc /absolute/new-check
```

The regression reads the real runtime Mach-O graph. The tested Apple Silicon
layout contains 43 images, two byte-identical LLVM providers and 24 actual LLVM
consumers. It compares every architecture, install ID, import and runpath before
and after the helper. Both private providers and all changed consumers must
pass strict signature checks. Each restored generic import must fail against
a foreign generic LLVM sentinel. Removing either private provider must also
fail its real consumer. A real unrelated dylib in `DYLD_LIBRARY_PATH` is
ignored under the generic basename. Under the private basename it must fail
with a missing LLVM symbol. The check preserves both inputs and reproduces
the old absolute-name overflow on a disposable library.

The staged compiler builds and runs the native allocation/thread/TLS/unwind
consumer. Rust tools and the bundled LLVM assembler, verifier, disassembler
and linker run from the relocated prefix. The real pkgsrc load-command checker
must resolve both private providers. Normal runs have no loader override.
The runtime trees come from upstream component manifests; documentation files
are neither copied nor scanned as executable inputs. These checks do not
register a package, establish memory-leak acceptance or execute target code.

Check the fresh-stage refusal separately with a real partial import rewrite:

```sh
python3 -B tests/rust-darwin.py --mixed-preflight /absolute/original-rust \
  /absolute/new-preflight-check
```

It changes only the import of the upstream `rustfmt` in a private clone.
Both original LLVM providers and the mandatory rustc/driver imports remain.
The helper must refuse the mixed graph before any rename or byte change.
Removing only the guard must reach the first rename. The witness intercepts
that boundary before mutation; its graph inspection remains real.

Run the Mach-O regression on macOS with the exported pkgsrc tree:

```sh
ruby tests/macho-load-commands.rb /absolute/pkgsrc /absolute/new-macho-check
```

It builds and runs real consumers, checks self-ID exclusion, universal images,
bare and relative loader/executable paths, and the architecture fallback order.
Missing libraries/runpaths, wrong-architecture providers, build-directory
references and undeclared or build-only package owners must be diagnosed.
The dependency-owner fixture uses a controlled pkg_info response; it does not
register fake packages. The legacy resolver remains a causal negative control.

Revision nb2 passed normal package creation and installation beside the registered
common LLVM package. A complete archive-to-prefix readback checked all 66,170 payload
entries, their bytes, modes and links, and the registered package metadata.
The metadata records the new recipe and both private provider names.
The installed compiler also passed the native allocation/thread/TLS/unwind
consumer. All 26 changed images passed strict signature checks. A real loader
trace selected the private LLVM provider. Common LLVM state and protected build
tools stayed unchanged. This accepts the Darwin build-host package; target
execution and memory-leak checks remain separate.

All six export modes previously passed composition checks, including refusal
when the Mach-O infrastructure patch was absent.

Use normal `bmake install` after acceptance. Native Rust consumers explicitly
select `RUST_TYPE=bin`; otherwise the pinned pkgsrc tree defaults to its older
source compiler. Do not install a separate compiler for cargo-c or librsvg.
The existing `devel/cargo-c` 0.10.25 recipe supplies its checksummed crate closure
and uses the installed host OpenSSL provider.

The common cross profile also defaults to `RUST_TYPE=bin`. Cargo build tools
then use the shared build-host provider instead of requesting pkgsrc's
source-built Rust and LLVM runtime. Package recipes can select another mode
when they have a tested host/target contract. Verify the exported selection
against the real pkgsrc consumer:

```sh
python3 tests/rust-cross-selection.py /absolute/pkgsrc \
  /absolute/cross-mk.conf /absolute/host/bin/bmake \
  /absolute/new-rust-cross-selection
```

The check removes any explicit `RUST_TYPE` assignment from the supplied
MAKECONF, then queries `devel/cargo-c` and the explicit `graphics/librsvg`
override. It requires the `rust-bin` provider for Cargo and preserves
`librsvg`'s native-tool selection.

It builds and installs with the shared Rust on macOS/Apple Silicon, with
`CHECK_SHLIBS=yes` and OpenSSL 3.6.5. The source archive does not ship
Cargo.lock; the offline build resolves only the recipe's pinned vendored crates.
Use the same native MAKECONF and separate work directory:

```sh
MAKECONF=/absolute/native-mk.conf bmake -C /absolute/pkgsrc/devel/cargo-c \
  WRKOBJDIR=/absolute/work DISTDIR=/absolute/distfiles MAKE_JOBS=2 \
  RUST_TYPE=bin CHECK_SHLIBS=yes install
ruby tests/cargo-c.rb /absolute/host-prefix /absolute/new-cargo-check
```

The offline consumer runs cbuild, ctest and cinstall, generates a C header and
pkg-config record, executes one Rust unit test, and links/runs a C consumer.
Its load commands must name the installed test library; the build-host
providers remain unchanged. This is native build-tool acceptance, not target
librsvg or target std package acceptance.

## NetBSD target boundary

The official compiler's private LLVM 23.1.1 backend is part of this upstream
binary distribution. It is not the target shared LLVM 23.1.2 provider used by
Mesa and is not rebuilt here.

The [target std package](rust-target-std.md) now installs the same-compiler
source build into this shared host sysroot. Normal package integrity and
AArch64 VM consumers pass TLS, unwind, C `dlopen`, and a Cargo target built
with a macOS proc macro and build script. Host Rust/LLVM bytes are unchanged.
An additional native host-data recipe imports the official x86_64 NetBSD std
component. Source/ELF fixtures pass; real host metadata acceptance and target
consumers remain pending. It shares the same Rust 1.99 compiler package.
Full librsvg/GIR/pixbuf, labwc surfaces/input/VT and an installed NetBSD
compiler remain separate acceptance steps.
