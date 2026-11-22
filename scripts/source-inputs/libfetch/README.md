# Common libfetch source

The pkgsrc `net/libfetch` recipe keeps its source in `files/`, without a
distfile. This owner exports the pinned pkgsrc tree with all common overlays,
then publishes that effective FILESDIR as an SDK prepared source tree. The
receipt identifies `net/libfetch` and its effective recipe inputs. It does
not replace the recipe or its patches.

Use the selected SDK and explicit source tools:

```sh
python3 -B scripts/source-inputs/libfetch/source.py --sdk-source /path/to/sdk-source --git /path/to/git prepare --patch /path/to/patch --output /new/libfetch
python3 -B scripts/source-inputs/libfetch/source.py --sdk-source /path/to/sdk-source --git /path/to/git verify-source --source /new/libfetch
```

An existing shared export can be selected with `--pkgsrc-export` and the same
explicit patch tool. Its receipt identity is the export key: the pinned pkgsrc
commit, the overlay inputs and the patch tool that produce the libfetch
FILESDIR. A matching key selects the export directly; neither preparation nor
`verify-source` reads FILESDIR again or makes another pkgsrc export. New
exports record a FILESDIR snapshot that preparation uses as the expected copy.
The caller owns the export; a different key is refused.
The consumer generates error headers in its object tree;
the prepared source remains read-only. Run `test-source.py` with the selected
Python, SDK source, Git and prepared source paths for its focused verification.

For an unchanged prepared payload, `refresh-source --source /path/to/source --patch /path/to/patch --pkgsrc-export /path/to/export` verifies the current source and atomically updates its receipt. The caller must hold exclusive use throughout; failed verification leaves the receipt unchanged.

Run the focused regression with the selected tools:

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/libfetch/test-refresh.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" --patch "$PATCH"
```

## OpenSSL 4 peer names

The common patch uses `SSL_set1_ipaddr` and `SSL_set1_dnsname` on each new
connection. It retains OpenSSL's IP parser and DNS fallback. It rejects an
empty reference identifier and stops if neither setter succeeds. SNI and the
existing certificate-chain verification remain in the shared connection path.
The library and its static `fetch` and `pkg_install` consumers have new revisions.

Run the certificate-matching check against the real exported helper:

```sh
"$HOST_PREFIX/bin/ruby40" profiles/common-build-tools/tests/libfetch-peername.rb \
  /absolute/exported-pkgsrc "$HOST_PREFIX"
"$HOST_PREFIX/bin/ruby40" profiles/common-build-tools/tests/libfetch-peername.rb \
  /absolute/exported-pkgsrc "$HOST_PREFIX" --sanitize
```

The check uses real OpenSSL certificate verification for DNS, IPv4 and IPv6,
including mismatches and a numeric DNS SAN that must not match an IP address.
It also checks SNI selection and empty-name refusal. `--sanitize` adds UBSan.
This host check does not establish a remote TLS handshake or target execution.
A strict build of the full exported `common.c` detects the former deprecated API.
