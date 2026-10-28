# Shared esbuild provider

The upstream Go executable and official matching npm JavaScript API are built
and installed together. The JavaScript API resolves the executable relative to
its installed module, with no npm platform binary, postinstall or download.
Upstream’s explicit `ESBUILD_BINARY_PATH` override remains available; build
callers must select it explicitly or sanitize the inherited environment.
The shared Go dependency uses the current `golang.org/x/sys` archive and the
selected Ports Go compiler. `lang/typescript` uses the same version.

To check a native staged package or installation, run `tests/api.js` with the
selected Node interpreter and the staged prefix as its first argument. It
checks the binary version, module metadata, synchronous transform, async build
and the module's executable link. Cross packages require target runtime tests.
