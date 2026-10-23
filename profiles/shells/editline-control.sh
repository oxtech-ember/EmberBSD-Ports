#!/bin/sh
# Build the current dash line-editing dependency and test installed consumers.
# Prepared with AI assistance.
set -eu

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 EMPTY_WORK CURRENT_NCURSES_PREFIX LIBEDIT_ARCHIVE" >&2
    exit 2
fi
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$profile/../.." && pwd)
mkdir -p "$1"
work=$(CDPATH= cd -- "$1" && pwd)
if [ -n "$(find "$work" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    echo "Work directory must be empty: $work" >&2
    exit 2
fi
ncurses=$(CDPATH= cd -- "$2" && pwd)
prefix=$work/prefix
prepared=$work/source
src=$work/build-source
archive=$(CDPATH= cd -- "$(dirname -- "$3")" && pwd)/$(basename -- "$3")
: "${EMBERBSD_SDK_SOURCE:?Set EMBERBSD_SDK_SOURCE to the SDK checkout}"
test -f "$EMBERBSD_SDK_SOURCE/scripts/prepare-libedit.py"
cc=${CC:-gcc}
case "$($cc -dumpfullversion)" in 16.*) ;; *) echo 'GCC 16 is required.' >&2; exit 2 ;; esac
test ! -e "$src" || { echo "Source directory already exists: $src" >&2; exit 2; }
test -f "$ncurses/lib/libncursesw.so" || { echo 'Current wide ncurses shared library is required.' >&2; exit 2; }
case "$("$ncurses/bin/ncursesw6-config" --version)" in
    6.6|6.6.*) ;;
    *) echo 'ncurses 6.6 is required.' >&2; exit 2 ;;
esac
for tool in python3 sha256sum autoreconf make perl valgrind; do command -v "$tool" >/dev/null; done
mkdir -p "$work/records/editline" "$work/logs" "$work/stage"
python3 "$EMBERBSD_SDK_SOURCE/scripts/prepare-libedit.py" \
    --ports "$root" --archive "$archive" --output "$prepared" \
    > "$work/logs/source.json"
cp -R "$prepared" "$src"
cd "$src"
autoreconf -fi > "$work/logs/autoreconf.log" 2>&1
export SHELL_REAL_CC SHELL_CC_RECORDS
SHELL_REAL_CC=$(command -v "$cc")
SHELL_CC_RECORDS=$work/records/editline
CC="$profile/record-cc.pl" CFLAGS='-O2 -g' \
    CPPFLAGS="-I$ncurses/include -I$ncurses/include/ncursesw" \
    LDFLAGS="-L$ncurses/lib -Wl,-rpath,$ncurses/lib" \
    ./configure --prefix="$prefix" --enable-examples > "$work/logs/configure.log" 2>&1
make -j1 > "$work/logs/build.log" 2>&1
make check > "$work/logs/upstream-check.log" 2>&1
make DESTDIR="$work/stage" install > "$work/logs/stage.log" 2>&1
ln -s readline.h "$work/stage$prefix/include/editline/history.h"
test -f "$work/stage$prefix/include/histedit.h"
test -f "$work/stage$prefix/include/editline/history.h"
test -f "$work/stage$prefix/lib/libedit.so"
make install > "$work/logs/install.log" 2>&1
ln -s readline.h "$prefix/include/editline/history.h"

cat > "$work/consumer.c" <<'EOF'
/* Installed libedit consumer. Prepared with AI assistance. */
#include <sys/types.h>
#include <histedit.h>
#include <editline/history.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define CHECK(expr) do { \
	if (!(expr)) { \
		fprintf(stderr, "line %d: %s\n", __LINE__, #expr); \
		exit(EXIT_FAILURE); \
	} \
} while (0)

