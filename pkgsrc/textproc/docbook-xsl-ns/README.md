# DocBook XSL namespace catalog

This recipe comes from [NetBSD pkgsrc](https://github.com/NetBSD/pkgsrc/tree/fff4deb639a1a640476203c80f752fb77b6cb14b/textproc/docbook-xsl-ns).
It retains the NetBSD RCS identifiers and the upstream MIT license.
The `patch-lib_lib.xsl` fix retains its Debian origin.
The EmberBSD adaptation and its regression were prepared with AI assistance.

DocBook XSL 1.79.2 uses the `docbook-xsl` archive for namespace-aware stylesheets.
The `docbook-xsl-nons` archive contains the non-namespaced stylesheets.
This recipe retains the namespace-aware archive and its full payload.

The two SourceForge catalog rules use `xsl-ns/current/`.
The existing non-namespaced package owns `xsl/current/`.
The CDN rules retain the upstream 1.79.2 naming.
Native and cross packages both use `1.79.2nb1`.
The upstream archive name has no package revision.
The libnotify build-host dependency rejects the broken older package.

Run `python3 tests/catalog.py --catalog NEW_CATALOG --baseline OLD_CATALOG`
from this recipe directory with the two actual patched source catalogs.
The test checks the two-rule delta and unconditional provider and consumer floors.
It does not evaluate package metadata, run XSLT or install catalog entries.
Check both package modes and offline DocBook 5 transformations separately.

Cross packages install `fo/pdf2index` with the target Perl from `lang/perl5`.
The catalog rewrite in `post-install` runs the build host Perl through the tools wrapper.
Run `BMAKE=bmake sh tests/cross-perl.sh PKGSRC MAKECONF NEW_OUTPUT` with absolute paths.
It runs the real `REPLACE_PERL` edit and `post-install` in cross mode and builds nothing.
