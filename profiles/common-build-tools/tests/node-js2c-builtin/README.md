# Node generated builtin preload regression

Use the selected SDK tools and a separate writable Node test work. Run `run.py prepare` with the selected `node_js2c` and, if it is outside the host prefix, its selected `--tool-work` to generate `electron_natives.cc`. Supply `fixture.gypi` to the normal Node GYP configure through `-I`, and set `ember_test_generated_source` to that generated file. Build the Node `cctest` target through the normal selected environment, then run `run.py run` with its absolute path. Both actions take the SDK source, host prefix, work and lock root explicitly.

The GYP input enables the embedder builtin only for `node_base` and `cctest`. The fixture runs the real C++ preload and generated builtin in main and worker environments; its imported ESM module is synthetic. It does not establish Electron renderer behavior.
