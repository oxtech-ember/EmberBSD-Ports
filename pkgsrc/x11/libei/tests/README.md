# libei source and compiled target checks

Origin: EmberBSD (AI-assisted). Upstream owns the libei and munit tests.

The `nb1` recipe retains the complete C and C++ test build. Its Meson patch
requires the target C++ compiler without probing a build-machine compiler.
It uses `cpp_args` so both C++ consumers actually include the public headers.
The previous cross configuration omitted these consumers after trying to run
an AArch64 compiler probe on macOS. Check the real `compile_commands.json`
for both C++ outputs and their `INCLUDE_LIBEI` / `INCLUDE_LIBEIS` definitions.

`patch-test_buildtest.cc` declares `std` with `<cstddef>` after the libei
headers. Clang rejects the upstream `using namespace std;` under `-Werror`
when nothing has declared `std`. Run
`BMAKE=bmake sh pkgsrc/x11/libei/tests/cxx-buildtest.sh PKGSRC MAKECONF`;
it compiles both header checks with the recipe's C++ compiler.

## Safe arithmetic regression

The protocol length helper must reject values that cannot fit after adding
the length field and alignment. The runtime patch returns the existing
protocol error before allocating or copying a string. It changes no valid
wire format and no public ABI.

```sh
HOST_CC=/absolute/native/clang ruby \
    pkgsrc/x11/libei/tests/length-arithmetic.rb \
    /absolute/upstream/src/brei-shared.c /absolute/patched/src/brei-shared.c \
    /absolute/new-arithmetic-results
```

This check extracts the actual helper from each source. It performs only
integer arithmetic with small values and the representable length boundary.
It does not allocate large buffers, create protocol messages or open sockets.
The original helper must return test status 1; the patched helper must return
status 0. Both runs use ASan/UBSan. The same boundary cases extend the existing
upstream `test_brei_string_proto_length` unit test.

The standalone helper passes Cppcheck 2.22 and Clang 21 Static Analyzer.
Valgrind is unavailable on the macOS/arm64 build host; the ASan/UBSan check
is not a Valgrind pass. See [the full source-analysis scope](source-analysis.md).

## Prepare existing upstream test binaries

Build the `nb1` recipe normally before preparing this bundle. No code is
compiled by this preparation tool or on the target.

```sh
READELF=/absolute/cross/bin/aarch64--netbsd-readelf ruby \
    pkgsrc/x11/libei/tests/prepare.rb \
    /absolute/libei-1.6.0 /absolute/emberbsd-sysroot /absolute/new-bundle
```

Use `ruby tests/host-controls.rb /absolute/new-host-results` from the recipe
directory to check preparation failures. These controls preserve existing
archives and dangling final links. They check cleanup after a missing input.
The root guard runs with a fixture for `id -u`; this is not a privileged run.

The input source directory must contain the real Meson `output` directory.
Preparation requires nine compiled upstream binaries and both C++ header
checks. It rejects missing binaries, wrong ELF architecture and an interpreter
other than `/libexec/ld.elf_so`.

The bundle contains the three built libraries, their non-base shared-library
closure, source licenses, protocol XML/DTD fixtures and SHA256 hashes.
The C tests create their other fixtures internally. The matching EmberBSD
base supplies libc and other base libraries; their reference hashes are recorded.
The bundle does not replace base libraries or install packages.

Extract the archive into a private directory on the matched EmberBSD AArch64
target. The runner rejects UID 0 before creating a result directory.
Run as an ordinary user with base `sh`, `timeout`, `sha256` and `ldd`:

```sh
sh /absolute/bundle/run.sh /absolute/new-target-results
```

The runner verifies hashes, uses private HOME/TMP/XDG directories and supplies
no existing session or system D-Bus address. Each invocation has a timeout
and a forced-kill grace period. It records all exit statuses and fails if any
invocation fails. It runs four unit binaries, both eierpecken modes and four
C/C++ build consumers. Build consumers only establish header and link coverage.

A supported target with Valgrind can run `run.sh NEW_RESULTS valgrind`.
This uses full leak checks, origin tracking and a nonzero error status.
The SIGALRM mode is excluded as required by upstream's Valgrind setup.

Python portal/scanner tests, a live portal and compositor input remain separate.
Preparing the bundle does not establish target execution or Plasma acceptance.
