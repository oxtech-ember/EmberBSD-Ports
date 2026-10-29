# NTP common source and package

This recipe uses NTP 4.2.8p18 and preserves the active native OS changes in
the common patch set. Native OS consumers build their own integration from
prepared Ports NTP and AutoGen libopts sources. The old OS source copy is not
a fallback.

The package requires `EMBER_NTP_LIBOPTS_SOURCE`, prepared and verified by
`scripts/source-inputs/autogen/source.py`, and the selected
`EMBERBSD_SDK_SOURCE`. After applying NTP's patches, the package replaces the
bundled libopts library source with the verified common tearoff. It retains
only NTP's Makefile.am and generated Makefile.in integration. libevent is the
selected common external dependency; configure refuses its bundled fallback.
The package's normal OpenSSL and editline providers are selected through
pkgsrc buildlink.

An NTP executable starting successfully does not demonstrate synchronized time
or physical reference-clock support. The Oncore command-sequence test uses
ordinary mocked device replies; no receiver was available for hardware testing.
