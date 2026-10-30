#!/bin/sh
# Verify the target shared library carries its own math dependency.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 readelf libduktape.so" >&2
    exit 2
fi
output=$("$1" -d "$2")
while IFS= read -r line; do
    case "$line" in
        *NEEDED*"[libm.so."*) exit 0 ;;
    esac
done <<EOF
$output
EOF
echo 'libduktape is missing its libm dependency' >&2
exit 1
