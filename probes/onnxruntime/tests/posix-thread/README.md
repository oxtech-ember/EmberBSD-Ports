# POSIX thread regression controls

These controls test two fixes in ONNX Runtime's private `PosixThread`
constructor. Initialized pthread attributes must be destroyed after success
and on failure. Diagnostics must use the error number returned by pthread
functions, even when `errno` contains a different error.

The generator reads the actual pristine and patched source trees. It copies
the constructor's attribute and thread-creation block verbatim. It also copies
the actual shared `GetErrnoInfo` implementation. Source and block SHA256 values
remain in `generated/source-contexts.json`.

The extracted files contain code by the TensorFlow Authors under Apache 2.0,
with portions copyright Microsoft Corporation. The project also supplies its
MIT license. The generated controls combine those excerpts with the MIT
licensed EmberBSD harness. Their SPDX expression is `MIT AND Apache-2.0`.
The generator preserves both source-file notices in
`generated/ONNXRuntime-SOURCE-NOTICES`. It copies the upstream project license
and complete third-party notices without changes. The latter includes the
Apache 2.0 license text. Hashes remain in `generated/licenses.sha256.json`.

The harness uses real pthread APIs. Linker wrappers inject `ENOMEM` from
attribute initialization and `EAGAIN` from thread creation. A real invalid
stack size returns `EINVAL`. Every case starts with unrelated `errno=ENOTTY`.
The normal and explicit-stack cases create and join a real worker.

```sh
cmake -S probes/onnxruntime/tests/posix-thread -B /absolute/control-build \
  -DORT_PRISTINE_SOURCE=/absolute/pristine-onnxruntime \
  -DORT_SOURCE_DIR=/absolute/patched-onnxruntime \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build /absolute/control-build --parallel 1
ctest --test-dir /absolute/control-build --output-on-failure
```

Ruby is a host build tool. It is not linked into either executable. A cross
build can use the same CMake toolchain as the runtime. Run
`posix-thread-patched` in EmberBSD. It must pass all five cases.

The baseline must exit with status 3 and print the five exact defect results.
The native CTest wrapper checks both conditions. It rejects unrelated crashes
or other failures. The patched program can run under strict Memcheck on a
supported host.

This is a focused source-block contract. It does not test the entire class,
custom thread callbacks, all thread-pool behavior, or a complete runtime.
Installed C/C++ inference and target thread-pool tests provide separate proof.
