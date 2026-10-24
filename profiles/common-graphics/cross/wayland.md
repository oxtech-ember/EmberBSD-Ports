# Cross-build and validate the common Wayland provider

Ports owns Wayland 1.26.0 and wayland-protocols 1.49 in the common graphics
profile. The selected versions follow the [upstream releases](https://wayland.freedesktop.org/releases.html).
[sources.tsv](../sources.tsv) pins original archives and SHA256; each recipe
retains pkgsrc provenance and patch checksums. The upstream libraries and
tests retain their MIT licence. EmberBSD adaptations disclose AI assistance.

Use the [complete cross composition](profile.md) with the existing GCC16
toolchain, target sysroot and common host build tools. These instructions
do not install another LLVM, Python or Wayland runtime on the build host.
Build the same scanner version as the target libraries:

```sh
HOST_CC=/absolute/native-gcc16/bin/gcc \
HOST_PYTHON=/absolute/python3.15 \
MESON=/absolute/meson-1.12.1/meson.py \
NINJA=/absolute/ninja PKG_CONFIG=/absolute/host/pkg-config \
sh build-wayland-scanner.sh /absolute/wayland-1.26.0.tar.xz /absolute/new-work
```

`HOST_CC` must name the [native GCC16](../../common-build-tools/cross/host-gcc16.md).
The script refuses a missing selection, system compilers, and Clang.

The scanner needs host Expat and libxml2 development metadata. `PKG_CONFIG`
must resolve those actual host providers. The helper verifies archive and
patch hashes, applies the series without fuzz, builds only the host scanner
with DTD validation and runs the original scanner golden/malformed-input
tests. Source, tool and installed file hashes remain in the work directory.
Keep the recipe and helper unchanged during execution.

The helper fixes its native library directory to `lib`. This keeps the
installed scanner metadata at the path required by protocol and Mesa consumers,
including on Linux hosts whose Meson default uses a multiarch directory.
It also records the actual compiler and linker flags. Private host libraries
must remain discoverable when the installed generator runs.

Set `EMBERBSD_WAYLAND_SCANNER` to `new-work/prefix/bin/wayland-scanner`.
The build requires its successful exact version response. Scanner consumers
also use its installed native `.pc` metadata through the cross profile.
The target `/usr/pkg/bin/wayland-scanner` must never execute on the Mac.
Both source-package and standalone generator checks retain their failures.

## Runtime and SDK packages

The NetBSD AArch64 and amd64 cross recipes split Wayland at revision 2.
`wayland-1.26.0nb2` contains twelve shared-library files and aliases, plus
the original `COPYING` notice. `wayland-devel-1.26.0nb2` contains the other
23 entries: headers, scanner, protocol data and development metadata.
It depends on that exact runtime. The two partitions do not overlap.
Their union is the complete upstream installation plus the notice.

Both ordinary recipes retain the complete Meson build, scanner and tests.
After installation, the selector first validates the complete staged inventory
and all symlink targets. Only then does it remove the other partition.
New, missing, unsafe or overlapping entries fail the package.
Normal package checks remain enabled. Native EmberBSD builds retain the full
35-entry package at the same revision, `wayland-1.26.0nb2`. This native
package satisfies the `wayland>=1.26.0nb2` tool dependencies of cross packages.

The upstream libraries and tests do not support Darwin. On a macOS build
host the same recipe therefore builds only the scanner
(`-Dlibraries=false -Dtests=false`). `PLIST.scanner` lists its six entries:
the executable, `wayland-scanner.pc`, the Autoconf and Make fragments, and
the protocol XML and DTD. This host package keeps the name
`wayland-1.26.0nb2` and satisfies the same tool dependencies. It does not
use epoll-shim or libffi. Target and native EmberBSD packages do not change.

The cross buildlink requires `wayland-devel` only during target compilation.
Application runtime dependencies retain `wayland`. The build-host scanner
still comes from native Wayland or the verified external scanner above.
Do not install `wayland-devel` in a runtime image.

The source contract checks actual pkgsrc metadata and a copy of a completed
normal package stage. It checks both partitions, unchanged bytes/modes/links,
native ownership, scanner routing and malformed-input refusals:

```sh
BMAKE=/absolute/native/bmake ruby ../tests/wayland-package-split.rb \
    /absolute/pkgsrc /absolute/cross.mk.conf /absolute/wayland-WRKSRC \
    /absolute/complete-DESTDIR /absolute/new-check
```

These checks pass with the actual GCC16 AArch64 revision-1 stage.
Separate fresh revision-2 builds now pass ordinary package creation and the
installed AArch64 checks below. The source-stage contract itself does not
substitute for those package and runtime results.

## epoll-shim configuration

The current epoll-shim release performs a target `kqueue` timer probe in
CMake. Cross configuration cannot infer the result from the build host.
Execute the generated
`ALLOWS_ONESHOT_TIMERS_WITH_TIMEOUT_ZERO_EXITCODE` probe on the target and
record its hash, kernel identity and exit status. Set the measured
`EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE` to `0` or `1` in the private MAKECONF.
Other values and an omitted measurement are rejected by the cross profile.

On the A733 NetBSD 11 target checked on 2026-10-08 the actual generated
probe returned `1`, selecting the upstream zero-timer workaround. This
result does not authorize hard-coding that answer for another target.

## NetBSD adaptations

The inherited peer-credential implementation incorrectly queried
`LOCAL_CREDS` into `struct sockcred`. That option returns an integer switch;
it cannot supply the peer identity. The correction uses `LOCAL_PEEREID`
and `struct unpcbid`, as specified by [unix(4)](https://man.netbsd.org/unix.4).
The new upstream client test compares PID and effective UID/GID with the
process that created the socket. The old implementation fails this check.
Use an EmberBSD kernel containing the
[local-socket fixes](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/local-socket-compatibility.md).
Older kernels also omit socketpair peer identity and can block a full-buffer
send despite `MSG_DONTWAIT`; a library-side identity fallback would hide
the missing kernel contract.

Upstream's generic descriptor counter enumerates `/dev/fd`. NetBSD can
provide static device nodes there, so their count neither detects new
descriptors nor tracks closed ones. The NetBSD test adaptation uses
`F_MAXFD` and `F_GETFD`, including descriptors above a lowered resource
limit. Existing leak and exec tests remain enabled. This is a test-harness
correction, not evidence that an untested runtime cannot leak descriptors.

## Test the installed target package

Run normal pkgsrc `package` checks and install the resulting package with
its recorded target dependencies. A complete cross build includes all
enabled upstream tests (`-Dtests=true`). Prepare the target bundle from
that exact WRKSRC and its installed cross sysroot:

```sh
ruby prepare-wayland-tests.rb --runtime --target amd64 /absolute/wayland-WRKSRC \
    /absolute/target-sysroot /absolute/new-test-bundle
```

The helper preserves all 26 invocations in Meson's original introspection.
Runtime mode selects the 24 ELF invocations and retains their original
data, exec descriptor helper and licence. `host-tests.tsv` explicitly records
the two separate checks: scanner golden tests and EGL symbols.
Neither target scanner nor `nm` is required in the runtime image.
Select `--target aarch64` or `--target amd64`; the default remains AArch64.
The helper checks ELF64, little-endian encoding and the selected machine for
every test ELF, the exec helper and all four installed runtime libraries.
It records the target in `target.txt`, bound by the bundle SHA256 manifest.
It records SHA256 for the bundle and installed libraries. No target library is bundled as an alternate provider.
Transfer it without macOS extended attributes, preserving executability.

On the target:

```sh
sh /absolute/test-bundle/run-wayland-tests.sh --runtime --target amd64 /absolute/new-results
```

The runner checks its selected target, the bundle marker and actual `uname`
before creating results. Unknown or duplicate target flags fail. The runner
verifies bundle and installed runtime hashes, package identity,
package contents and ELF dependency resolution. It clears loader overrides
and leak/timeout-disabling variables. Each invocation retains the upstream
30-second limit and an additional five-second kill grace. Exit 77 is
reported separately as SKIP. A failed process makes the suite fail.
The result directory contains individual logs, loader paths and totals.
Minimal images must also provide the ordinary base utilities used by the
runner, including `tee`.

Passing these tests establishes installed protocol-library behavior on the
recorded kernel. It does not establish target scanner behavior, a compositor,
physical display/input, accelerated Mesa or a VirGL/Wayland desktop.

The host regression uses actual amd64 test inputs and labelled AArch64 ELF
header fixtures. It preserves the 26-invocation selection and rejects foreign
machines, truncated helpers, class/byte-order mismatches and changed timeouts.
Runner guard fixtures do not execute target tests on the host:

```sh
ruby ../tests/wayland-targets.rb /absolute/wayland-WRKSRC \
    /absolute/target-sysroot /absolute/new-check
```

This preparation check is separate from an installed amd64 suite result.
The default helper mode retains the historical 26-invocation full package
check. Explicit `--runtime` selects the new package boundary and requires
that the target scanner and SDK package are absent.

Run the two separate source checks and prepare the runtime bundle together:

```sh
ruby ../tests/wayland-runtime.rb /absolute/wayland-WRKSRC /absolute/sysroot \
    /absolute/native/wayland-scanner /absolute/cross-nm \
    /absolute/cross-readelf /absolute/new-check
```

This passes the actual native 1.26.0 scanner golden/malformed-input cases
and checks the target library exports with the actual cross `nm`.
It prepares all 24 real AArch64 runtime test executables. Their ELF RPATH
entries contain only installed target library directories. No target
execution or new runtime package acceptance is inferred from these checks.

## Accepted runtime-only AArch64 VM run

On 2026-10-18, two fresh ordinary pkgsrc builds on Linux/GCC16.2 produced the
complete runtime and SDK partitions with all upstream tests enabled. Both pass
file, interpreter, permission, PIE, RELRO, RPATH and work-directory checks.
Normal SDK installation verifies all 13 runtime and 23 development entries,
including their bytes, modes and links. The package SHA256 values are:

| Package | SHA256 |
| --- | --- |
| `wayland-1.26.0nb2` | `66fa58ed077199d192eab2c7db082c53f2c39b1649c0c15d418d2c1bc53c38c1` |
| `wayland-devel-1.26.0nb2` | `5b46ee4da1f15df0baf4dc71e43914cd876fb3c0ce84daa9e3c9d76b5cfa7253` |

The EmberBSD 11 AArch64 VM installs only the runtime package and its genuine
runtime dependencies. All 153 entries across these seven packages match their
recorded SDK providers. The 24 upstream ELF invocations pass twice with zero
skips or failures, before and after normal deletion/reinstallation. The removed
library causes the real client loader to fail as expected. Loader overrides,
leak-check suppression and target SDK/scanner installation are absent.
The native scanner golden/malformed-input test and target EGL symbol check
pass separately; they are not counted as target runtime executions.

An initial run stopped because the minimal image lacked `tee`. Its exact
utility from the verified E34 base set was added, and the unchanged runner
then passed. Those partial logs remain with the successful results. All
5,822 prior package paths retain their hashes and metadata. Two verified
source/evidence archives preserve the full builds and guest readback; scoped
temporary guest files were removed after process, descriptor and mount checks.

This validates the new runtime package on the recorded AArch64 VM. It does not
establish a new native or amd64 package run, target scanner execution, a
compositor, physical display/input or KiCad WebView behavior.

## Earlier full-package board run

On 2026-10-08 the package cross-built on Apple Silicon with Ports GCC16.2
and passed pkgsrc file, dependency, interpreter, PIE, RELRO, RPATH and
work-directory checks. Installed on Orange Pi Zero 3W (A733), it passed
all 26 enabled upstream invocations, with zero skips or failures, on the
updated `EMBER64` kernel. Runtime hashes and ordinary loader paths were
checked; no alternate libraries or disabled leak checks were used.

The descriptor-counter regression separately reproduced eight failures
across twelve cases with the old static-directory counter and zero with
the corrected counter. The kernel tests reproduced 3/12 nonblocking-send
and 16/25 peer-identity failures before the update, then passed all 37.
This receipt covers that board/kernel, not every supported EmberBSD platform
or a sustained compositor workload.
