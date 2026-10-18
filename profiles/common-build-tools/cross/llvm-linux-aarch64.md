# LLVM 23 runtime/SDK acceptance on Linux → EmberBSD/AArch64

On 2026-10-18, Linux amd64 with GCC16.2.0 cross-built LLVM 23.1.3 for
EmberBSD/AArch64. Both independent source packages completed ordinary pkgsrc
build, installation, exhaustive partition selection and package checks.
The sysroot contains the runtime and full target SDK; the E34 VM contains
only the runtime. Native LLVM generators remain separate build tools.

| Artifact | SHA256 |
| --- | --- |
| `llvm-23.1.3nb1.tgz` | `98e733929bd897b5b41bbf8c416073e5af5cf2854f097b2c3e9d606884736198` |
| `llvm-devel-23.1.3nb2.tgz` | `46bb6b70fb98836e9f8c304700fbdb9f32a36e7c73e35186a33274a69c3e1cab` |
| Installed `libLLVM.so.23.1` | `d4b68decd87ef657e155cd7d6659f577c4b074b1b8bb28d8deaf7f39a55133f6` |
| Normal API/JIT acceptance bundle | `3cf8511f3940a4c082a58cbbdaea733a8247ecdd806e176603bd927a5be73e7f` |
| UBSan consumer acceptance bundle | `837323123d0d61559392fb3566b0a185e8a396ee422cc0b5a219930c2ade340f` |

The recipes and Python/lit dependency roles are pinned to Ports
`eeec1f094000f02d5d558651d5405cdf7ac0710c`. The metadata producer repair is
`8b426850f7ce50162bb107cdc4c5612f37db50f5`; its corrected pkgsrc patch checksum
is in `40bfce1548b5837805a38af1408da308b967a207`.
The common cross compiler configuration is pinned to `d645c98`.
The native helper repair is `8fab2d42e75a373d1939f7f693a3c6997f7c9735`.

Both builds preserve all 25 normal/experimental backends, shared LLVM, RTTI,
static SDK archives and installed gtest support. No target or native compilation
uses Clang. PIE/RELRO, interpreter, permissions, RPATH and work-reference checks
pass. SDK packaging reports two executable-bit warnings for upstream
`optpmap.py` and `style.css`, with zero errors. Every installed SDK payload
entry matches its package bytes, mode or symlink: eight runtime entries and
2781 development entries. Runtime SONAMEs and their aliases retain one provider.

## Installed target execution

The E34 source revision is `6dd57144183678938164b4c2dcfc370cdbde8473`.
Its matching kernel SHA256 is
`b813c4344e4aeef15a087567dacf3609273851e8955def1ae86ff13af8b3e46e`.
The VM reports its upstream NetBSD 11.0 AArch64 ABI identity.
It uses the accepted GCC16 runtime nb3 and the normal shared dependencies.
No compiler, generator, Python/lit or LLVM SDK is installed in the guest.

The installed [API acceptance](llvm-api-tests.md) passes:

- C API module creation, malformed-IR verifier rejection and bitcode roundtrip.
- Four default ORC LLJIT lifecycles, real JITLink selection and cross-DSO RTTI.
  Each creates, executes and removes generated code, then rejects missing symbols.
- A separate typed `SymbolsNotFound` negative exits exactly 1.
- Ordinary `pkg_delete` removes all eight runtime entries. The real C consumer
  then fails at the loader with missing `libLLVM.so.23.1`, exit 1.
- Ordinary reinstallation restores exact payload bytes/modes/links and package
  inventory. The same API/JIT suite passes again. `pkg_admin check` validates
  9537 files in 33 packages; removal preserves the preceding 9529 files/32 packages.

All execution uses canonical installed libraries without loader overrides.
GCC16 UBSan trap instrumentation also passes for both C/C++ consumers and
their header inline code. The LLVM DSO and generated JIT code are uninstrumented.
Valgrind does not support this NetBSD/AArch64 target; this is not target
Memcheck acceptance or a complete LLVM upstream test-suite result.
The compact [target logs](../tests/llvm-linux-aarch64/) retain actual output.

## Metadata handoff to Mesa

The GCC16 Linux [metadata helper](../../common-graphics/cross/llvm-config.md)
uses the original completed runtime build and installed SDK. Genuine generated
CMake install-strip instructions reproduce the installed DSO exactly.
Runtime/SDK generated report fields agree except their declared source/object
roots; installed public configuration headers agree byte for byte.
All 15 staged metadata/refusal checks pass.

Both before and after sealing, all 16 query groups agree with exact installed
SDK executables actually run in the VM. These tools are temporary QA fixtures;
their library link resolves to the installed runtime. The SDK package is never
installed in the guest. Fresh post-seal reference archive SHA256:
`140773e8f03f234eef4c8b5b61f875bb3ee3a10ba4dcef1b8059520ab927b49f`.

The accepted native executable SHA256 is
`1644431373926111f49c845c21f9c3120cb6ccf4a0a93d11a81ccc991af53aae`.
Its original manifest anchor is
`5b0ef566c7ae41d07901f5cb8a4192a4200795e063d551e4a139c8bd2d1bfb94`;
the sealed manifest is
`b60d6f8c313cc4fe54ffdfebe826b47a4b650939ff2c6b68fd3867bd53e270d3`.
All 32 sealing/integrity checks pass, including changed live headers/libraries
and retained native runtime files. Strict native Memcheck covers all 16 query
kinds on the actual accepted executable: zero errors, live blocks or suppressions.
This native metadata scope does not instrument target LLVM.

The actual MesaLib 26.2.4nb8 recipe parses with this sealed helper and emits
its path into pkgsrc's real NetBSD/AArch64 Meson machine file. The exact production
LLVM receipt, prefix, version, RTTI and shared ORC guards pass. Continue with the
[complete graphics composition](../../common-graphics/cross/profile.md) using
the sealed `bin/llvm-config`. Full Mesa configuration, package build and rendering
on this Linux/E34 stack remain the next consumer milestone. Earlier CM5 Mesa
receipts retain their separate package and hardware scope. KiCad is not built.
