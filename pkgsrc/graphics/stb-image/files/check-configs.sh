#!/bin/sh
# Origin: EmberBSD (AI-assisted). Check upstream single-format configurations.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: CC=/absolute/compiler $0 INCLUDE_DIR" >&2; exit 2; }
: "${CC:?Set the selected compiler}"
case "$CC:$1" in /*:/*) ;; *) echo 'Absolute compiler and include paths required' >&2; exit 2;; esac
for feature in STBI_ONLY_PIC STBI_ONLY_PNG STBI_ONLY_GIF STBI_NO_HDR STBI_NO_LINEAR; do
    printf '#define STB_IMAGE_IMPLEMENTATION\n#include <stb/stb_image.h>\n' |
        "$CC" -std=c11 -Werror=return-type -fsyntax-only "-D$feature" "-I$1" -x c -
done
printf '%s\n' 'PASS: stb_image configuration compilation'
