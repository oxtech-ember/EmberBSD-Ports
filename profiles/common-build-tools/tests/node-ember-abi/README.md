# Native-addon ABI regression

Use the selected SDK compiler and a fresh staging directory containing the
Node package's installed `include/node` headers and `config.gypi`. Compile
`addon.cc` twice using those headers and C++20: once normally and once with
`-DNODE_EMBEDDER_MODULE_VERSION=137` as a deliberately mismatching ABI. Compile
`napi.c` with `-DNODE_GYP_MODULE_NAME=ember_abi_fixture`. Link each as a Node
addon with the selected platform's linker and addon flags. Do not reuse a
foreign prebuilt binary. Run the selected Node runtime on `runtime.cjs` with
absolute paths to the matching, mismatching and Node-API addons, in that order.

The test checks the EmberBSD standalone module ABI, native addon loading,
rejection of the deliberately mismatched module, and the separate Node-API
load path. Run node-gyp separately with `--nodedir` pointing at the staged
prefix to verify its actual headers and `config.gypi`; use the matching SDK
compiler, Python and platform metadata. For Electron use the Electron header
and runtime instead: its module ABI is distinct.
