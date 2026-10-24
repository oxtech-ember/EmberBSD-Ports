# Common Poppler provider

The common recipe pins [Poppler 26.10.0](https://poppler.freedesktop.org/).
It requires C++23 and the shared GCC16 toolchain. The core library uses
SONAME 165. The split C++, Qt and header packages use the same source release.

Brotli stream decoding and HarfBuzz font subsetting use the common Ports
providers. GLib, GObject introspection, NSS and GPGME++ remain enabled.
The GPGME++ 2.2.0 recipe requires GPGME 2.2.0. NSS and NSPR use their shared
current recipes. The mutex initialization repair is part of this upstream
release, so the earlier backport is removed.

The existing cross scanner uses native GLib tools and the SDK target query
executor. `tests/gi-paths.sh` checks real pkgsrc metadata and the upstream
CMake introspection rule with scanner fixtures. It checks native selection,
compiler wrappers and literal sysroot path rewriting. Its output describes
the fixture scope. Ordinary package, real target GType queries and installed
PDF printing require separate acceptance.