int
main(void)
{
	int cycle;

	for (cycle = 0; cycle < 32; cycle++) {
		HistEvent event;
		HistEventW wevent;
		History *hist = history_init();
		HistoryW *whist = history_winit();
		Tokenizer *tok = tok_init(NULL);
		TokenizerW *wtok = tok_winit(NULL);
		const char **args, *line;
		const wchar_t **wargs;
		FILE *input = tmpfile(), *output = tmpfile();
		EditLine *edit;
		int count, length;

		CHECK(hist != NULL && whist != NULL && tok != NULL && wtok != NULL);
		CHECK(input != NULL && output != NULL);
		CHECK(history(hist, &event, H_SETSIZE, 8) == 0);
		CHECK(history(hist, &event, H_ENTER, "first") >= 0);
		CHECK(history(hist, &event, H_ENTER, "second") >= 0);
		CHECK(history(hist, &event, H_FIRST) == 0);
		CHECK(strcmp(event.str, "second") == 0);
		CHECK(history(hist, &event, H_SET, -999) == -1);
		CHECK(history_w(whist, &wevent, H_SETSIZE, 8) == 0);
		CHECK(history_w(whist, &wevent, H_ENTER, L"wide") >= 0);
		CHECK(history_w(whist, &wevent, H_FIRST) == 0);
		CHECK(wcscmp(wevent.str, L"wide") == 0);
		CHECK(tok_str(tok, "alpha 'two words'", &count, &args) == 0);
		CHECK(count == 2 && strcmp(args[1], "two words") == 0);
		tok_reset(tok);
		CHECK(tok_str(tok, "'unclosed", &count, &args) == 1);
		CHECK(tok_wstr(wtok, L"wide 'two words'", &count, &wargs) == 0);
		CHECK(count == 2 && wcscmp(wargs[1], L"two words") == 0);
		CHECK(fputs("line input\n", input) >= 0);
		rewind(input);
		edit = el_init("editline-control", input, output, output);
		CHECK(edit != NULL);
		CHECK(el_set(edit, EL_SIGNAL, 0) == 0);
		CHECK(el_set(edit, EL_EDITMODE, 0) == 0);
		line = el_gets(edit, &length);
		CHECK(line != NULL && length == 11 && strcmp(line, "line input\n") == 0);
		CHECK(el_gets(edit, &length) == NULL && length == 0);
		el_end(edit);
		CHECK(fclose(input) == 0 && fclose(output) == 0);
		tok_end(tok);
		tok_wend(wtok);
		history_end(hist);
		history_wend(whist);
	}
	using_history();
	add_history("readline compatibility");
	CHECK(history_length == 1);
	clear_history();
	puts("PASS: 32 installed libedit input/history/tokenizer lifecycles");
	return EXIT_SUCCESS;
}
EOF
"$cc" -std=c11 -Wall -Wextra -Werror -g -I"$prefix/include" "$work/consumer.c" \
    -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -ledit -o "$work/consumer"
TERM=dumb "$work/consumer" > "$work/logs/consumer.log" 2>&1
TERM=dumb valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
    --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
    --error-exitcode=97 --log-file="$work/logs/memcheck.log" "$work/consumer"
"$cc" -std=c11 -Wall -Wextra -Werror -g -I"$prefix/include" \
    "$root/pkgsrc/devel/editline/files/completion-oom.c" \
    "$prefix/lib/libedit.a" -L"$ncurses/lib" -Wl,-rpath,"$ncurses/lib" \
    -lncursesw -Wl,--wrap=realloc,--wrap=calloc,--wrap=free \
    -o "$work/completion-oom"
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
    --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
    --error-exitcode=97 --log-file="$work/logs/completion-oom-memcheck.log" \
    "$work/completion-oom" > "$work/logs/completion-oom.log" 2>&1
make uninstall > "$work/logs/uninstall.log" 2>&1
rm "$prefix/include/editline/history.h"
test ! -e "$prefix/include/histedit.h"
test ! -e "$prefix/lib/libedit.so"
make install > "$work/logs/reinstall.log" 2>&1
ln -s readline.h "$prefix/include/editline/history.h"
TERM=dumb "$work/consumer" > "$work/logs/reinstalled-consumer.log" 2>&1
"$cc" --version > "$work/logs/compiler.txt"
sha256sum "$(readlink -f "$prefix/lib/libedit.so")" "$work/consumer" "$work/completion-oom" \
    > "$work/logs/outputs.sha256"
perl -MJSON::PP -e '
    my @records;
    for my $file (sort glob "$ARGV[0]/records/editline/*.json") {
        next if $file =~ /compile_commands\.json$/;
        open my $fh, "<", $file or die "$file: $!";
        local $/;
        push @records, decode_json(<$fh>);
    }
    print JSON::PP->new->canonical->pretty->encode(\@records);
' "$work" > "$work/compile_commands.json"
python3 "$EMBERBSD_SDK_SOURCE/scripts/prepare-libedit.py" \
    --ports "$root" --validate "$prepared" > "$work/logs/source-validated.json"
echo "PASS: editline staging, installed consumer, Memcheck, removal and reinstallation"
echo "Installed prefix: $prefix"
