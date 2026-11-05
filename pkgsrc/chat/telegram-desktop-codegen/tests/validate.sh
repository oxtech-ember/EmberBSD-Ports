#!/bin/sh
set -eu
[ "$#" -eq 2 ] || { echo 'usage: validate.sh NATIVE_CODEGEN_DIR TELEGRAM_SOURCE_DIR' >&2; exit 2; }
tools=$1
src=$2
out=$(mktemp -d "${TMPDIR:-/tmp}/ember-codegen-check.XXXXXX")
trap 'rm -rf "$out"' EXIT
trap 'exit 1' HUP INT TERM
printf 'output: %s\n' "$out"
mkdir -p "$out/lang" "$out/emoji" "$out/styles"
"$tools/codegen_lang" "-o$out/lang" "$src/Telegram/Resources/langs/lang.strings"
test -s "$out/lang/lang_auto.h"
"$tools/codegen_emoji" "-o$out/emoji" "$src/Telegram/lib_ui/emoji.txt" "$src/Telegram/lib_ui/emoji_suggestions/emoji_autocomplete.json"
test -s "$out/emoji/emoji.h"
"$tools/codegen_style" "-I$src/Telegram/lib_ui" "-I$src/Telegram/Resources" "-o$out/styles" "-t$out/styles/widgets_style" "-w$src/Telegram/lib_ui" "$src/Telegram/lib_ui/ui/widgets/widgets.style"
test -s "$out/styles/style_widgets.h"
echo 'PASS: native Telegram language, emoji and style generators'
