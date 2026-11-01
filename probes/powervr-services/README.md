# Legacy PowerVR Services compatibility probes

These experimental probes precede a native EmberBSD port of the GE8300
PowerVR Services stack. They do not load GPU firmware or access GPU devices.
They do not establish graphics acceleration or vendor userspace compatibility.

## Selected candidate

The candidate uses the published GE8300 fbdev/musl ARM64 bundle from
`CrealityTech/sonic_pad_os`, revision
`7f37a7fbf4ad59907034715e3d967b9177de1cd4`.
Its kernel and userspace metadata identify DDK `1.11@5516664`.
Use the kernel interface, userspace and firmware as one candidate set.
The same BVNC does not establish firmware ABI compatibility.

Vendor binaries stay outside this repository. Source URLs, licenses and
checksums must be recorded before a runtime probe uses that closure.

## Initial loader questions

1. Can the native AArch64 loader handle Linux-format ELF TLS descriptors
   without loading a Linux libc?
2. Does `RTLD_LOCAL` isolate imports from native startup symbols?
3. Does an explicit import namespace select the intended ABI adapter?

`tests/foreign_tls.c` has no libc dependency or constructors. Its normal
variant uses ELF TLS. `PROBE_GLOBAL` is a deliberate negative control.
The negative control uses atomic access to avoid a data race.

`tests/native_loader.c` verifies initial TLS values and isolation across
the main thread and two native pthread threads. Build its executable with
dynamic symbol export for the binding tests.

The binding provider returns 29. The native executable exports a conflicting
function that returns 11. The consumer calls either the conflicting name
or a dedicated name selected with `PROBE_NAMESPACED`.

Require real TLSDESC relocations and an empty dependency list in the TLS
DSO before interpreting its runtime result. The conflicting binding test
must expose the actual target, not only compare `dlsym` addresses.

## Build boundary

Use native-tools v2 and separate `EMBER_HOST_ABI_*` settings.
Do not reuse objects built through native-tools v1.
Build host tools for the host and target consumers for native EmberBSD.
Synthetic foreign DSOs deliberately select the Linux AArch64 ELF target;
they do not import a Linux runtime or replace the EmberBSD application ABI.

Target execution uses a temporary unprivileged child with CPU, memory and
core-dump limits. GPU device access remains outside these loader tests.
Complete dependency, constructor and symbol-binding checks before loading
vendor GPU libraries.

Compile `native_loader.c` with the selected SDK's native EmberBSD C target
and link flags, plus `-pthread -Wl,-E`. Compile `run_guarded.c` with the
same C target and link flags. Use `-std=c11 -O2 -Wall -Wextra -Werror`.

For the synthetic foreign DSOs, use that SDK compiler and LLVM linker with:

```text
--target=aarch64-linux-musl -march=armv8-a -std=c11 -O2
-Wall -Wextra -Werror -fPIC -shared -nostdlib
-fno-stack-protector -fno-emulated-tls -mno-outline-atomics
-ftls-model=global-dynamic -Wl,-z,defs
```

| Output | Source | Additional selection |
| --- | --- | --- |
| `foreign_tls.so` | `tests/foreign_tls.c` | No definition. |
| `foreign_global.so` | `tests/foreign_tls.c` | `-DPROBE_GLOBAL` |
| `binding_provider.so` | `tests/binding_provider.c` | SONAME `binding_provider.so` |
| `binding_plain.so` | `tests/binding_consumer.c` | Link the separate provider DSO. |
| `binding_namespaced.so` | `tests/binding_consumer.c` | `-DPROBE_NAMESPACED`; link the provider DSO. |

Build the provider before its consumers. Give each DSO its own SONAME.
Retain the provider's `DT_NEEDED` entry in both consumers.
Use a literal `$ORIGIN` runpath or a process-local library search directory
for that provider. Do not include Linux libc in this directory.

`tests/run_guarded.c` requires an unprivileged caller. It bounds CPU time,
disables core dumps and kills its child after a monotonic wall timeout.
Run target probes with a five-second CPU limit and a 256 MiB address limit:

```sh
./run_guarded 5 256 ./native_loader tls ./foreign_tls.so
```

An address limit of zero is reserved for host sanitizer runs whose shadow
mapping requires a large virtual address range. Target acceptance uses 256.
The loader fixture also rejects a privileged caller.

The `tls` case creates threads after `dlopen`. The `tls-preexisting` case
waits for both workers to reach a barrier before calling `dlopen`.
A second barrier publishes the function pointers to those workers.
Both cases require an initial value of 7 in each worker and retain
main-thread value 21 while worker values become 100 and 101.

## Required runtime cases

Each row runs in a fresh process under `run_guarded 5 256`.
The artifact names below describe the intended build outputs.
They are not present until the selected v2 SDK builds them.

| Loader arguments | Expected exit | Purpose |
| --- | --- | --- |
| `tls ./foreign_tls.so` | 0 | New threads receive independent TLS. |
| `tls-preexisting ./foreign_tls.so` | 0 | Existing threads receive dynamic TLS. |
| `tls ./foreign_global.so` | 65 | Shared atomic storage must fail isolation. |
| `tls-preexisting ./foreign_global.so` | 65 | Existing threads also detect shared storage. |
| `binding ./binding_plain.so 11` | 0 | Native startup symbol wins ordinary binding. |
| `binding ./binding_plain.so 29` | 65 | Detect an incorrect isolation assumption. |
| `binding ./binding_namespaced.so 29` | 0 | Explicit namespace selects the provider. |

Exit 71 (loader failure), a signal or a timeout cannot satisfy an expected 65.
Inspect the TLS DSO for `PT_TLS`, `R_AARCH64_TLSDESC`, no `DT_NEEDED`,
no undefined runtime imports, and no constructors before running it.
The shared-storage control must have no TLS segment or TLS relocations.
The binding consumers must retain a real imported relocation and a
`DT_NEEDED` entry for the separate provider DSO. Do not use LTO,
`-Bsymbolic`, protected symbols or hidden marker visibility.

These cases only test the native loader boundary.
The next interfaces are defined in [ABI boundary](ABI-BOUNDARY.md).

## Current validation

On 2026-11-02, Clang 23.1.4 built the fixtures through native-tools v2.
The native executables used a completed EmberBSD AArch64 C base, its CRT,
compiler-rt builtins and LLVM linker. No native-tools v1 objects were reused.

All seven cases above passed on a physical AArch64 EmberBSD 11.0 device.
Each process ran as an ordinary user with the documented limits.
Both real TLS cases passed. Both shared-storage controls returned 65.
Ordinary binding returned 11; the explicit namespace returned 29.
The native consumer loaded the installed `libpthread.so.1` and `libc.so.12`.
This tests the installed native loader and runtime, not installation of the
newly built SDK runtime on that device.

Cppcheck and Clang Static Analyzer passed for the probe sources.
On the Linux x86_64 build host, ASan/UBSan passed the same seven cases,
two invalid-input cleanup cases and a blocking-child wall-timeout control.
Valgrind was unavailable in the selected prefix and was not run.
These host checks do not substitute for the AArch64 loader results.

Temporary target fixtures were removed. The application image, its profile,
known process liveness and system boot time were unchanged across the run.
No GPU registers, vendor libraries or firmware were used.
The results establish the synthetic TLS and symbol-binding boundaries.
The vendor ABI adapter, native KMD and hardware EGL/GLES remain untested.

The original probe sources use the [BSD 2-Clause license](LICENSE).
