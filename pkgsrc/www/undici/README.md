# Common Undici provider

This package installs the ordinary Undici module and the Node-compatible
`loader.js` in `${PREFIX}/lib/node_modules/undici`. It generates both embedded
llhttp WebAssembly wrappers from the installed common `llhttp-wasi` tool
package; it does not install Undici's bundled llhttp source or binary files.
The recipe needs no Node interpreter to build and the resulting package does
not depend on Node, allowing Node to select this provider without a cycle.

For a native package the loader uses `${PREFIX}`. Cross package builds must set
`EMBERBSD_UNDICI_RUNTIME_PREFIX` to the absolute prefix visible on the target
(for example `/usr/pkg`); the target loader must not contain a host sysroot or
host tool prefix. The EmberBSD cross profile sets it to `CROSS_LOCALBASE`. `EMBERBSD_UNDICI_HOST_PREFIX` selects the native prefix with
`llhttp-wasi` and defaults to `TOOLBASE`.

A Node build selects this loader using upstream
`--shared-builtin-undici/undici-path=<runtime-prefix>/lib/node_modules/undici/loader.js`.
The package supplies a source module; this option does not by itself establish
that the resulting Node binary or target runtime has been tested. Native Node
snapshot builds need a host-visible loader, while target artifacts need the
corresponding target runtime path. Electron's host snapshot and code-cache
integration must also verify on the real BuiltinLoader path that the host
loader or its `createRequire` location is not retained in the target output.
Loading `loader.js` directly is not equivalent to that builtin integration.
