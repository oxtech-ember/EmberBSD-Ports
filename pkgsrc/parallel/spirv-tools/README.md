# SPIRV-Tools source consumers

`share/spirv-tools/generated/core_tables_header.inc` is an internal build input,
not public ABI. Upstream `utils/ggt.py` generates it during the ordinary package
build from the selected SPIRV-Headers grammars. Consumers of internal headers
must use the matching patched SPIRV-Tools source and package archives together
with this table and the same selected SPIRV-Headers. The upstream generator is
distributed under Apache-2.0; the grammars retain their upstream provenance.
