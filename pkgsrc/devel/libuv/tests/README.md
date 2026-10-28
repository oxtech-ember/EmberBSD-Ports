# Electron loop integration

The shared libuv recipe retains the pre-existing `uv_loop_option` values and
adds the Electron loop interruption API. The suspend/resume depth is owned by
the loop thread; a suspended embedder must re-read `uv_backend_timeout()`
before it waits again. `uv_async_send()` remains the cross-thread wakeup.

Run the libuv suite's `embed`, `embed_with_external_timer`, and
`embed_with_interrupt_suspended` tests against the built library. Compile and
run `loop-abi.c` against the same headers and library to check the enum ABI and
ordinary nested suspension. Run target binaries only in a compatible target
runtime; a host test does not establish Windows or target runtime behavior.
