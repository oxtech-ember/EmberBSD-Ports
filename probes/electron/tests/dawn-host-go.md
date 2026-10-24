# Dawn host Go source generation

Origin: EmberBSD (AI-assisted). The patch applies after the pinned NetBSD
overlay. Its existing source-generator wrapper contains `@GOBIN@`, normally
substituted by pkgsrc before configure. A direct GN build does not execute
that substitution. Both target and host generator actions therefore fail
before Go starts.

`dawn_host_go_path` declares an explicit host executable. The existing Tint
action forwards it with `--go-binary` for either toolchain. An empty GN option
keeps the upstream DEPS-selected CIPD default. An explicit Windows path keeps
its supplied suffix; the default Windows path adds `.exe`. Module-relative
execution, output-directory resolution, forced module mode, disabled CGO,
and generator status remain unchanged. The helper also corrects the inherited
platform-variable typo. No target compiler or target object is changed.

Run `python3 third_party/dawn/tools/python/generate_sources_gn_test.py` from
the patched Chromium root. Seven contracts pass on Darwin CPython3.15. They
cover default Mac/Linux/Windows selection, the inherited BSD/Cygwin mapping,
explicit Windows suffixes, output paths with spaces, module/CGO policy, exit
status, empty-path refusal, and an unknown default host. These are invocation
fixtures; native Windows, Linux, and BSD execution are not claimed.

Both previously failing production generator actions pass with supported
Go1.27.3 darwin/arm64 and local toolchain selection. Each creates 27 outputs
and covers all 26 declared outputs. The two toolchain output sets are byte
identical. All bodies match the pinned generated-source oracle after only
normalizing the first-line copyright year; raw hashes remain recorded. Missing
and empty explicit paths fail without outputs. An initial bounded export
missed two template includes; the corrected export includes the exact pinned
files. Its successful replays supersede that input-staging failure.

The exact GN declaration and action pass four default/explicit argument cases
across both toolchains. Before and after GN formatting checks also pass.
No complete Dawn/Electron link, native BSD host run, or browser acceptance is
established by these generator checks.
