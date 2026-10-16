# Cross-build and validate the common Wayland provider

Ports owns Wayland 1.26.0nb1 and wayland-protocols 1.49 in the common graphics
profile. The selected versions follow the [upstream releases](https://wayland.freedesktop.org/releases.html).
[sources.tsv](../sources.tsv) pins original archives and SHA256; each recipe
retains pkgsrc provenance and patch checksums. The upstream libraries and
tests retain their MIT licence. EmberBSD adaptations disclose AI assistance.

Use the [complete cross composition](profile.md) with the existing GCC16
toolchain, target sysroot and common host build tools. These instructions
do not install another LLVM, Python or Wayland runtime on the build host.
Build the same scanner version as the target libraries:

```sh
HOST_PYTHON=/absolute/python3.15 \
MESON=/absolute/meson-1.12.1/meson.py \
NINJA=/absolute/ninja PKG_CONFIG=/absolute/host/pkg-config \
sh build-wayland-scanner.sh /absolute/wayland-1.26.0.tar.xz /absolute/new-work
```

The scanner needs host Expat and libxml2 development metadata. `PKG_CONFIG`
must resolve those actual host providers. The helper verifies archive and
patch hashes, applies the series without fuzz, builds only the host scanner
with DTD validation and runs the original scanner golden/malformed-input
tests. Source, tool and installed file hashes remain in the work directory.
Keep the recipe and helper unchanged during execution.

Set `EMBERBSD_WAYLAND_SCANNER` to `new-work/prefix/bin/wayland-scanner`.
The build requires its successful exact version response. Scanner consumers
also use its installed native `.pc` metadata through the cross profile.
The target `/usr/pkg/bin/wayland-scanner` must never execute on the Mac.
Both source-package and standalone generator checks retain their failures.

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
ruby prepare-wayland-tests.rb --target amd64 /absolute/wayland-WRKSRC \
    /absolute/target-sysroot /absolute/new-test-bundle
```

The helper preserves all 26 invocations from Meson's actual introspection,
their original test scripts/data, the exec descriptor helper and licence.
Select `--target aarch64` or `--target amd64`; the default remains AArch64.
The helper checks ELF64, little-endian encoding and the selected machine for
every test ELF, the exec helper and all five installed runtime providers.
It records the target in `target.txt`, bound by the bundle SHA256 manifest.
It records SHA256 for the bundle and target scanner/libraries. No target library is bundled as an alternate provider.
Transfer it without macOS extended attributes, preserving executability.

On the target:

```sh
sh /absolute/test-bundle/run-wayland-tests.sh --target amd64 /absolute/new-results
```

The runner checks its selected target, the bundle marker and actual `uname`
before creating results. Unknown or duplicate target flags fail. The runner
verifies bundle and installed runtime hashes, package identity,
package contents and ELF dependency resolution. It clears loader overrides
and leak/timeout-disabling variables. Each invocation retains the upstream
30-second limit and an additional five-second kill grace. Exit 77 is
reported separately as SKIP. A failed process makes the suite fail.
The result directory contains individual logs, loader paths and totals.

Passing these tests establishes installed protocol-library and scanner
behavior on the recorded kernel. It does not establish a compositor,
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

## Accepted target run

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
