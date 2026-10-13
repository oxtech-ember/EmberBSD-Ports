#!/bin/sh
# Check the real Fcitx diagnose gettext prologue and its original catalog.
set -eu
payload=$1
work=$2
prefix=$3
if [ ! -x "$prefix/bin/bash" ]; then
    echo 'SKIP: installed Bash is missing'
    exit 77
fi
mkdir "$work"
cd "$work"
mkdir -p locale/ru/LC_MESSAGES
"$prefix/bin/msgfmt" --check -o locale/ru/LC_MESSAGES/fcitx5.mo "$payload/fcitx/po/ru.po"
# Keep the complete original startup and translation function definitions.
awk '/^# utility$/ { found=1; exit } { print } END { if (!found) exit 1 }' \
    "$payload/fcitx/data/fcitx5-diagnose.sh" > diagnose-prologue.sh
cat > invoke.sh <<'SCRIPT'
set -e
. ./diagnose-prologue.sh
__test_bash_unicode
declare -f _ | grep 'gettext' >/dev/null
_ 'System Info:'
SCRIPT
# GNU gettext honors LANGUAGE outside the C/POSIX locale. Use an installed
# UTF-8 locale. Missing locale support is a SKIP, never a successful lookup.
chosen=
for candidate in en_US.UTF-8 ru_RU.UTF-8 en_US.utf8 ru_RU.utf8; do
    if LC_ALL=$candidate locale charmap 2>/dev/null | grep -Ei '^UTF-?8$' >/dev/null; then
        chosen=$candidate
        break
    fi
done
if [ -z "$chosen" ]; then
    echo 'SKIP: no supported UTF-8 locale was found'
    exit 77
fi
LC_ALL=$chosen LANGUAGE=ru TEXTDOMAINDIR="$PWD/locale" \
    "$prefix/bin/bash" ./invoke.sh > actual.txt
printf '%s' 'Информация о системе:' > expected.txt
cmp expected.txt actual.txt
printf 'PASS: original Fcitx gettext function and Russian catalog (%s)\n' "$chosen"
