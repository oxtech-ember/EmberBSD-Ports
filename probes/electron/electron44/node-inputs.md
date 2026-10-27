# Chromium WebUI Node inputs

The Chromium pin `dd78960ccd8a03a2fe1f629543d27783885b78e9` declares
`third_party/node/node_modules` as a separate GCS source input. Git-only source
acquisition does not obtain it. Its DEPS metadata is:

- Bucket: `chromium-nodejs`.
- Object: `faaf73cc8ff7b0b2f0d984d6cedcf758e006f57a`.
- Generation: `1781805676756361`.
- Size: 11,320,770 bytes.
- SHA256: `a298af5fafd358179d6aec9a42f667902dbcdb03a42ee4a87a1bff83515e96b9`.

The [pinned DEPS](https://chromium.googlesource.com/chromium/src/+/dd78960ccd8a03a2fe1f629543d27783885b78e9/DEPS)
is the authority for these bytes. The archive contains 303 package manifests.
It is not a complete selected build-tool contract. It includes the old
`@rollup/wasm-node` binary as well as JavaScript, declaration and license data.
Do not expose its old Rollup provider after selecting the shared native recipe.

## Consumer mapping

Paths below are relative to the acquired Chromium source root. These are
actual source imports; the final GN/Ninja graph must establish which targets
and actions the Electron distribution selects.

| Consumer | Input | Required integration |
|---|---|---|
| `ui/webui/resources/tools/bundle_js.py` | `node_modules.PathToRollup()` | Bind the shared `devel/rollup` provider. |
| `tools/typescript/ts_library.py`, `ts_definitions.py` | `node_modules.PathToTypescript()` | Bind the shared native TypeScript CLI and check its generated tsconfig files. |
| `ui/webui/resources/tools/minify_js.js` | Terser `dist/bundle.min.js` | Use one current shared Terser recipe and its dependency closure. |
| `tools/polymer/css_minifier.js` | PostCSS and postcss-minify | Use shared recipes; retain the consumer's transform behavior. |
| `tools/typescript/tsconfig_base.json` | `@types/trusted-types` | Preserve the declaration contract explicitly. |
| WebUI Lit resources | `lit`, `lit-html`, `lit-element`, `@lit/reactive-element` | Retain the selected resource and declaration inputs, including their licenses. |
| `ui/webui/resources/tools/eslint/` | TypeScript JS API, typescript-eslint, esquery, eslint-plugin-lit | Migrate selected API consumers; TypeScript 7 is not a drop-in replacement for `lib/typescript.js`. |
| `ui/webui/resources/tools/lit_template_formatter/` | TypeScript JS API and parse5 | Check whether the graph selects these developer tools before adding build dependencies. |

`third_party/node/node_modules.py` also names ESLint, Stylelint, SVGO and
`ts-proto` entry points. An entry point alone does not prove an Electron
`electron_dist_zip` dependency. Preserve declarations and inspect the generated
graph instead of fetching every developer or test tool automatically.

## Upstream transformations

The pinned `third_party/node/update_npm_deps` applies six patches before
filtering and publishing its archive: d3 declarations, Lit HTML, Lit reactive
element, trusted-types, TypeScript DOM declarations and ts-poet. Its
`npm_include.txt`, `npm_exclude.txt` and `lit_include.txt` select the payload.
The recipe must preserve or deliberately migrate each selected behavior.
Copying only `package.json` or running an unpinned npm install loses that input.

The TypeScript patch changes trusted HTML/script URL setters and narrows
`HTMLElement.hidden` to boolean. Those changes need consumer checks against the
new shared declaration provider; do not silently edit a private compiler copy.
The archive remains a source reference while these bindings are implemented.
No full WebUI or Electron build is established by the archive inventory.

## Shared CLI selection

The ordered `gn-shared-node-providers.patch` binds `PathToRollup()`,
`PathToTypescript()` and DevTools `rollup_path()` to explicit
`EMBERBSD_HOST_ROLLUP` and `EMBERBSD_HOST_TYPESCRIPT` JavaScript entries.
Node remains the selected native executor. Missing/empty/relative explicit
entries fail; absent selections retain upstream standalone defaults.

The recipe's [selector](files/node-providers.py) consumes SDK host-prefix API2
roles `rollup` and `tsc`. It verifies the ordinary shared package layout and
matching TypeScript entry/backend version and returns the actual package files
for GN inputs. The native TypeScript backend and its standard `.d.ts` files
are included, as is Rollup's native addon. Paths escaping the selected prefix
are refused. This reads installed packages, without copying a compiler into
the source tree or constructing another node_modules toolchain.

`emberbsd_node_provider_inputs` retains those package files as Ninja inputs.
`emberbsd_typescript_definitions` is separately passed to the existing missing
declaration dependency check. It does not add every standard library to the
TypeScript project: the actual tsconfig still selects DOM/WebWorker libraries.
Ordinary application `definitions` and their validation are unchanged.

The regression runs actual GN/Ninja Node version, WebUI bundle and TypeScript
library actions, including JS/declaration output and bundle execution. It uses
only the pinned archive's trusted-types declaration files. It checks DevTools
selection, malformed explicit entries, actual provider inputs and rejection
when standard library dependency declarations are removed. It does not
establish the complete Electron graph, migrate every TypeScript 7 API consumer,
or validate Chromium's full DOM declaration adaptation.

```sh
/absolute/native-prefix/bin/python3.15 -B -I -S \
  probes/electron/tests/electron-node-providers.py \
  --source /absolute/prepared-electron/src --work /absolute/new-provider-check \
  --git /absolute/control-git --sdk-source /absolute/EmberBSD-SDK \
  --host-prefix /absolute/native-prefix \
  --node-input-archive /absolute/node_modules-faaf73cc.tar.gz
```

Run against prepared sources before `gn-shared-node-providers.patch`.
