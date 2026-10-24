# Optional launcher for linking

The [linker-launcher patch](../patches/linker-launcher.patch) adds optional
command prefixes to the unbundled GCC target toolchain family and the Apple
toolchain families. Empty arguments preserve the existing commands.

The prefixes apply to C/C++ executable, shared-library and module links.
They also apply to the complete Rust commands that perform final native
links: `rust_bin`, `rust_cdylib`, `rust_dylib` and `rust_macro`. Rust code
generation for those outputs runs within the launcher. C/C++ and Objective-C
compilation, assembly, static archives, Rust rlibs and Rust static libraries
retain their commands. The separate unbundled GCC `host` family stays
unchanged. The Apple argument covers the Mac host toolchains separately.

The generic `gcc_toolchain` template accepts `linker_launcher` as an optional
invoker parameter. Its existing forwarding templates pass that parameter to
the derived toolchains. The Apple toolchains use `apple_linker_launcher`.
Their `TOOL_VERSION` assignment remains before the launcher. No target ABI,
compiler flags, response-file contents or linker flags change.

## Configure a shared link context

Use an explicit SDK source that provides `scripts/link-launcher.py`.
The interface is available at SDK revision
`ea8666e66739ca80fa9834ea1668930ea359dd0c`.
Set absolute paths to the selected host Python, SDK and object workspace.
When a cross-build uses the unbundled GCC target and Apple host toolchains,
add these arguments:

```gn
concurrent_links = 1
unbundle_linker_launcher = "\"/absolute/host/python3\" \"/absolute/SDK/scripts/link-launcher.py\" --lock-root \"/absolute/obj\" --context \"/absolute/obj/coordination/heavy-link\" --"
apple_linker_launcher = unbundle_linker_launcher
```

Set only the applicable argument when the build selects one toolchain family.
Use shell quoting inside the GN string for path names that require it.
Configure other concurrent producers with the same SDK launcher, lock root
and context. The ordinary GN link pool limits links in one Ninja process.
The SDK context coordinates the participating producers.
The launcher retains the context until its owned command group is drained.
Do not replace the selected C or C++ compiler with this launcher.

## Compare captured production rules

The [rule checker](check-linker-launcher.py) uses only Python's standard
library. It reads captured Ninja files and executes no build commands.
Capture the generated `toolchain.ninja` files with their relative paths before
and after enabling the prefix. Include the after `build.ninja`, which defines
the link pool. Keep the source, toolchain and other build inputs equivalent.

```sh
python3 probes/electron/tests/check-linker-launcher.py --self-test
python3 probes/electron/tests/check-linker-launcher.py \
  --before /absolute/captured-before \
  --after /absolute/captured-after \
  --launcher '"/absolute/host/python3" "/absolute/SDK/scripts/link-launcher.py" --lock-root "/absolute/obj" --context "/absolute/obj/coordination/heavy-link" --' \
  --wrap toolchain.ninja \
  --wrap clang_arm64/toolchain.ninja
```

Pass the exact prefix text found in the generated Ninja commands, including
its quotes. Repeat `--wrap` for every participating derived toolchain file.
The checker requires unchanged rules in all unselected toolchain files.
It checks the C/C++ and available Rust native-link prefixes, compiler and
archive commands, rule metadata, and a single link-pool depth of one.
Use `--link-pool` if the generated pool has a different name.
The self-tests reject compiler changes, missing Rust guards, incorrect Apple
environment ordering, changed unselected toolchains and invalid pool depths.
This check does not execute the SDK launcher or prove runtime behavior.

## Verification scope

The GCC/unbundle files were exported at Chromium source revision
`2bc373d14b1b7befc5efc0ba225eff44136b6193`. The Apple file was exported at
`10f01bf13ce9f3f2cbfcade44fa26e403ff54888`.
The combined three-file patch applies and reverses with `patch -F0` and
exact byte comparisons.

A finite GN 2486 harness imported the complete unbundle file. It used the
actual optional-linker assignment, all six actual Rust tool definitions and
all three actual GCC forwarding templates. Its C/C++ rule bodies were a
minimal harness. Eleven generation cases checked default and explicit-empty
command identity, the four target and four separate host families, quoted
prefixes, and retained NetBSD target `READELF` checks. Host-prefix and
Rust-link-bypass mutations were rejected.

A second GN harness used the complete actual Apple toolchain file, including
all compiler, archive, C/C++ link, Rust and forwarding definitions. Its imports
and tool-mtime provider supplied controlled fixture values. Nine cases
checked all four Apple families, empty argument identity, quoted prefixes,
both LLVM-ar and native libtool archive routes, and the seven final-link rule
types. Incorrect environment ordering and a Rust-macro bypass were rejected.

Both harnesses checked unchanged compilation, assembly, static archives,
Rust rlibs and Rust static libraries. Neither harness generated the complete
production Chromium graph or executed a compiler or linker.

`gn format --dry-run` returned 2 for the patched unbundle file. This is not a
formatting pass. Production graph generation, production command comparison
and actual SDK launcher execution remain separate checks. Complete those
checks before starting the production build with the new launcher.
A complete Electron build remains a separate acceptance gate.
