#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute the actual native XML generator.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 QTWAYLANDSCANNER NEW_OUTPUT" >&2; exit 2; }
scanner=$1 output=$2
[ -x "$scanner" ] && [ ! -e "$output" ]
mkdir -p "$output"
cat > "$output/protocol.xml" <<'XML'
<protocol name="ember_probe"><interface name="ember_probe" version="1">
<request name="destroy" type="destructor"/>
<event name="value"><arg name="value" type="uint"/></event>
</interface></protocol>
XML
for side in client server; do
    "$scanner" "$side-header" "$output/protocol.xml" > "$output/$side.h"
    grep -Eq 'class[[:space:]]+ember_probe' "$output/$side.h"
done
status=0
"$scanner" client-header "$output/missing.xml" > "$output/missing.h" 2> "$output/missing.log" || status=$?
if [ "$status" != 1 ]; then
    echo "Missing XML must return EXIT_FAILURE (1), got $status." >&2; exit 1
fi
printf '<protocol><interface' > "$output/invalid.xml"
status=0
"$scanner" client-header "$output/invalid.xml" > "$output/invalid.h" 2> "$output/invalid.log" || status=$?
if [ "$status" != 1 ]; then
    echo "Invalid XML must return EXIT_FAILURE (1), got $status." >&2; exit 1
fi
shasum -a 256 "$scanner" > "$output/tool.sha256"
echo 'PASS: native Qt client/server generation and missing/invalid XML rejection'
