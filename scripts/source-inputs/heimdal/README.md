# Common Heimdal source

Prepare `security/heimdal` from its verified release archive and the full
pkgsrc patchset with `source.py --sdk-source SDK --git GIT prepare --archive
ARCHIVE --patch PATCH --output NEW_DIRECTORY`. The owner also applies the
recipe's post-extract `heim_find_prime.h` copy. `verify-source --source
DIRECTORY` checks the prepared output and its recipe identity.

Native OS integration, ABI compatibility and target runtime are separate from
source preparation.

For the selected NetBSD native OpenSSL 4 backend, `hxtool info` lists
available key-management providers; this is not a selected default method or
an ENGINE configuration equivalent.

The checked `heim_ntlm_derive_ntlm2_sess` interface returns an `int` error
code. Its callers must check the return value before using the derived key.
This is an ABI change: the portable libtool version is 2:0:0 and the native
OS library uses SONAME 7. Rebuild consumers of the previous library.
