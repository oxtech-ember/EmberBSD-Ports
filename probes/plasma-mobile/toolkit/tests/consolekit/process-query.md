# NetBSD process snapshot checks

The source is `ConsoleKit2-2.0.0/src/ck-sysdeps-netbsd.c` from
`ConsoleKit2-2.0.0.tar.gz`. Its SHA256 is
`f3f4a424f2a4fbb67696b4011caf2fd4c02e5e67c24ef1c86cecb2301bccdba4`.
The recipe patch retains the upstream GPL-2.0-or-later source and authorship.
This local adaptation is AI-assisted. It has not been submitted upstream.

The private query now requires a complete `kinfo_proc2` record for the requested
PID. It requires valid user data, an active or stopped process, and a valid
start time. It uses `p_realstat` for process state. `p_stat` can describe an LWP.
A missing PID can produce a successful sysctl response with zero returned bytes.
The query rejects this response before any consumer reads the record.

The query initializes failure output. Invalid PID input does not call sysctl.
The stat constructor initializes its output and frees a rejected allocation.
The UID query returns `(uid_t)-1` for invalid input or a rejected record.
A verified UID of zero remains valid. The environment query closes each opened
KVM handle and does not read the environment after a rejected snapshot.

Public function signatures do not change. `CkProcessStat` is opaque. Its private
NetBSD representation retains start microseconds beside the existing seconds.
This change does not expose a new public identity or session API.

## Run the host regression

Provide GCC 16, Clang with ASan/UBSan, Cppcheck, pkgsrc digest, and a native GLib
pkg-config file. Run from any directory. Use absolute tool and archive paths.
Set `HOST_CFLAGS` to the native SDK flags if the compiler needs them.

```sh
CC=/absolute/gcc-16 \
SANITIZER_CC=/absolute/clang \
CPPCHECK=/absolute/cppcheck \
DIGEST=/absolute/digest \
PKG_CONFIG=/absolute/pkg-config \
ruby process-query.rb /absolute/ConsoleKit2-2.0.0.tar.gz /new/receipt
```

The runner verifies the archive and all recipe patch hashes. It extracts the
actual private struct and six functions after applying the recipe patches.
Its baseline omits only the NetBSD sysdeps patch. The selected baseline functions
are the original upstream functions. There is no dependency on local Git history.
The receipt contains the original source, extracted functions, upstream COPYING,
commands, logs, and input hashes. Temporary source trees and executables are removed.

The host test links real native GLib. It controls only sysctl, KVM, and the native
record representation. This model does not prove the target record layout.
Cases cover missing, short, oversized, unwritten, mismatched, invalid, and dead
records. They also cover valid stopped processes, sleeping LWPs, absent controlling
TTYs, distinct start microseconds, UID zero, allocation balance, and KVM failures.
Ten mutations remove individual production checks or lifetime operations.
Every mutation must cause the actual-source fixture to fail.

GCC `-fanalyzer`, Clang Static Analyzer, and Cppcheck analyze both source variants.
The runner retains their full logs. Review their delta before accepting a change.
ASan/UBSan run the candidate. This is not a Valgrind run. Valgrind is unavailable
for the tested macOS host platform.

## Check the genuine target declarations

Use the target compiler and the actual EmberBSD target sysroot:

```sh
/absolute/x86_64--netbsd-gcc --sysroot=/actual/target/sysroot \
  -std=gnu11 -Wall -Wextra -Werror -fsyntax-only \
  process-query-netbsd-header.c
```

This small compile checks the genuine MIB constants, state constants, and relevant
record field sizes. It also checks that `sys/proc.h` exposes the state constants to
ordinary userland. It does not compile the full ConsoleKit translation unit.

## Evidence and remaining boundary

The host run found 100 failures in 144 baseline checks. The candidate passed all
157 checks and all ten negative controls. GCC 16 path analysis had no diagnostics
for either host variant. Clang Static Analyzer reported two baseline uninitialized
reads and no candidate diagnostics. Cppcheck retained one unchanged warning in
native GLib `gstrfuncs.h` (`uselessAssignmentPtrArg`). ASan/UBSan passed.
The genuine amd64 target header compile also passed.

The full target translation unit remains pending. It requires real cross-built
GLib headers, its target `glibconfig.h`, and the target ConsoleKit configuration.
Native GLib headers cannot replace those inputs. Host analysis is not target
analysis or evidence of a working native ConsoleKit backend.

This patch checks process metadata only. It does not verify session membership,
D-Bus caller authority, controlling-terminal ownership, or a root broker's target
user. It does not enable a backend or alter PAM policy. The environment remains
untrusted. KVM can look up the environment by PID after the snapshot, so PID reuse
still needs a separate authority contract. A cookie remains a locator.
