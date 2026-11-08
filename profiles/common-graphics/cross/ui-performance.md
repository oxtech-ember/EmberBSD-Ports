# Measure a UI rendering path

Measure the application, GPU work, and display presentation separately.
A renderer string establishes selection. It does not measure responsiveness.
Use the current common packages for the target ABI and record their source revisions.
Keep board acceptance in [DevBoards](https://github.com/oxtech-ember/EmberBSD-DevBoards).

## Record the active path

For each run, save the kernel revision, package versions, loaded library paths,
application revision, compiler mode, scene inputs, and backend environment.
Record the actual client device and renderer from its GL or Vulkan context.
For Vulkan, retain physical-device name, vendor/device IDs, device type, and ICD.
Record the compositor's renderer separately from the application's renderer.
Use the current process, because package metadata can differ from loaded libraries.

In an existing Plasma session, query its own session bus:

```sh
/usr/pkg/qt6/bin/qdbus org.kde.KWin /KWin org.kde.KWin.supportInformation
```

The [Plasma session check](../../../probes/plasma-mobile/toolkit/tests/plasma-session/README.md)
checks KWin and plasmashell independently. Its virtual backend is not physical scanout.
The [Qt composed-frame example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/desktop/kwin-frame-check)
checks client and composed pixels; screenshot time is not frame time.

For GTK4, inspect the actual GSK renderer and its device through GTK Inspector.
`GSK_RENDERER=gl` requests GL; it does not prove hardware execution.
The current shared GTK4 recipe disables Vulkan. A Vulkan loader alone cannot enable it.
wxGTK4 GLCanvas uses EGL pbuffers, immutable shared GL textures, and GTK snapshots.
Its [GLCanvas checks](../../../pkgsrc/x11/wxGTK32/tests/README.md#gtk4-glcanvas-contract)
remain separate from complete KiCad execution.

For bsdfb, record whether the consumer selected the native-image interface or
the ordinary backing store. Both copy pixels on the CPU.
Follow the [offscreen contract](qt-bsdfb-vulkan-offscreen.md) for ownership and rotation.
Software Qt Quick, software GL, and software Vulkan are different comparison paths.
Keep their actual renderer and API in the result; do not combine their samples.

## Controlled before and after runs

1. Keep resolution, refresh, scale, orientation, scene, images, and input sequence identical.
2. Keep power policy, CPU/GPU clocks, temperature range, and background load comparable.
3. Change one implementation or option. Record cold-cache and warm-cache runs separately.
4. Use a fixed warm-up count, then at least 1000 frames for tail-percentile comparisons.
5. Repeat A/B/A. Preserve raw per-frame samples and pixel checks with every phase.

Use the same duration and workload for the explicit software comparison.
If a backend cannot display the same scene, report that limitation rather than a speed ratio.
Do not use a screenshot or full pixel readback in each timed frame unless the
production path itself requires it. Capture correctness samples in a separate pass.

| Measurement | Clock or completion source | Boundary |
| --- | --- | --- |
| Application work | Monotonic wall clock and process/thread CPU clock | Input delivery, model work, QML sync and preparation |
| Render submission | Monotonic wall clock and CPU clock | Time inside render/submit calls; blocking includes waits |
| GPU work | Supported GPU timestamp queries | Device execution; check disjoint/availability and timestamp period |
| Readback and CPU copy | Separate monotonic and CPU intervals | Report each copy and any completion wait independently |
| Presentation | Wayland presentation feedback or DRM page-flip timestamps | Record clock ID, output, sequence and hardware flags |
| Input latency | Input event receipt to the frame that contains its effect | Software latency; optical measurement is a separate result |

Read timestamp-query results only after completion. Avoid adding `glFinish`,
`vkDeviceWaitIdle`, or a blocking query read to every production frame.
If GPU timestamps are unavailable, report GPU time as unavailable.
A long submit call or fence wait is not a standalone GPU-time measurement.

For bsdfb, native-copy return measures completion of the CPU write, not scanout.
The current interface has no presentation feedback or vblank timestamp.
Label that interval `copy-complete`, and use optical measurement for visible latency.
Do not report Qt `frameSwapped` or a Wayland frame callback as physical presentation.

## Report results

Report p50, p95, p99, sample count, and maximum for each measured phase.
State the percentile definition, warm-up exclusion, and missing-sample count.
Report presentation intervals separately from application and render durations.
Count compositor-discarded submissions separately from missed refresh periods.
Infer missed periods only for a fixed refresh rate and one unchanged output.
Record variable-refresh and output changes instead of applying that inference.

Report process CPU seconds and elapsed seconds; state whether CPU percent is
normalized to one CPU or all CPUs. Report GPU load only from a supported counter.
Keep unmeasured GPU load and optical latency unavailable, rather than zero.
Source checks, host contracts, target builds, device runs, and sustained operation
are distinct evidence levels. A scheduler refactor alone establishes no UI speedup.

## Software checks without a device

These existing checks use a Ports-patched Mesa source tree and selected native tools:

```sh
"$HOST_PREFIX/bin/python3.15" pkgsrc/graphics/MesaLib/tests/pvr-queue-syncs.py \
    "$MESA_SOURCE/src/imagination/vulkan/pvr_arch_queue.c" \
    --cc "$HOST_PREFIX/bin/clang" --work "$WORK/queue-syncs"
"$HOST_PREFIX/bin/python3.15" pkgsrc/graphics/MesaLib/tests/pvr-bo-reuse.py \
    --mesa "$MESA_SOURCE" --cc "$HOST_PREFIX/bin/clang" --work "$WORK/bo-reuse"
"$HOST_PREFIX/bin/python3.15" pkgsrc/graphics/MesaLib/tests/pvr-bo-reuse.py \
    --mesa "$MESA_SOURCE" --cc "$HOST_PREFIX/bin/clang" \
    --work "$WORK/bo-sanitize" --sanitize
```

Run from the Ports root with explicit absolute input paths and an owned work directory.
These checks model winsys operations. They do not contact a board or run its GPU.
