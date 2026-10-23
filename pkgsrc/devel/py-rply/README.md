# rply

Use the unmodified [0.7.8 release](https://github.com/alex/rply).
The archive SHA256 is `2a808ac25a4580a9991fc304d64434e299a8fc75760574492f242cbb5bb301c9`.
The upstream `LICENSE` is modified-bsd; this recipe does not change upstream source.

The dependency contract matches the upstream `setup.py` and the
[FreeBSD recipe](https://github.com/freebsd/freebsd-ports/blob/main/devel/py-rply/Makefile)
and [OpenBSD recipe](https://github.com/openbsd/ports/blob/master/devel/py-rply/Makefile).
Build with the shared Python and the normal pkgsrc wheel mechanism.
Native and cross packages use the same version and dependency floors.

The source distribution has no upstream test directory.
The rnc2rng upstream suite is a parser consumer, not the complete rply suite.
No test result is implied by package creation.
