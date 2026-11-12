# Betaflight Configurator package

The pinned `betaflight-configurator-2026.6.2-ember1.asar` is an external,
checksum-verified input containing the upstream 2026.6.2 Vite WebUI. The
package does not compile that WebUI from upstream source, and the distfile
has no download location in this recipe: the builder must supply it in
`DISTDIR/betaflight-configurator/`. Its checksum verifies the supplied
archive, not independent reproducibility of the original WebUI build.

The normal pkgsrc build uses the selected native Node and `@electron/asar`
to extract that archive, replace the three shell files from `files/`, and
repack it. The helper verifies unchanged archive contents and the exact shell
files before replacing the output. The original archive remains unchanged.
A reproducible producer for the [upstream WebUI](https://github.com/betaflight/betaflight-configurator)
is not yet provided; changing the WebUI requires establishing that source
build and its dependencies separately.

Run the shell regressions with the selected native Node:

```sh
"$EMBERBSD_HOST_NODE" tests/serial.cjs
"$EMBERBSD_HOST_NODE" tests/app-paths.cjs
```

The tests exercise mocked Electron events and URL policy; they do not establish
that a physical serial device or the graphical chooser works on EmberBSD.
