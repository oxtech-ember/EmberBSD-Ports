# Dawn source bundle

The ONNX Runtime 1.31.0 `cmake/deps.txt` pins Dawn
`v20260916.214021` (SHA-1 `514e914f23a0787213c89eed879f74b5e275690d`).
`dawn-sources.json` identifies that archive and the 19 source trees selected
by Dawn's `tools/fetch_dawn_dependencies.py` from that version's `DEPS`.
Each source is downloaded from its upstream repository at the exact commit.

Chromium's generated git archives include varying timestamps. For each of
those inputs, the manifest therefore pins a SHA-256 of its sorted regular
files: `path`, NUL, normalized mode (`644` or `755`), NUL, SHA-256 of file
contents, newline. The assembly tool rejects unexpected members, duplicate
paths, and a different tree hash. It writes sorted Dawn files followed by
the manifest's dependency trees, with fixed ownership, mode and timestamps.
The resulting source bundle contains the upstream files and their licenses;
it contains neither Git metadata nor macOS AppleDouble files.

From this directory, using the selected native SDK Python:

```sh
python3 assemble-dawn.py --inputs /path/to/dawn-inputs \
    --output /path/to/ort-dawn-v20260916.214021-sources.tar.gz --fetch
```

The expected bundle SHA-256 is
`c7154feb8d5dbd1dea8418106c3d32f3ec4c4cfc63d97e0ae869bcf313747eab`.
The source bundle is published in the [pinned release](https://github.com/oxtech-ember/EmberBSD-Ports/releases/tag/onnxruntime-dawn-v20260916.214021).
The package Makefile uses that release asset URL.
Normal package builds verify the published bundle with `distinfo` and do not
fetch submodules or run this assembler.

The previously used local bundle contained AppleDouble files and a Windows-only
DirectX checkout with CRLF differences from the pinned upstream source. The
new bundle uses upstream bytes; a package build and target acceptance are
separate from assembly validation.
