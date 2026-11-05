# OpenType Sanitizer source

`source.py` prepares and verifies the common `fonts/opentype-sanitizer` release
and full Ports patch set. Use the selected SDK Python and its explicit SDK
source, archive, patch tool, and output options; `--help` describes the CLI.
Prepared source does not require the standalone tools or their build graph.
Consumers provide their own build integration and explicitly select features.
