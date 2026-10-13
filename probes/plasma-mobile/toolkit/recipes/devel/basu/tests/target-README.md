# Compiled basu local unit tests

Origin: EmberBSD, AI-assisted packaging. The test binaries and their test cases
come from basu 0.2.1. The prepared build uses the EmberBSD Ports nb2 patches.
The archive copies three unchanged upstream unit tests.

## Selected upstream tests

| Test | Local coverage |
| --- | --- |
| `test-bus-signature` | Type signatures and namespace/path matching |
| `test-bus-error` | Error values, standard errno maps and registered maps |
| `test-bus-introspect` | In-memory XML generation for a fixed interface |

Meson registers each test with no arguments, an empty environment override,
an exit-code protocol and a 30-second deadline. Their source files need no
external fixtures. The test executables include basu through its upstream
`libsystemd_static` target. They do not load the installed `libbasu.so`.

The other nine registered tests are outside this bundle. Marshal, GVariant,
match and cleanup tests open a user or system bus. Vtable uses a system-bus
socket. Credentials inspects the current process and PID 1. Chat, server and
objects exercise IPC sessions. The benchmark is not registered by this build.
No system services or network access are required by the selected three tests.

## Prepare on the build host

Use the completed cross-build tree and its matching EmberBSD sysroot:

```sh
READELF=/absolute/cross-tools/bin/aarch64--netbsd-readelf \
  ruby target-prepare.rb /absolute/basu-v0.2.1 /absolute/sysroot /absolute/new-basu-tests
```

The command copies existing binaries. It does not compile, install packages
or change the sysroot. It checks Meson metadata, ELF64/AArch64, the interpreter
and dynamic dependencies. It records source, binary and base-file hashes.
The output contains the bundle, a sibling `.tar.gz` archive and its `.sha256`.
Existing paths, including dangling links, are rejected without replacement.

The checked build needs `/libexec/ld.elf_so`, `libc.so.12` and `libpthread.so.1`.
These files belong to the installed EmberBSD base. The bundle records their
sysroot hashes and requires matching target files. It does not bundle a libc,
replace the loader or make aliases. A different base requires a reviewed,
matching rebuild or new base-compatibility evidence.

The archive includes upstream test sources and the LGPL license. Meson test
and compiler metadata, ELF details, compilation commands and compiled-source
hashes preserve the build evidence. This is an acceptance bundle, not an
installed-library consumer test or a complete upstream suite.

## Run on the target

Extract the archive as an existing ordinary user. Keep the bundle intact.
Choose a new absolute directory for results:

```sh
sh ./run.sh /tmp/basu-local-results
```

The runner verifies all bundle hashes and the required base files. It uses
private HOME, XDG and temporary directories. Each unchanged upstream binary
runs without arguments under the original 30-second deadline. Exit 77 is a
failure here; skipped coverage does not count as success. Logs and exit codes
remain in the results directory. No target compilation is required.

On a platform with a supported Valgrind build, use:

```sh
sh ./run.sh /tmp/basu-memcheck-results valgrind
```

Memcheck uses a 300-second deadline per test. Invalid accesses, uninitialized
values and definite or possible leaks produce a failing exit code. This mode
must run successfully before it can be reported as Valgrind coverage.

## Validation boundary

Run the host-only output guards with `ruby target-prepare.rb --self-test`.
They check existing files, directories and dangling links for output, archive
and checksum paths. They also check the target runner's existing-result guard.
They do not execute the AArch64 binaries. Target execution, memory analysis,
the installed shared library and a complete D-Bus session remain separate.
