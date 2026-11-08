# Fontconfig prefix-owned defaults

The official GitLab tag API confirms 2.18.3 (2026-08-06) as the current stable
release: [upstream release](https://gitlab.freedesktop.org/fontconfig/fontconfig/-/releases/2.18.3).

On Darwin, NetBSD and Linux, where Meson verifies `dladdr` and `Dl_info`, a private data
anchor locates the loaded `libfontconfig.so[.*]` or `libfontconfig*.dylib`.
When its directory matches the configured prefix-relative library-directory
suffix, compiled default paths under that prefix follow the library. This
includes the default configuration, templates, cache and fallback font paths.
Missing relocated files do not cause a search in the former producer prefix.

The fallback XML is built from the same defaults and XDG elements, escaping
runtime paths before handing them to the existing XML parser. Ordinary user
XML is not rewritten. Explicit `FONTCONFIG_FILE`, `FONTCONFIG_PATH`, XDG
overrides and paths configured outside the installation prefix retain their
upstream meaning. Static executables, unsupported loaders, renamed libraries
and explicitly different library-directory layouts keep configured defaults.
`FcConfigSetSysRoot` keeps its existing target-root semantics.

Package-owned XML and install hooks still use the SDK's existing signed text
relocation/deferred-hook contract. The library does not modify configuration
files or relocate arbitrary user paths. Loader dependencies are included in
the Meson library dependencies and common buildlink for static consumers.

Run the causal native check with the selected SDK Python:

```
python3 pkgsrc/fonts/fontconfig/tests/relative-defaults.py \
    /absolute/prefix/lib/libfontconfig.so.1 --producer-prefix /absolute/prefix
```

It copies the native library to a temporary prefix containing Unicode and an
XML-special character, and exercises configuration-file selection, environment precedence,
external paths, template scanning, default cache insertion and fallback XML.
Its fixture uses this recipe's `etc/fontconfig`, `share/fonts/X11` and native
prefix-local `var/cache/fontconfig` layout. Dependencies may still load from the
original prefix. It does not compile code or modify the supplied installation.

The old 2.18.3nb3 library fails by reading the producer configuration instead of
the relocated one. The source patch and Meson syntax have been checked;
compilation, the fixed runtime, static consumers, full signed-package lifecycle
and target execution remain unverified.
