# libsecret 0.20.5 for KiCad

The common graphics profile provides `libsecret` for KiCad's C/C++ credential
store integration. The target package retains the shared library, public
headers, `secret-tool`, pkg-config metadata, man page and translations.

The native pkgsrc package keeps its default documentation, Vala and
GObject-introspection outputs. Its `doc` option is enabled by default.
Set `PKG_OPTIONS.libsecret=-doc` to omit only the API reference site and its
gi-docgen dependency. The manual, runtime interfaces and upstream tests remain.
For cross builds, the recipe disables those
optional outputs (`gtk_doc`, `vapi` and `introspection`) and selects
`PLIST.cross`. The C/C++ API does not require the generated reference site,
Vala bindings or typelib. This also prevents host generators from trying to
execute target binaries while creating introspection data.
The older common cross recipe does not support `doc`; the complete Plasma
toolkit recipe supports the option in both modes.

Check an exported common graphics or Plasma tree with the same metadata test:

```sh
BMAKE=/absolute/bmake sh probes/plasma-mobile/toolkit/tests/libsecret-tools.sh \
    /absolute/prepared-pkgsrc /absolute/cross.mk /absolute/new-check
```

This check covers source metadata and generator selection. Package builds,
upstream execution and installed consumers remain separate acceptance checks.

Meson receives host `gdbus-codegen` and `glib-mkenums` paths explicitly. The
`gio-2.0.pc` and `glib-2.0.pc` variables otherwise point into the target
sysroot, where these Linux-hosted build generators cannot run.

The pkgsrc export pins upstream `libsecret-0.20.5.tar.xz` with SHA256
`3fb3ce340fcd7db54d87c893e69bfc2b1f6e4d4b279065ffe66dac9f0fd12b4d`.
The GCC16 AArch64 `libsecret-0.20.5nb4` package was installed in the target
sysroot. Its archive SHA256 is
`b6cca7be9539e1e8575c7c22c2f4e172a4f68c44e93e664514bfaf9db223a693`.
A separate C consumer compiled and linked against the installed package with
the exported pkg-config flags and produced an AArch64 ELF executable. Set
`PKG_CONFIG_SYSROOT_DIR` to the target sysroot so pkg-config rewrites its
`/usr/pkg` include and library paths for the cross compiler.

The D-Bus Secret Service runtime and a full KiCad GUI session remain pending.
