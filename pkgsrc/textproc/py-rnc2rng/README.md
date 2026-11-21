# rnc2rng

Use the unmodified [2.8.0 release](https://github.com/djc/rnc2rng).
The archive SHA256 is `e6213f96dc88f0b499b281f038a53ed6dc1f21dae8bf822b9fdee9406468a2a6`.
The upstream `LICENSE` is mit; this recipe does not change upstream source.

The dependency contract matches the upstream `setup.py` and the
[FreeBSD recipe](https://github.com/freebsd/freebsd-ports/blob/main/textproc/py-rnc2rng/Makefile)
and [OpenBSD recipe](https://github.com/openbsd/ports/blob/master/textproc/py-rnc2rng/Makefile).
Build with the shared Python and the normal pkgsrc wheel mechanism.
Native and cross packages use the same version and dependency floors.

The test target runs the upstream unittest suite against the release’s schema fixtures.
This also exercises the shared rply parser. Mesa uses these modules through
lxml's RNC interface; schema validation remains enabled.

The wheel installs the upstream `AUTHORS` and `LICENSE` files.
