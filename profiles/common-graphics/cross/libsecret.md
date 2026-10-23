# libsecret for KiCad

The common graphics profile uses `libsecret` for KiCad's C/C++ credential
store integration. The canonical [libsecret recipe](../../../pkgsrc/security/libsecret/)
selects libsecret 0.21.8.2. The Plasma toolkit uses the same recipe.

The cross build keeps the shared library, public headers, `secret-tool`,
pkg-config metadata, Secret GIR/typelib, Vala bindings, manual pages and
translations. It needs native Vala and the common GI transport inputs.
The [Plasma toolkit guide](../../../probes/plasma-mobile/toolkit/cross/libsecret.md)
describes the native generators, package options and checks.

Check an exported tree with the metadata test:

```sh
BMAKE=/absolute/bmake sh probes/plasma-mobile/toolkit/tests/libsecret-tools.sh \
    /absolute/prepared-pkgsrc /absolute/cross.mk /absolute/new-check
```

This check covers source metadata and generator selection. Package builds,
upstream execution and installed consumers remain separate acceptance checks.
The D-Bus Secret Service runtime and a full KiCad GUI session remain pending.
