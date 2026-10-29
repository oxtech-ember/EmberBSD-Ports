# PPP platform support

The package retains the Linux and Solaris upstream backends and the BSD
backend for NetBSD and DragonFly. The previous pkgsrc recipe listed FreeBSD
and OpenBSD, but its configure rejected FreeBSD and did not select OpenBSD.
Neither is claimed as a working backend here. NetBSD AArch64 was built and
the ordinary version and authentication algorithm tests ran on a device;
other platforms require their own build and runtime verification.

The old NetBSD status plugin is outside the active OS build and references
LCP hooks no longer supplied by the common daemon. A future port needs an
explicit replacement event interface and a working plugin test.
