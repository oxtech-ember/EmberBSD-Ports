#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# A stalled HTTPS site must end within the pkgsrc fetch stall timeout, so
# that the pkgsrc fetch script tries the next site. A slow site that still
# sends data must not be cut off. FETCH is a fetch built from net/fetch
# with net/libfetch of the export (patches/libfetch-https-stall.patch).
# Upstream fetch set no timeout for https URLs, and libfetch called
# SSL_read without a poll; such a fetch hangs here until the deadline.
set -eu
[ "$#" = 7 ] || { echo 'usage: fetch-stall-fallthrough.sh BMAKE PKGSRC MAKECONF PYTHON OPENSSL FETCH NEW_WORK' >&2; exit 2; }
bmake=$1 pkgsrc=$2 makeconf=$3 python=$4 openssl=$5 fetch=$6 work=$7
for path in "$bmake" "$pkgsrc" "$makeconf" "$python" "$openssl" "$fetch" "$work"; do
    case "$path" in /*) ;; *) echo 'absolute paths required' >&2; exit 2;; esac
done
stall=5
deadline=$((stall * 6))
mkdir "$work"
mkdir "$work/distfiles"
before=$("$bmake" -C "$pkgsrc/net/fetch" MAKECONF="$makeconf" FETCH_TIMEOUT=$stall \
    -V '${_FETCH_BEFORE_ARGS.fetch}')
case " $before " in *" -T $stall "*) ;; *) echo "FETCH_TIMEOUT gives no fetch -T: $before" >&2; exit 1;; esac

"$openssl" req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=127.0.0.1 \
    -addext subjectAltName=IP:127.0.0.1 -keyout "$work/key.pem" -out "$work/cert.pem" \
    > "$work/openssl.log" 2>&1
cat > "$work/server.py" <<'PYEOF'
import http.server, ssl, sys, threading, time
work, stall = sys.argv[1], int(sys.argv[2])
body = bytes(range(256)) * 4096

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args):
        pass
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.path.startswith('/stall/'):
            # Headers and the first data, then no progress.
            self.wfile.write(body[:4096]); self.wfile.flush()
            time.sleep(3600)
        elif self.path.startswith('/slow/'):
            # Progress at intervals below the stall timeout, longer in total.
            chunks = stall * 2
            size = len(body) // chunks + 1
            for start in range(0, len(body), size):
                self.wfile.write(body[start:start + size]); self.wfile.flush()
                time.sleep(stall / 3)
        else:
            self.wfile.write(body)

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
server.daemon_threads = True
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(work + '/cert.pem', work + '/key.pem')
server.socket = context.wrap_socket(server.socket, server_side=True)
open(work + '/body', 'wb').write(body)
open(work + '/port.new', 'w').write(str(server.server_address[1]))
import os; os.rename(work + '/port.new', work + '/port')
server.serve_forever()
PYEOF
"$python" -B "$work/server.py" "$work" "$stall" > "$work/server.log" 2>&1 &
server=$!
trap 'kill -TERM $server 2>/dev/null || :' EXIT
n=0
while [ ! -f "$work/port" ]; do
    n=$((n + 1)); [ $n -lt 100 ] || { echo 'test server did not start' >&2; exit 1; }
    sleep 0.1
done
port=$(cat "$work/port")

# run NAME SITE...: the pkgsrc fetch script as fetch.mk runs it, with a deadline.
run()
{
    name=$1; shift
    start=$(date +%s)
    set -m
    ( cd "$work/distfiles" && env SSL_CERT_FILE="$work/cert.pem" FETCH_CMD="$fetch" \
        FETCH_BEFORE_ARGS="$before" FETCH_OUTPUT_ARGS=-o FETCH_RESUME_ARGS=-r \
        sh "$pkgsrc/mk/fetch/fetch" -v "$name" "$@" ) > "$work/$name.log" 2>&1 &
    job=$!
    set +m
    while kill -0 $job 2>/dev/null; do
        if [ $(($(date +%s) - start)) -gt $deadline ]; then
            kill -TERM -- -$job 2>/dev/null || :
            kill -TERM $job 2>/dev/null || :
            echo "$name: no result within ${deadline}s; a stalled site held the fetch" >&2
            exit 1
        fi
        sleep 1
    done
    wait $job || { echo "$name: fetch failed" >&2; cat "$work/$name.log" >&2; exit 1; }
    elapsed=$(($(date +%s) - start))
    cmp -s "$work/distfiles/$name" "$work/body" || { echo "$name: wrong content" >&2; exit 1; }
}

run stalled.bin "https://127.0.0.1:$port/stall/" "https://127.0.0.1:$port/good/"
grep -q 'Unable to fetch expected file stalled.bin' "$work/stalled.bin.log" ||
    { echo 'the stalled site was not tried first' >&2; exit 1; }
[ $elapsed -le $((stall * 3)) ] || { echo "fallthrough took ${elapsed}s" >&2; exit 1; }
stalled=$elapsed
run slow.bin "https://127.0.0.1:$port/slow/"
[ $elapsed -gt $stall ] || { echo "the slow site took only ${elapsed}s" >&2; exit 1; }
echo "PASS: a stalled HTTPS site fell through in ${stalled}s (stall timeout ${stall}s); a slow site with progress for ${elapsed}s completed"
