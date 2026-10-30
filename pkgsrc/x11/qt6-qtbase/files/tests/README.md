# Public suffix consumer

Compile `publicsuffix-consumer.cpp` with the selected QtCore and QtNetwork
libraries. Run it against the QtNetwork under test: it exercises both
`qIsEffectiveTLD` and `QNetworkCookieJar` for ordinary, wildcard, exception,
unknown, Unicode, ACE and dot cases. The expected rules are present in the
libpsl release selected by this recipe. For changes in the suffix dataset,
compare the old and new algorithms on the same input data separately from this
consumer test.

Compile `ssl-consumer.cpp` against the QtCore and QtNetwork under test and run
it with the Qt TLS plugin directory and its selected common OpenSSL closure.
Pass a temporary localhost certificate and private key as arguments. It requires
a usable OpenSSL 3 backend, trusts only that fixture certificate, and verifies
a local encrypted ping/pong exchange without changing the system trust store.

Run `target-metadata-boundary.py PERL TARGET_METADATA_PL` with the selected
host Perl and this recipe's `target-metadata.pl` to check the exact buildlink
root, child paths and rejection of neighboring unresolved build paths.
