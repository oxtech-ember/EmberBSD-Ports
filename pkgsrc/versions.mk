# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). One version of each versioned package family.
#
# Each EMBERBSD_VERSION_FAMILIES word is FAMILY=KEPT. Both are fnmatch(3)
# patterns over PKGPATH. scripts/prepare-pkgsrc.py removes every exported
# package directory that matches FAMILY but not KEPT, and requires KEPT to
# exist. EMBERBSD-DEFAULTS-MK.CONF includes this file and rejects a package
# whose PKGPATH matches FAMILY but not KEPT. Patch a consumer onto the kept
# version instead of adding an old one back. Use one word per line.
# EMBERBSD_VERSION_DEPENDENTS lists PKGPATHs that the exporter removes too:
# each one needs a removed version, and no kept package needs it. Port one
# onto the kept version to bring it back.
EMBERBSD_VERSION_FAMILIES+=	lang/python[0-9]*=lang/python315
EMBERBSD_VERSION_FAMILIES+=	lang/gcc[0-9]*=lang/gcc16*
EMBERBSD_VERSION_FAMILIES+=	lang/go[0-9]*=lang/go127
EMBERBSD_VERSION_FAMILIES+=	lang/lua[0-9]*=lang/lua55
EMBERBSD_VERSION_FAMILIES+=	lang/php[0-9]*=lang/php85
EMBERBSD_VERSION_FAMILIES+=	lang/ruby[0-9]*=lang/ruby40
EMBERBSD_VERSION_FAMILIES+=	lang/openjdk[0-9]*=lang/openjdk21
# One Berkeley DB, db18; db1 is the libc one.
EMBERBSD_VERSION_FAMILIES+=	databases/db=databases/db18
EMBERBSD_VERSION_FAMILIES+=	databases/db[0-9]*=databases/db18
EMBERBSD_VERSION_FAMILIES+=	databases/postgresql[0-9]*=databases/postgresql18*
EMBERBSD_VERSION_FAMILIES+=	databases/mariadb[0-9]*=databases/mariadb118-*
EMBERBSD_VERSION_FAMILIES+=	databases/mysql[0-9]*=databases/mariadb118-*
# One MySQL ODBC driver: MariaDB Connector/ODBC, built on the one client.
EMBERBSD_VERSION_FAMILIES+=	databases/myodbc=databases/mariadb-connector-odbc
EMBERBSD_VERSION_FAMILIES+=	security/libressl=security/openssl
EMBERBSD_VERSION_FAMILIES+=	games/love[0-9]*=games/love11
EMBERBSD_VERSION_FAMILIES+=	lang/tcl[0-9]*=lang/tcl
EMBERBSD_VERSION_FAMILIES+=	x11/tk[0-9]*=x11/tk
EMBERBSD_VERSION_FAMILIES+=	print/poppler-qt[0-9]*=print/poppler-qt6
EMBERBSD_VERSION_FAMILIES+=	*/opencv[0-9]*=graphics/opencv
EMBERBSD_VERSION_FAMILIES+=	graphics/opencv-contrib*=graphics/opencv-contrib
# Lua 5.1 or 5.3 C API.
EMBERBSD_VERSION_DEPENDENTS+=	games/asc
EMBERBSD_VERSION_DEPENDENTS+=	games/valyriatear
EMBERBSD_VERSION_DEPENDENTS+=	security/ap-modsecurity2
EMBERBSD_VERSION_DEPENDENTS+=	www/nsm
# GNAT from GCC 14; GCC16 has no Ada package. GPC needs GCC 2.
EMBERBSD_VERSION_DEPENDENTS+=	cad/ghdl
EMBERBSD_VERSION_DEPENDENTS+=	devel/ghdl-yosys-plugin
EMBERBSD_VERSION_DEPENDENTS+=	lang/gpc
# The embedded MariaDB 10.11 server; MariaDB 11.8 has no embedded package.
EMBERBSD_VERSION_DEPENDENTS+=	audio/amarok
# Upstream bulk test sets that pin removed versions.
EMBERBSD_VERSION_DEPENDENTS+=	meta-pkgs/bulk-large
EMBERBSD_VERSION_DEPENDENTS+=	meta-pkgs/bulk-medium
EMBERBSD_VERSION_DEPENDENTS+=	meta-pkgs/bulk-small
EMBERBSD_VERSION_DEPENDENTS+=	meta-pkgs/bulk-test-icu
EMBERBSD_VERSION_DEPENDENTS+=	meta-pkgs/bulk-test-python27
