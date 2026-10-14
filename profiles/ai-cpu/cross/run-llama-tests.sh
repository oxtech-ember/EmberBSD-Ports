#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed package and local GGUF acceptance.
set -eu
test "$#" = 3 || { echo 'Usage: run-llama-tests.sh PACKAGE MODEL NEW_OUTPUT' >&2; exit 2; }
package=$1 model=$2 out=$3
test "$(uname -s)" = NetBSD && test "$(uname -p)" = aarch64
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
test ! -e "$out" && test ! -L "$out"
test -f "$package" && test -f "$model"
test -z "${LD_LIBRARY_PATH:-}${LD_PRELOAD:-}"
export PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin
export LC_ALL=C
if nc -z -w 2 127.0.0.1 18080; then
    echo 'Acceptance port 18080 is already in use.' >&2; exit 1
fi
mkdir "$out"
uname -a > "$out/platform.txt"
pkg_add "$package"
pkg_info -e llama-cpp-0.6.0nb1
pkg_admin check llama-cpp > "$out/package-integrity.txt"
llama-completion --version > "$out/version.txt" 2>&1
ldd /usr/pkg/bin/llama-completion > "$out/linkage.txt"
grep -q '/usr/pkg/gcc16/lib/libstdc++.so.7' "$out/linkage.txt"
grep -q '/usr/pkg/gcc16/lib/libgcc_s.so.1' "$out/linkage.txt"
/usr/bin/time -l llama-completion -m "$model" -p 'The capital of France is' \
    -n 24 -c 512 -t 2 -ngl 0 --seed 1 --temp 0 --no-display-prompt --no-conversation \
    > "$out/generated.txt" 2> "$out/generation.log"
test -s "$out/generated.txt"
grep -qi Paris "$out/generated.txt"
printf 'not a GGUF model\n' > "$out/invalid.gguf"
if llama-completion -m "$out/invalid.gguf" -n 1 > "$out/invalid.log" 2>&1; then
    echo 'Malformed model was accepted.' >&2; exit 1
fi
pkg_delete llama-cpp-0.6.0nb1
test ! -e /usr/pkg/bin/llama-completion
if pkg_info -e llama-cpp-0.6.0nb1; then echo 'Package remained registered.' >&2; exit 1; fi
pkg_add "$package"
pkg_admin check llama-cpp > "$out/reinstalled-integrity.txt"
llama-completion --version > "$out/reinstalled-version.txt" 2>&1
server=
stop_server() {
    if [ -n "$server" ]; then
        kill "$server" 2>/dev/null || :
        wait "$server" 2>/dev/null || :
        server=
    fi
}
trap stop_server EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
alias=ember-gcc16-smollm2-$$
printf '%s\n' "$alias" > "$out/server-alias.txt"
llama-server -m "$model" --host 127.0.0.1 --port 18080 --alias "$alias" \
    -c 512 -t 2 -ngl 0 --parallel 1 > "$out/server.log" 2>&1 &
server=$!
ready=0
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    kill -0 "$server"
    printf 'GET /health HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n' | \
        nc -w 5 127.0.0.1 18080 > "$out/health.http" 2>/dev/null || :
    kill -0 "$server"
    if grep -q '200 OK' "$out/health.http"; then ready=1; break; fi
    sleep 1
done
test "$ready" = 1
printf '%s' '{"prompt":"The capital of France is","n_predict":16,"temperature":0,"seed":1,"stream":false}' > "$out/request.json"
bytes=$(wc -c < "$out/request.json" | tr -d ' ')
{
    printf 'POST /completion HTTP/1.0\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: %s\r\nConnection: close\r\n\r\n' "$bytes"
    cat "$out/request.json"
} | nc -w 60 127.0.0.1 18080 > "$out/completion.http"
kill -0 "$server"
grep -q '200 OK' "$out/completion.http"
grep -qi Paris "$out/completion.http"
grep -Eq '"tokens_predicted"[[:space:]]*:[[:space:]]*16' "$out/completion.http"
grep -Eq '"model"[[:space:]]*:[[:space:]]*"'"$alias"'"' "$out/completion.http"
kill "$server"
wait "$server"
server=
echo 'PASS: installed GGUF text generation, invalid-model rejection, integrity, removal and reinstallation'
echo 'PASS: loopback HTTP completion and server shutdown'
cat "$out/generated.txt"
