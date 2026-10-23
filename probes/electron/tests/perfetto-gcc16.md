# Perfetto GCC16 regression tests

The typed-proto regression compiles the production
`third_party/perfetto/src/trace_processor/importers/proto/typed_proto_field.h`
with a supported enum and an unsupported enum mode. The supported case must
compile. The unsupported case must still fail with the intended static
assertion; only the unrelated tautological-comparison warning must disappear.
The test checks the generated Perfetto build-flag header from the selected GN
output and writes every object and dependency file under its new work path:
Its overlay-normalization check exercises both exact baseline input and
already-patched input, and verifies that each produces a baseline `before`
overlay and a patched `after` overlay without changing Chromium source.

```sh
python3.15 -E -S probes/electron/tests/perfetto-typed-proto-gcc16.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --ports-root /absolute/Ports --source-root /absolute/chromium/src \
  --gn-out /absolute/chromium/out/Default \
  --patch /absolute/Ports/probes/electron/patches/perfetto-typed-proto-gcc16-dependent-false.patch \
  --cxx /absolute/GCC16-target-g++ --workspace /absolute/SDK-workspace \
  /absolute/NEW_PERFETTO_WORK
```

The production `trace_processor_context.cc` GCC16 translation unit is the
causal before/after regression. The bounded typed-proto fixture checks the
production header's accepted-type result and preserves rejection of an
unsupported schema type. Neither test builds Electron or executes target code.

The GCC16 warning-cleanup regression checks MurmurHash2 output for every length from 0 through 15. The fixed vectors include high-bit bytes and run against both the pinned source and patch overlay with a host C++ compiler. The runner then reads the actual GCC command lines from the selected GN output's Ninja command database. It compiles the production `network_trace_module.cc` and `console_interceptor.cc` translation units before and after the patch with `-Werror`; the baseline must reproduce array-bounds, format-truncation, and null `%.*s` diagnostics. Object and dependency outputs go to a new work directory. The runner does not modify Chromium source, GN output, or sysroot. The console annotation case is compile-checked; the runner does not execute console interception code.

```sh
/absolute/EmberBSD/host-tools/python315/bin/python3.15 -B -I -S probes/electron/tests/perfetto-gcc16-warning-cleanups.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --ports-root /absolute/Ports --source-root /absolute/chromium/src \
  --gn-out /absolute/chromium/out/Default \
  --cxx /absolute/GCC16-target-g++ --sysroot /absolute/target-sysroot \
  --workspace /absolute/SDK-workspace --ninja /absolute/host-ninja \
  --host-cxx /absolute/host-c++ --host-sdk /absolute/selected/MacOSX.sdk \
  --patch /absolute/Ports/probes/electron/patches/perfetto-gcc16-warning-cleanups.patch \
  /absolute/NEW_PERFETTO_WARNINGS_WORK
```

The command requires the source and Perfetto revisions recorded in the runner, the matching SDK workspace sysroot, and generated GN output with NetBSD x64 GCC arguments. Ninja's command database supplies both production command lines; the runner does not read a saved build log. It verifies the patch hash and records command and output hashes in `results.json`.
