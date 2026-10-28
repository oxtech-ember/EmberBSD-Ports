# Common V8 source

This recipe provides a single patched V8 source tree. Node and Chromium-based
consumers select their own build configuration and generate their own ABI
artifacts. The package itself does not provide a V8 binary.

The patch set combines applicable NetBSD pkgsrc Node and Chromium changes with
Electron's V8 patches. External Abseil remains owned by `devel/abseil`; its ELF
version handling is already carried there. The BSD sanitizer detection remains
upstream so sanitizer-aware V8 behavior is not hidden.

Electron's `build_warn_instead_of_abort_on_builtin_pgo_profile_mismatch.patch`
is deliberately not applied globally: it changes a strict profile mismatch
into a warning. The selected Node and Electron builds currently use no V8
builtin profile; when one is selected, it must match the build and the upstream
strict check remains enabled. The Chromium `tools/run.py` substitution using a
fixed `@WRKSRC@/out/Release` and replacing the environment is not applied;
consumer build outputs must supply their actual loader paths.

The source producer and verification interface are documented in
[`scripts/source-inputs/v8`](../../../scripts/source-inputs/v8/README.md).
