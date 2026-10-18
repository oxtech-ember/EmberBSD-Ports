# Libspnav 1.2

The canonical `x11/libspnav` provider retains the native Unix-domain socket
protocol, the X11 Magellan protocol and the public Magellan compatibility API.
The graphics, media and Plasma exports use this one provider.
The default, development-only and common-tools-only exports do not add it.
X11 support remains enabled.

The source is the current stable [upstream 1.2 release](https://github.com/FreeSpacenav/libspnav/releases/tag/v1.2),
at commit `d641e5cbbe0d6d2381a2ee8d95c8c7273d005272`.
The original `libspnav-1.2.tar.gz` has SHA256
`093747e7e03b232e08ff77f1ad7f48552c06ac5236316a5012db4269951c39db`.
The [manifest](../sources.tsv) and recipe `distinfo` retain its URL and hashes.
The package preserves John Tsiombikas's BSD license without changes.

The custom upstream Makefile now accepts the actual target OS and search paths.
Its native defaults remain intact. pkgsrc supplies its compiler, archiver,
target OS and managed include/link paths. Target builds select NetBSD ELF
output independently of the build host's `uname` result.

## Socket lifetime repairs

The original library allocates its event queue before it connects.
Four unsuccessful opens lose 144 bytes and leave another 48 bytes reachable.
The repair allocates that queue after a successful connection and closes the
socket if allocation fails.

Five original Unix-path guards test the descriptor as a Boolean.
Descriptor zero skips event, sensitivity and close paths; minus one can enter
closed-library queue paths. The guards now require `sock >= 0`.
This also preserves the original X11 branch when the Unix descriptor is absent.
Public headers, signatures, protocol values and library SONAME remain intact.

The [socket contract](../tests/libspnav/socket-protocol.rb) uses real Unix
sockets and the public library API. Its peer exchanges actual protocol-0 and
protocol-1 packets. It checks known motion/button values, descriptor-zero
events and legacy sensitivity, failed opens, closed state and reconnect.
The unmodified library reproduces allocation loss, descriptor-zero failures
and closed-state SIGSEGV. The actual packaged native library passes every case.
Four strict Valgrind 3.24 runs report zero errors and zero live allocations,
without suppressions.

The native runner requires GCC16, Ruby, Valgrind and `timeout`:

```sh
ruby profiles/common-graphics/tests/libspnav/socket-protocol.rb \
  /absolute/native-prefix /absolute/gcc16 /absolute/new-check
```

`CPPFLAGS` and `LDFLAGS` can supply a separate native dependency prefix.
The C client also cross-compiles for target execution.
The [plain C peer](../tests/libspnav/socket-peer.c) forks that same client and
exchanges the same known protocol packets. It needs no interpreter in the guest.
Its three native protocol modes and strict peer memory check also pass.
Its periodic deadline also interrupts a wait entered after the first expiry.
Two native negative clients remain silent or complete the unchanged API client
and refuse to exit. The peer terminates and reaps both clients at its deadline
and removes its socket. Neither negative needs a simulated device.
The matching GCC16 AArch64 peer and client pass the five public socket
contracts in EmberBSD.
After target installation, their invocation is:

```sh
./socket-peer ./socket-client events /tmp/new-libspnav-socket
```

The packet peer establishes a library/protocol contract; it does not establish
physical input-device or X11 runtime acceptance.

## Package and analysis checks

Ordinary Linux-native and AArch64 GCC16 packages pass the normal pkgsrc checks.
The full static PLIST has nine entries: three headers, the static library,
the shared library and its two links, `spnav.pc` and the original notice.
The standard install commands set data/header modes to 0644 and the DSO to
0755. pkgsrc creates all package-owned directories with public traversal.
The [access contract](../tests/libspnav/package-access.rb) rejects private
umask-derived modes and passes both corrected stages. The installed target
library also loads under the real `nobody` account, with no supplementary groups.
That user reads all seven regular payloads byte-identically to the GCC16 stage.
Both complete stages and package ownership match every payload byte/link.
The original public headers and enabled X11 configuration match.
All 70 upstream exported symbols remain present; the target linker also
exports its five ordinary data-boundary symbols.

Real GCC16 AArch64 consumers link against the shared provider and the complete
static archive. Both outputs are AArch64 PIE with RELRO and target runtime
paths. The target DSO retains `libspnav.so.0` and its actual NetBSD/X11 providers.
The provider's exporter preflight refusal checks pass.
The actual positive-export absence guard also rejects a regular file,
directory, symlink and dangling symlink in the five-path regression.
The full positive export matrix remains pending.

The ordinary target package installs with genuine `libX11`, `libxcb`, `libXau`
and `libXdmcp` packages. This adds no compiler or generator package.
All 3,554 payload entries match their package bytes, symlink targets,
permissions and owners.
All 6,187 prior paths under `/usr/pkg`, excluding its package database, retain
their bytes, modes, uid and gid.
The shared-library client and the client linked with the complete static
archive each pass five checks as `nobody`:
closed state, failed opens, descriptor-zero events, legacy sensitivity, and
known motion/button values with disconnect and reconnect.
Normal package deletion removes all nine provider paths. The real nonroot
loader then refuses the missing `libspnav.so.0`. Reinstallation of the same
verified archive restores every entry and repeats all five shared checks.

GCC16, Clang 19 analysis and Cppcheck 2.22 use the actual native and target
compile flags for all four library translation units, before and after repair.
Clang retains the configuration-file stream-lifetime warning.
GCC retains ordinary unchecked-I/O and character-index diagnostics.
Native Cppcheck parsing stops at a Linux signed-128-bit declaration.
Target preprocessing parses successfully, with 141 style and four
float/integer representation portability findings retained.
These reports retain findings.

The plain C peer also passes GCC16 and Clang path analysis.
Cppcheck parses its actual native and target preprocessing before and after
the deadline repair. Its findings do not change. The standard POSIX socket
cast, signal-handler representation and style findings remain visible.
Client and timeout-negative analysis also retains branch-analysis limits.

Fragmented stream input, event removal after EOF, the configuration-file
lifetime warning, X11/device execution and complete KiCad integration remain
separate acceptance work.
