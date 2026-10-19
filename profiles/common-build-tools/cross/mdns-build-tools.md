# mDNSResponder source and cross build contract

The common `net/mDNSResponder` recipe selects Apple's latest published tag,
[2881.120.11](https://github.com/apple-oss-distributions/mDNSResponder/tree/mDNSResponder-2881.120.11),
checked on 2026-10-18. The tag resolves to commit
`641cdf73ef46e1824895cbc44ad8ac7647da2479`. The official archive SHA256 is
`f665cf02b5c930f9b70fb39b7567f03dd821997594c56ce399098eaa0372fb15`.
The [manifest](../sources.tsv) and pkgsrc distinfo pin that archive.
The exporter checks all nine retained patch checksums before copying the recipe.

The public header still reports API version `16610000` and a 16-byte
`TXTRecordRef`. These values do not identify the project release. Buildlink
requires the current package version. Cross builtin detection reads the target
sysroot header; native dependency recursion reads the native header.

The source update retains the pkgsrc license, authorship, complete package list
and IPv6 option. Two portability patches need new context. The old client-stub
limits patch is obsolete because upstream now supplies those declarations and
initializers. The POSIX Makefile patch preserves upstream `MDNS_NO_STRICT=1`.

The published resolver callback refers to `request_state.resolve_awdl` and
`AWDLInterfaceID`. Neither exists in the published source. The source patch
removes that private-only log operand and its format fields. Both resolver
event logs and their public values remain. The patch changes no resolver
decisions, public interfaces or daemon command-line behavior.

Daemon startup now stops if `F_GETFL` fails. A startup error closes a listening
socket created by that call and invalidates its saved descriptor. Caller-owned
launch sockets remain open. This repairs the confirmed descriptor leak in the
same published module.

The upstream POSIX Makefile assigns `os` from the build host's `uname` result.
This overrides a recipe environment value. The recipe passes all seven existing
platform mappings through `MAKE_FLAGS`, which GNU Make command arguments retain.
Flex and Bison generate `dnsextd`, selected by the default graph only on Darwin.
NetBSD's complete default graph builds directly from C. Its package needs no
generator or target Flex library. Darwin and explicit `dnsextd` generator rules
remain intact. Explicit `dnsextd` is outside the NetBSD package's installed list.
The existing Linux TLS selection remains platform-specific; the NetBSD source
branch has no POSIX TLS object selection. This update adds no TLS restriction.

The recursive `Clients/Makefile` uses a separate `SYSTEM` variable. The recipe
passes `SYSTEM=${OPSYS}` as a make command argument. This prevents a Darwin
cross host from selecting the implicit system-library branch for a NetBSD
client. `mdns-client-platform.py` checks the actual recursive make graph and
the expanded pkgsrc flags. Four cases retain native `SYSTEM=Darwin`, reproduce
the missing client library, select `SYSTEM=NetBSD` with `-ldns_sd`, and show
that an environment value alone is insufficient. This graph check does not
establish a compiled package.

The [build regression](../tests/mdns-build-tools.py) uses Python 3.15 and
SDK library API 1. It compares actual pkgsrc metadata with the original pinned
recipe. Separate work directories prevent cached tool selections from hiding
the former Flex buildlink dependency. Upstream GNU Make dry runs reproduce host
OS selection and check the full NetBSD graph. Darwin and explicit `dnsextd`
controls still contain both generator commands.

```sh
python3.15 profiles/common-build-tools/tests/mdns-build-tools.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --pkgsrc /absolute/prepared-pkgsrc \
  --baseline-recipe /absolute/pinned-pkgsrc/net/mDNSResponder/Makefile \
  --archive /absolute/mDNSResponder-2881.120.11.tar.gz \
  --makeconf /absolute/private-cross-mk.conf \
  --bmake /absolute/native-bmake --gmake /absolute/native-gmake \
  --work /absolute/new-check-directory
```

Ordinary native x86-64 Linux and cross AArch64 packages pass with GCC16 and one
build job. Package-list, PIE, applicable RELRO, runtime-path and work-reference
checks pass. The package contains `dns-sd`, four standalone clients, `mdnsd`,
`libdns_sd`, the public header and both manual pages. The recipe retains its
existing library RELRO exception. These checks install no package.

The [public API contract](../tests/mdns-api.c) passes 518 native cases against
the actual newly staged library. It checks exact binary TXT values, both buffer
ownership routes, growth, replacement, key rules, invalid inputs and escaped
service names. Strict Memcheck reports zero errors and zero live allocations.
Compile it with GCC16, `-std=c23 -O2 -g -Wall -Wextra -Werror -UNDEBUG`, the
selected stage's include/library paths, and `-ldns_sd`. Select that library
explicitly at runtime. The staged native `dns-sd` no-argument usage path exits
normally under a ten-second timeout. No daemon or multicast service runs.

The AArch64 consumer builds with GCC16 undefined-behavior trap instrumentation
(`-fsanitize=undefined -fsanitize-trap=undefined`). It needs only `libdns_sd.so`
and `libc.so.12`. This instruments the consumer; it does not instrument the
packaged provider. All 518 cases also pass against the ordinary installed
AArch64 package in an EmberBSD VM. The installed library hash matches the
package and SDK. `ldd` selects `/usr/pkg/lib/libdns_sd.so` and the verified fork
libc. The package integrity check passes. This tests the public local API;
it does not establish network discovery or daemon service operation.

The [socket regression](../tests/mdns-sockets.py) links the complete ordinary
native daemon objects. It renames the real daemon entry point and runs the
[fault contract](../tests/mdns-sockets.c) as its test entry point. Real sockets
exercise ten negative startup cases: socket, bind, both `fcntl` operations,
listen and event registration failures. The control reverses only the socket
repair. It reports twelve assertion failures; the repaired source passes.
Strict Memcheck with descriptor tracking reports zero errors, zero live
allocations and only the three standard descriptors at exit. Actual descriptor
counts and caller-owned handles are checked in each case. Event registration
always fails in this test; it starts no service.

```sh
python3.15 profiles/common-build-tools/tests/mdns-sockets.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --source /absolute/native-package-WRKSRC \
  --build-log /absolute/native-package.log \
  --work /absolute/new-short-test-directory
```

The full changed resolver module is checked with the ordinary native and target
GCC16 flags and wrappers. The source control fails on the two missing private
identifiers. The patched units compile without warnings. Clang19 static
analysis passes on native and target source with the same platform and
hardening flags. Clang cannot parse GCC's fortified glibc vararg builtins in
the preprocessed native unit. Its additional NetBSD preprocessed run reports a
potential null reply header after an opaque call. The header is an embedded
array; that call either returns an allocation or terminates. Its short-length
guard cannot apply to the minimum 15-byte response constructed there.
Cppcheck 2.22 analyzes
the complete NetBSD preprocessed units before and after; all 146 inherited
diagnostics match after source-line mapping. The native preprocessed controls
both stop at Linux UAPI's aligned signed `__int128` declaration.

GCC16's analyzer still reports the socket helper as leaking at both `-O2` and
`-O0`. Its trace stops inside the helper before the caller's new cleanup. The
real descriptor regression verifies that exact failure path closes its socket.
The `-O0` target run also reports a request error socket before its caller
closes it through `AbortUnlinkAndFree` and `abort_request`. That report exists
in both controls. Diagnostics are retained without suppression. The package also
retains existing warnings in `mDNSUNP.c` and `mDNS.c`. These results do not
establish a warning-free daemon.
Installed discovery, daemon service operation and CUPS integration need their
own acceptance checks. Dry runs do not establish a Darwin build.
