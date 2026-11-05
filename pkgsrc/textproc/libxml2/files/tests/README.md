# Relative default XML catalog

`relocated-catalog.py` copies `lib/libxml2*` and `etc/xml/catalog` into a
temporary prefix, clears `XML_CATALOG_FILES`, and asks `xmlcatalog` to resolve
a catalog entry through the default system catalog. The library must use the
catalog next to itself, not the build-time absolute `XML_SYSCONFDIR`. An
explicit `XML_CATALOG_FILES` override remains authoritative and is checked
separately.
