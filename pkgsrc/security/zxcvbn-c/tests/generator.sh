#!/bin/sh
# Run with selected native tools and a freshly built common zxcvbn library.
set -eu
[ "$#" -eq 5 ] || { echo 'usage: generator.sh DICTGEN UPSTREAM_DICTGEN WORDS_DIR INCLUDE_DIR LIB_DIR' >&2; exit 2; }
generator=$1
upstream=$2
words=$3
includes=$4
libs=$5
test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=$(mktemp -d "${TMPDIR:-/tmp}/zxcvbn-descriptor.XXXXXX")
trap 'rm -rf "$out"' EXIT
trap 'exit 1' HUP INT TERM
set -- "$words/words-eng_wiki.txt" "$words/words-female.txt" "$words/words-male.txt" "$words/words-passwd.txt" "$words/words-surname.txt" "$words/words-tv_film.txt"
"$upstream" -o "$out/upstream.h" "$@"
"$generator" -o "$out/default.h" "$@"
cmp "$out/upstream.h" "$out/default.h"
"$generator" --descriptor SixWordLists -o "$out/six.c" "$@"
printf 'alpha\nbeta\ngamma\n' > "$out/small.txt"
"$generator" --descriptor SmallWordList -o "$out/small.c" "$out/small.txt"
"$generator" --descriptor StdoutDictionary "$out/small.txt" > "$out/stdout.c"
"${CC:?select the native C compiler}" -std=c11 -I"$includes" -c "$out/stdout.c" -o "$out/stdout.o"
for bad in 9bad bad-name int 'a;touch' '' DictNodes Ranks ChildLocs WordEndBits ChildMap EndCountLge EndCountSml CharSet SizeChildMapEntry NumLargeCounts ND ROOT_NODE_LOC BITS_CHILD_PATT_INDEX BITS_CHILD_MAP_INDEX SHIFT_CHILD_MAP_INDEX SHIFT_WORD_ENDING_BIT CHARSET_SIZE ZXCVBN_DICTIONARY_ABI ZxcvbnDictionaryData ZxcvbnDictionary ZxcvbnDictionaryCreate ZxcvbnDictionaryFree ZxcvbnMatchWithDictionary ZxcvbnMatch ZxcvbnFreeInfo ZxcMatch_t ZxcTypeMatch_t NON_MATCH _reserved user_t bool constexpr typeof size_t int32_t uint64_t uint_least16_t int_fast64_t intptr_t uintmax_t; do
    if "$generator" --descriptor "$bad" -o "$out/invalid.c" "$out/small.txt" >/dev/null 2>&1; then
        echo "accepted invalid C identifier: $bad" >&2; exit 1
    fi
done
if "$generator" --descriptor badmode -b -o "$out/invalid.c" "$out/small.txt" >/dev/null 2>&1; then
    echo 'accepted descriptor in binary mode' >&2; exit 1
fi
"${CC:?select the native C compiler}" -std=c11 -I"$includes" "$test_dir/generated-descriptors.c" "$out/six.c" "$out/small.c" -L"$libs" -lzxcvbn -Wl,-rpath,"$libs" -o "$out/check"
"$out/check"
