# rnc2rng

Use the unmodified [2.7.0 release](https://github.com/djc/rnc2rng).
The archive SHA256 is `dd9ffbbd69d09cb07e6e7a8cf80fd28703fdc6d3b9026f8756b49cbe3314676b`.
The upstream `LICENSE` is mit; this recipe does not change upstream source.

The dependency contract matches the upstream `setup.py` and the
[FreeBSD recipe](https://github.com/freebsd/freebsd-ports/blob/main/textproc/py-rnc2rng/Makefile)
and [OpenBSD recipe](https://github.com/openbsd/ports/blob/master/textproc/py-rnc2rng/Makefile).
Build with the shared Python and the normal pkgsrc wheel mechanism.
Native and cross packages use the same version and dependency floors.

The test target runs upstream test.py and the release's schema fixtures.
This also exercises the shared rply parser. Mesa uses these modules through
lxml's RNC interface; schema validation remains enabled.

The wheel installs the upstream `AUTHORS` and `LICENSE` files.
