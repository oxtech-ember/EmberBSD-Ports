# Boost ICU option

The common Boost libraries enable the `icu` option by default. This supplies
ICU to Boost.Regex and Boost.Locale for consumers that need their ICU-backed
Unicode interfaces and locale backend.

A native build graph whose consumers do not use those interfaces may select
`PKG_OPTIONS.boost-libs=-icu` explicitly. This removes the ICU dependency and
passes Boost's separate `--disable-icu` and `boost.locale.icu=off` controls.
Regular Boost.Regex, Boost.Wave and other enabled libraries remain available;
the ICU-backed interfaces and locale backend are unavailable in that package.
Do not substitute this variant for a package that requires those interfaces.
Use the same selected option when resolving and building the graph.

For the common graph exporter, pass the assignment as a repeated make variable:
`--make-variable PKG_OPTIONS.boost-libs=-icu`.

The owner regression `tests/boost-icu-option.py` queries the real pkgsrc metadata
for default, enabled and disabled options. A complete acceptance also builds
the chosen package and exercises its consumers.
