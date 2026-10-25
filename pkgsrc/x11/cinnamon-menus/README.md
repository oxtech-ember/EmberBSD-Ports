# Cinnamon Menus source recipe

This is the common Cinnamon Menus 6.6.0nb4 recipe. The normal Ports exporter
includes it without a profile or a second preparation step.
The source archive, four patches, PLIST and GIR regression retain the
[revision-3 package boundary](../../../probes/cinnamon-stable/VALIDATION.md#cinnamon-menus-660nb3).
Revision 4 changes dependency metadata. It has no new package or runtime acceptance.

The public buildlink requires Cinnamon Menus 6.6.0 and exposes GLib for
the installed headers' GIO types. GTK 3 is outside this dependency closure.

| Build mode | GLib GIR data | Scanner and typelib compiler |
| --- | --- | --- |
| Native | Native tool dependency | Native programs |
| Cross | Target build dependency | Native programs with real target GType queries |

Cross builds use the shared
[`gobject-introspection/cross.mk`](../../devel/gobject-introspection/cross.mk)
launcher, target data path and ELF dependency wrapper. Native builds keep
their native discovery paths and do not select a target-query launcher.

## Source and finite metadata checks

Select explicit executables and a new work directory:

```sh
/absolute/python3 -B tests/dependency-roles.py \
  --bmake /absolute/bmake --git /absolute/git --patch /absolute/patch \
  --work /absolute/new-cmenu-check
```

The check runs the real exporter with a finite upstream fixture. It compares
every exported recipe file and rejects a second provider. The bmake checks
evaluate this recipe and the actual shared GI routing include with finite
pkgsrc dependency stubs. They use `-r` and `-V` with an empty command path.
No build target, compiler, generator, SSH query or package tool runs.

Native, AArch64 and amd64 metadata checks pass. Five deliberate faults must
fail: missing target GIR data, missing native GIR data, missing public GLib,
a stale CMenu minimum and cross metadata applied to native builds.
The final unmodified inputs are checked again. `results.json` records the
evaluated variables, failures, source hashes and explicit tool identities.

These are source regression checks, not full pkgsrc graph evaluation or SDK
tool qualification. Ordinary SDK GCC16 package builds, installed consumers,
package lifecycle and target execution remain separate acceptance work.
The existing [`check-gir.py`](tests/check-gir.py) checks actual CMenu GIR output;
the metadata fixture does not produce GIR files or replace that check.
