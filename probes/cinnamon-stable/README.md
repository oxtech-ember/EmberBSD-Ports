# Cinnamon 6.6 stable port

The stable source set in `sources.tsv` uses Cinnamon 6.6.9 and matching
6.6 component releases. CJS 140.1 uses the common SpiderMonkey 140 ESR
provider. GTK 3 is outside the accepted Cinnamon dependency closure. Keep
GTK 3 out of buildlink dependencies, generated introspection metadata and
runtime package requirements. Port components that still require GTK 3 in
Ports against the current supported stack.

The last packaged Cinnamon Menus revision, 6.6.0nb3, built for EmberBSD/AArch64 with GCC 16.2.0,
GLib 2.90.1, GObject Introspection 1.86.0 and Meson 1.12.1. Its package
includes the CMenu library, GIR and typelib. The port repairs the CMenu
launch callback introspection metadata. CJS 140.1 has focused source and
target-compiler checks, but the full shell and session remain blocked by
the missing libc `uselocale()` interface. The other stable components
still need package recipes and target checks.

The [common Cinnamon Menus recipe](../../pkgsrc/x11/cinnamon-menus/README.md)
is now revision 4. It separates native generators from target GIR data and
exports the public GLib dependency. Source and finite metadata checks pass;
the revision-3 package evidence does not accept a new revision-4 package.

The earlier development probe used Cinnamon 6.7 snapshots and GTK 4
adaptations. It is not the package basis for this stable port.

## CJS thread cleanup

`patches/patch-libgjs-private_gjs-util.c` fixes the actual locale-array
ownership. `gjs_locales_new()` allocates an array of `GjsLocale` structures.
The original destructor treats that array as pointers. It dereferences a
null pointer for an empty element and an invalid pointer for a populated
element. The repaired destructor uses the actual structure address.
This is a local AI-assisted change. It is not submitted upstream.

Use the unmodified 140.1 source and an existing native GLib provider:

```sh
python3 tests/cjs-locales.py /absolute/cjs-140.1 /absolute/new-checks \
  --pkg-config /absolute/native/bin/pkg-config \
  --pkg-config-libdir /absolute/native/lib/pkgconfig:/absolute/native/share/pkgconfig
```

The test extracts the actual structure and four unchanged helper bodies.
It applies the production patch to a disposable copy. It checks empty,
one-element, complete-array and thread-exit cleanup through the original
callback ABI. The baseline must fail all four cases. The candidate must
pass. Both repeat under ASan/UBSan. Darwin has no supported LeakSanitizer
in this compiler; the result records that limit explicitly.

The same extracted source is compatible with GCC16 target compilation and
execution. This focused contract does not establish a complete CJS build.
See [the validation boundary](VALIDATION.md).

## Required operating-system contract

CJS 140.1 calls POSIX `uselocale()` from `gjs_set_thread_locale()`.
The selected EmberBSD libc provides `newlocale()`, `duplocale()` and
`freelocale()`, but it does not provide `uselocale()`.
A complete port needs the per-thread locale selector in the operating
system, including its query operation, previous-locale return value,
`LC_GLOBAL_LOCALE` selection, and the locale lifetime rules.
The [thread-locale probe and acceptance contract](LOCALE.md) check these
operations independently of CJS, including rejection of a no-op selector.
These operations follow the [POSIX interface](https://pubs.opengroup.org/onlinepubs/9799919799/functions/uselocale.html).
Returning `LC_GLOBAL_LOCALE` without selecting the requested locale does
not implement this interface. The full CJS and Cinnamon session remain
blocked on this interface and their separate package/runtime checks.
