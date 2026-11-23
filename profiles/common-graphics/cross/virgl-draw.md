# First bounded guest VirGL draw

This experimental Ports runner uses the existing, unchanged `epoxy-render`
from [installed libepoxy acceptance](epoxy.md). Its real interface accepts a
GBM device path and expected renderer substring. The runner passes exactly
`/dev/dri/renderD128 virgl`, requires four VirGL cycle records and refuses
software/loader overrides. It does not build or install any library.

The accepted inputs are MesaLib 26.2.4nb2, libepoxy 1.5.10nb2 and the shared
LLVM 23.1.2nb1 runtime. The two complete artifact manifests are pinned in
`run-virgl-draw.sh`: the immutable [Mesa runtime rebind](mesa-runtime-rebind.md)
metadata and its newly prepared epoxy bundle. Changed manifests, payloads,
unrecorded files and nonregular bundle entries fail before execution. The
unchanged accepted verifier scripts check complete installed package files,
links and runtime library hashes. Another accepted package revision requires
deliberate revalidation and new pins; missing files are never skipped.

From the cross-build host, verify the exact target sysroot without executing
target code:

```sh
sh run-virgl-draw.sh --verify-sysroot /absolute/mesa-metadata-bundle \
    /absolute/epoxy-bundle /absolute/sysroot
ruby ../tests/virgl-draw-runner.rb /absolute/mesa-metadata-bundle \
    /absolute/epoxy-bundle /absolute/sysroot /absolute/new-guard-work
```

The host guard fixture changes private copies/links, exercises actual shell
function bodies against synthetic logs, and checks the clean environment,
exact consumer arguments, timeout arguments and nonzero status preservation.
It neither simulates GPU success nor establishes target rendering.

## Isolated target execution

Use a matched experimental [VirGL trial kernel](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/utm-virgl-optin.md) with explicit classic VirGL
negotiation and the existing DMA/ownership checks retained. Ordinary VirtGPU trial
still disables VirGL. The selected paired QEMU must use its opt-in classic
lifecycle profile and the accepted ANGLE Metal renderer. Kernel creation,
host identity checks and the isolated VM lifecycle are separate from this
target runner; see [the paired host instructions](../../../probes/utm-virgl-host/qemu/README.md).
No sysctl can retrofit feature negotiation into an already attached device.

Transfer the runner and both accepted bundles into a private synthetic root,
with the exact installed package closure and native `/usr/bin/timeout`.
The small root also needs the ordinary `find`, `awk`, `sha256`, `readlink`,
`ldd`, `sed` and shell utilities used by these verifiers:

```sh
sh /tests/run-virgl-draw.sh /tests/mesa-metadata /tests/epoxy \
    /tmp/virgl-draw-result
```

The log directory must be new. The device must be a real character node,
not a symlink. The child receives a clean environment, shader caching disabled,
and a 60-second limit with a five-second forced-kill grace period. Its original
nonzero exit status is preserved in `exit-status` and returned by the runner.
`ldd` and the live `dl_iterate_phdr` inventory must name recorded package
providers. The live inventory must include epoxy, EGL, GLES, GBM, Gallium,
LLVM and libdrm; loaded package bytes are checked again after drawing.
Base-system library paths retain the accepted runner's separate OS boundary.

The existing consumer rejects invalid GLSL, draws a green triangle over red,
checks an interior and exterior pixel, and performs four EGL context lifecycles
on one GBM device. Its `glFinish` and readback exercise completion; this is not
an outstanding-command reset test. The final marker is:

```text
PASS: installed VirGL shader/triangle readback and four GBM EGL lifecycles on renderD128
```

The guest boot script should record the runner status before `halt -p`; the
host supervisor must require that status, the marker and normal QEMU exit.
Package/guard success alone is not guest draw acceptance. The accepted execution follows.
A successful run qualifies this offscreen workload on the exact guest/host
pair, not a visible compositor, scanout, general fault recovery, live reset,
hostile-command validation or physical A733 GPU acceleration. This local
BSD-2-Clause runner and guard fixture were developed with AI assistance.

## Host supervisor and accepted result

The [host supervisor](../../../probes/utm-virgl-host/qemu/run-guest-draw.rb)
checks the accepted QEMU/renderer receipts and ANGLE framework hashes, then
starts a dedicated snapshot guest with no network or monitor. It checks actual
loaded host providers, Metal selection, the exact target success marker and
four VirGL cycles. It requires normal QEMU exit and unchanged input bytes.
The whole VM has a 120-second limit and a five-second termination grace;
individual logs are limited to 64 MiB and total retained output to 100 MiB.
A failed attempt retains diagnostics without a success manifest.

Use simple absolute paths; the evidence parent must be canonical and exist:

```sh
ruby probes/utm-virgl-host/qemu/run-guest-draw.rb \
    /absolute/accepted-qemu-work /absolute/accepted-renderer-work \
    /absolute/netbsd-VIRGL_TRIAL.img /absolute/root.ffs \
    /absolute/ANGLE-frameworks /absolute/new-guest-evidence
```

The synthetic root must run the target command above, print exactly one
`EMBER_VIRGL_EXIT=0` only on success, then `EMBER_VIRGL_END` and shut down with
`halt -p`. The supervisor independently requires the consumer's success
and renderer records, rather than accepting this boot marker alone. Keep a
complete matching base userland, including the verifier utilities above.

On 2026-10-08, VirGL trial built from EmberBSD
`103bcbdc2144c5667398ce2de3d65f9759db36e9` negotiated `+virgl -edid` and two
capsets. The unchanged installed libepoxy consumer completed four real EGL 1.5,
GLES 3.0 lifecycles with renderer `virgl`, including shader rejection, triangle
readback and cleanup. The host loaded the accepted renderer and ANGLE frameworks,
reporting `ANGLE Metal Renderer: Apple M3`. Both guest runner and QEMU exited
zero; the input filesystem remained byte-identical.

| Evidence | SHA256 |
| --- | --- |
| VirGL trial kernel image | `f05248b338cc3078b442111846c6a67a97f3d305eb61cbba4db6a309cf915b44` |
| Unchanged epoxy-render executable | `98130892520393aeb42afbeff9fd1ac9b740dc5d5029b285aebd861e041dcb0f` |
| Guest serial log | `2792eec2559db30746b663868769a54ec987f4ab8d717dca36d4aa950fd6a47f` |
| Host provider/Metal log | `7190eabae18d00672eee5a6a1df3ec8b7be99cb3eac978e3bbb54fbdbc0f4b78` |
| Complete input manifest | `731046b87b14650bb0bfc91a3e0db632c21ee6c433a78f7cf2f5aa871f2c0866` |
| Complete output manifest | `1f19e98ac071528abeb7457a25f5a84b1b70d0653b9d19444bfc967ac2786233` |

This is GPU-backed offscreen GLES acceptance for that pair. Visible Wayland
application surfaces, accelerated scanout, VT recovery, live guest reset,
fault recovery and sustained operation remain unverified. It makes no claim
about physical A733 or CM5 acceleration. The host supervisor shares the local
BSD-2-Clause, AI-assisted provenance of the target runner.
