# dprint-swc-ext view regeneration

`projection.patch` adapts the upstream generator at dprint-swc-ext commit
`9236c9292cd1f1e56ba2e55d592c69ef30fcaaba` to the selected SWC schema and Node. Apply it to that source tree.
The generated view is carried in the adjacent crate patch; use the same SWC
versions and Cargo patches as the consuming graph. `test.mjs` exercises the
projection and its parent graph with synthetic schemas.

With the selected SDK tools and locks, run these commands offline from the
consumer's locked Cargo graph (replace placeholders with its actual paths):

```sh
RUSTC_BOOTSTRAP=swc_ecma_ast cargo rustdoc --offline --locked --manifest-path "$MANIFEST" -p swc_ecma_ast --lib -- -Z unstable-options --output-format json
RUSTC_BOOTSTRAP=swc_ecma_parser cargo rustdoc --offline --locked --manifest-path "$MANIFEST" -p swc_ecma_parser --lib -- -Z unstable-options --output-format json
CODE_BLOCK_WRITER_ESM="$PREFIX/lib/node_modules/code-block-writer/esm/mod.js" "$NODE" scripts/generate.ts "$TARGET/doc/swc_ecma_ast.json" "$TARGET/doc/swc_ecma_parser.json" "$OUTPUT"
```

`NODE`, Cargo, Rust and code-block-writer come from the selected common host
prefix. Run `test.mjs` with that Node in the patched generator tree.
