# Dawn / Vulkan diagnostics

These optional probes compare Vulkan transfer, compute and ONNX Runtime WebGPU
on a selected adapter. They do not establish general GPU correctness or repair
the underlying memory defect. Run only with a working Vulkan loader and a
compatible LP64 ABI; the scripts validate the ctypes structure sizes at runtime.
The loader defaults to `/usr/pkg/lib/libvulkan.so.1`; pass `--vulkan-library`
for another installation. They require exactly one enumerated physical device;
`--device-name` may additionally require a name substring. They print memory
types and flags: verify the requested memory type was actually selected.

The packaged NetBSD RADV adapter `1002:15d8` has a targeted Dawn restriction
for the two optional mapped-buffer extended-usage features. Direct mapped
storage reads were observed to be incorrect beyond 2 MiB; the Vulkan/OS cause
remains unresolved. The restriction does not alter direct Vulkan. Other WebGPU
upload paths are not covered by this probe.

## Vulkan isolation

From this directory, with the selected native Python:

```sh
python3 vulkan-copy-diagnostic.py --device-name RAVEN2
python3 vulkan-compute-diagnostic.py --variant constant --device-name RAVEN2
python3 vulkan-compute-diagnostic.py --variant add1d --source-memory host --device-name RAVEN2
python3 vulkan-compute-diagnostic.py --variant add1d --source-memory host --staging --device-name RAVEN2
python3 vulkan-compute-diagnostic.py --variant add1d --source-memory device-local --device-name RAVEN2
python3 vulkan-compute-diagnostic.py --variant add2d --source-memory device-local --device-name RAVEN2
```

The transfer probe checks two distinct 4 MiB byte patterns. Compute checks
921,600 float outputs over two submissions: input is 0.5 and every output must
be 1.0. A nonzero exit reports the first mismatch; it is a failure, not an
accepted expected result. On the previously affected Raven2 setup, transfer,
constant, host-only source and staged source passed; both direct mapped local
add variants failed after 2 MiB. A fixed system should pass all variants. The
1D and 2D variants use identical linear indexing with different dispatch shapes.
Source-memory selection requires a matching coherent memory type; unsupported
memory layouts stop with an error rather than silently changing the experiment.
The scripts wait for a Vulkan fence and may block if the driver hangs.

The embedded SPIR-V in the compute probe corresponds to the adjacent GLSL
`.comp` files, built with `glslangValidator -V`; rebuild and compare all bytes
when changing shaders. The diagnostic uses raw Vulkan directly, not Dawn.

## ONNX Runtime CPU/WebGPU

`onnx-add-diagnostic.py` derives a small Add graph from a supplied ONNX model,
retaining its IR and opset metadata; it does not download weights. The source
model's own license and provenance must be respected. For the original tested
YOLO26n source, use the matching version and attribution from its provider;
no model or application-specific asset is distributed here. The synthetic Add
has one float32 input `[1,3,480,640]` and returns its input doubled.

```sh
python3 onnx-add-diagnostic.py /path/to/source.onnx /path/to/new-add.onnx
mkdir -p /path/to/new-profiles
python3 onnx-runtime-diagnostic.py --model /path/to/new-add.onnx \
  --profile-dir /path/to/new-profiles --mode compare --strict --fill 0.5 --expected 1 \
  --vendor 0x1002 --device 0x15d8
```

This requires the target's installed ONNX Runtime C API 31 and WebGPU EP. Pass
`--prefix` if installed outside `/usr/pkg`. The probe obtains the model's input
and output names, tensor types and shapes from the runtime; it supports one
fixed-shape rank-4 float32 input and compares every float32 output. The default
input is a deterministic nonconstant pattern; `--input-file` accepts an exact
little-endian float32 tensor in model layout, and `--fill` selects a constant.
`--output-dir` writes exclusive raw float32 snapshots and JSON shape/name/type
metadata for each output and run, even when a result is nonfinite.
It runs each session twice and rejects nonfinite data, incompatible shapes and
CPU/GPU differences above the chosen tolerances. `--strict` rejects CPU graph
fallback; the profile must show actual WebGPU-executed nodes even without it.
Profiles report per-provider node events. `--expected` checks every output and
is meaningful for the generated Add graph with `--fill 0.5`, not arbitrary
models. For detection models, raw differences may arise from reordered results
with equal or close scores; inspect the saved detections and masks before
attributing a numerical mismatch to the GPU. Dynamic input dimensions and
non-float tensors need another harness.
`onnx-intermediate.py --list` inspects a model and `--node N --output PATH`
creates an exclusive new pruned diagnostic graph without modifying the source.

## Capability restriction checks

Dawn `v20260916.214021` is pinned by `local-ai/onnxruntime` with its `webgpu`
option. The adaptation hides `BufferMapExtendedUsages` and
`BufferMapWriteExtendedUsages` only for NetBSD RADV `1002:15d8`; ordinary
staging remains available. Run the source-level predicate and patch checks from
the Ports repository root:

```sh
CXX=/path/to/native/clang++ python3 pkgsrc/local-ai/onnxruntime/files/test-dawn-map-features.py
```

Target acceptance still requires comparing all outputs of representative ONNX
models on the actual WebGPU provider and checking the intended application.
