# Cinnamon 6.6 stable source control

The stable source set in `sources.tsv` uses Cinnamon 6.6.9 and the matching
6.6 component releases. CJS 140.1 uses the common SpiderMonkey 140 ESR
provider. The source set keeps the current common GTK 3 provider.
These source pins do not establish a complete package set or session.

The earlier development probe used Cinnamon 6.7 snapshots and GTK 4
adaptations. The stable control does not carry its removed decoration code,
no-op locale implementation, disabled tests, or private host paths.

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
These operations follow the [POSIX interface](https://pubs.opengroup.org/onlinepubs/9799919799/functions/uselocale.html).
Returning `LC_GLOBAL_LOCALE` without selecting the requested locale does
not implement this interface. The full CJS and Cinnamon session remain
blocked on this interface and their separate package/runtime checks.
