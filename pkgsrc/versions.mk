# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). One version of each versioned package family.
#
# Each EMBERBSD_VERSION_FAMILIES word is FAMILY=KEPT. Both are fnmatch(3)
# patterns over PKGPATH. scripts/prepare-pkgsrc.py removes every exported
# package directory that matches FAMILY but not KEPT, and requires KEPT to
# exist. EMBERBSD-DEFAULTS-MK.CONF includes this file and rejects a package
# whose PKGPATH matches FAMILY but not KEPT. Patch a consumer onto the kept
# version instead of adding an old one back. Use one word per line.
EMBERBSD_VERSION_FAMILIES+=	lang/python[0-9]*=lang/python315
EMBERBSD_VERSION_FAMILIES+=	lang/gcc[0-9]*=lang/gcc16*
EMBERBSD_VERSION_FAMILIES+=	lang/go[0-9]*=lang/go127
EMBERBSD_VERSION_FAMILIES+=	lang/lua[0-9]*=lang/lua55
EMBERBSD_VERSION_FAMILIES+=	lang/php[0-9]*=lang/php85
EMBERBSD_VERSION_FAMILIES+=	lang/ruby[0-9]*=lang/ruby40
EMBERBSD_VERSION_FAMILIES+=	lang/openjdk[0-9]*=lang/openjdk21
EMBERBSD_VERSION_FAMILIES+=	databases/postgresql[0-9]*=databases/postgresql18*
EMBERBSD_VERSION_FAMILIES+=	databases/mariadb[0-9]*=databases/mariadb118-*
EMBERBSD_VERSION_FAMILIES+=	databases/mysql[0-9]*=databases/mariadb118-*
EMBERBSD_VERSION_FAMILIES+=	security/libressl=security/openssl

# Select the kept versions where pkgsrc chooses one.
LUA_VERSION_DEFAULT=		55
PHP_VERSION_DEFAULT=		85
PGSQL_VERSION_DEFAULT=		18
MYSQL_VERSION_DEFAULT=		mariadb118
