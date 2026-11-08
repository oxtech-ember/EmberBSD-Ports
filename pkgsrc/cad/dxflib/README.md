# dxflib provenance and KiCad compatibility

Upstream QCAD currently lists dxflib 3.26.4 and licenses it as GPLv2 or later.
The recipe fetches Debian's original-source mirror at
`https://deb.debian.org/debian/pool/main/d/dxflib/`; its archive hash is pinned
in `distinfo`. No C/C++ source is copied into Ports.

KiCad 10.0.8's vendored tree identifies as dxflib 3.17.0. Its source has
formatting and override annotations, plus these behavior/API differences from
3.26.4:

- The KiCad constructor initializes auxiliary parser state; this repair is
  carried as a patch to the common 3.26.4 source.
- The KiCad writer uses bounded `snprintf` and returns before dereferencing a
  null C string; both fixes are retained.
- The KiCad Windows compatibility macro checks whether `strcasecmp` already
  exists; the guarded definition is retained.
- KiCad adds `DL_Dxf::in(FILE*)`, which takes ownership and closes the stream.
  Upstream 3.26.4 instead has `in(std::istream&)`. KiCad's current application
  consumer calls `in(const std::string&)`, so the common provider supports the
  used path API without adding a private FILE wrapper.
- KiCad adds optional `writeDimLinear` parameters and narrows the return types
  of `writeImage` and `writeDictionaryEntry`; current application sources do
  not call these APIs. Upstream's wider return types are kept.

The recipe exports the shared `dxflib::dxflib` CMake target and installs the
upstream public headers and GPL license text.
