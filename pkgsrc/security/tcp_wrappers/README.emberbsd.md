# Common TCP wrappers

The common recipe retains the `tcp_wrappers_7.6-ipv6.4` pkgsrc source and
complete patch inventory from pinned pkgsrc revision
`fff4deb639a1a640476203c80f752fb77b6cb14b`. Its NetBSD build uses the
maintained NetBSD implementation for both native and package consumers,
including the native blocklist integration. Other platforms retain their
existing pkgsrc backend.

The upstream notice is recorded as `tcp-wrappers`; the package also carries
the NetBSD BSD-2 notices and the Berkeley notice for the optional historical
`strcasecmp.c` implementation. The upstream and Berkeley notices are installed
with the package documentation.

The NetBSD package uses SONAME 8: the previous pkgsrc SONAME 7 exported
interfaces declared by the old package header that are absent from the
maintained NetBSD implementation. Existing
binary consumers of SONAME 7 must be rebuilt. The native OS library keeps its
separate SONAME 1 and its native ABI. System builtin detection alone is not
sufficient to establish the common patchset, so NetBSD package consumers use
the common package by default.
