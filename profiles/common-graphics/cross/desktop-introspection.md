# Complete text and GTK introspection during cross builds

The common profile keeps introspection enabled for HarfBuzz 14.6.0nb1,
Pango 1.58.2nb3, AT-SPI 2.62.1 and GTK 3.24.52nb4. On 2026-10-12 all four
complete packages passed normal macOS/GCC16 cross packaging and installation
into the common EmberBSD sysroot. No native board compilation is required.

The native scanner/compiler generate metadata. Actual GType queries execute
on CM5 through the [verified query transport](introspection.md). HarfBuzz,
all six Pango namespaces, both AT-SPI/ATK namespaces, and GTK's Gdk, GdkX11
and Gtk queries completed successfully. These are real library executions;
they do not establish a working graphical GTK session or accessibility bus.
The complete upstream widget/accessibility suites remain unrun.

## Portability changes

- Select target X11/Wayland for GTK when cross-building on macOS. Host Quartz
  framework detection applies only when the target OS is Darwin.
- Preserve the GObject library, GIR and typelibs. Native generation tools
  remain separate from target GLib GIR build dependencies. Explicitly disabling
  the package option is still supported; it is not the common-profile default.
- Read target GIR metadata from the sysroot. Canonical scanner include paths
  remain inside the declared buildlink headers. In-tree shared libraries enter
  the temporary query closure; they never replace installed target libraries.
- Explicitly link GDK into GTK's temporary query executable. A cross linker
  does not use host `LD_LIBRARY_PATH` to resolve libgtk's in-tree dependency.
- Use the already verified native Wayland scanner and target protocol XML.
- AT-SPI's manifest matches upstream 2.62.1, including its ATK library version
  and the actual translation set. The absent upstream Lao translation is not
  fabricated or required by the package.

An incremental build after upgrading dependencies can retain old package
identities in pkgsrc's `.*_makevars.mk` snapshots and stale buildlink lists.
Clean the affected consumer after such a dependency update. Do not manufacture
missing headers, copy installed files into the source, or disable introspection.

## Reproduce

Prepare a fresh export with the
[Plasma toolkit recipes](../../../probes/plasma-mobile/toolkit/README.md) and the
common cross MAKECONF. Configure
all required real target-query inputs as described in the introspection guide.
Build/install HarfBuzz, Pango and AT-SPI before GTK using ordinary `bmake package`
and package installation. The exporter checks original source and patch hashes.

```sh
BMAKE=/absolute/bmake sh ../tests/desktop-introspection-selection.sh \
    /absolute/prepared-pkgsrc /absolute/cross.mk /absolute/new-test
```

The check queries the real four recipes. It covers cross/native defaults,
explicit option removal, missing-query rejection, target Wayland/X11 and
native Darwin Quartz selection. Fresh export, source SHA256 and all patches
at zero fuzz passed. The changes are build descriptions and packaging;
no new C/C++ adaptation was introduced in this step. They do not establish
whole-source static-analysis or Valgrind coverage.

| Complete package | SHA256 |
| --- | --- |
| harfbuzz-14.6.0nb1 | `1da1a776aa94d34f183a025923784640382e053fad34d0366d5c0632cf6660f9` |
| pango-1.58.2nb3 | `42641461335dc258bfbd5f4efff2ee9c81708c6e14f3ee55b02c54744fd57cc6` |
| at-spi2-core-2.62.1 | `78b03bf0e473383fbe2feb28dedeea8ae09b420d93bce7e594fccf2217e729fd` |
| gtk3+-3.24.52nb4 | `3d654040f8ed98d6726cfc0bb262eb0da8281b389cda7389410043ee1df1a347` |
