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
# Gems that Ruby 4.0 ships as default or bundled gems, at the same or a
# newer version.
EMBERBSD_VERSION_FAMILIES+=	benchmarks/ruby-benchmark=lang/ruby40
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-io-console=lang/ruby40
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-reline=lang/ruby40
EMBERBSD_VERSION_FAMILIES+=	security/ruby-openssl=lang/ruby40
# Faraday 2 and Octokit 6; faraday_middleware is Faraday 1 only.
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday1=www/ruby-faraday
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday-excon1=www/ruby-faraday-excon
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday-httpclient1=www/ruby-faraday-httpclient
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday-net_http1=www/ruby-faraday-net_http
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday-net_http_persistent1=www/ruby-faraday-net_http_persistent
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday-patron1=www/ruby-faraday-patron
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday-rack1=www/ruby-faraday-rack
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday-retry1=www/ruby-faraday-retry
EMBERBSD_VERSION_FAMILIES+=	www/ruby-faraday_middleware=www/ruby-faraday
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-octokit4=devel/ruby-octokit
# Rails 8.1; roadie-rails 3.2/3.3 and propshaft 1.1 do not allow it.
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-activesupport[0-9]*=devel/ruby-activesupport81
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-activemodel[0-9]*=devel/ruby-activemodel81
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-activejob[0-9]*=devel/ruby-activejob81
EMBERBSD_VERSION_FAMILIES+=	databases/ruby-activerecord[0-9]*=databases/ruby-activerecord81
EMBERBSD_VERSION_FAMILIES+=	www/ruby-actionview[0-9]*=www/ruby-actionview81
EMBERBSD_VERSION_FAMILIES+=	www/ruby-actionpack[0-9]*=www/ruby-actionpack81
EMBERBSD_VERSION_FAMILIES+=	www/ruby-actioncable[0-9]*=www/ruby-actioncable81
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-railties[0-9]*=devel/ruby-railties81
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-activestorage[0-9]*=devel/ruby-activestorage81
EMBERBSD_VERSION_FAMILIES+=	mail/ruby-actionmailer[0-9]*=mail/ruby-actionmailer81
EMBERBSD_VERSION_FAMILIES+=	mail/ruby-actionmailbox[0-9]*=mail/ruby-actionmailbox81
EMBERBSD_VERSION_FAMILIES+=	textproc/ruby-actiontext[0-9]*=textproc/ruby-actiontext81
EMBERBSD_VERSION_FAMILIES+=	www/ruby-rails[0-9]*=www/ruby-rails81
EMBERBSD_VERSION_FAMILIES+=	mail/ruby-roadie-rails3[0-9]=mail/ruby-roadie-rails
EMBERBSD_VERSION_FAMILIES+=	www/ruby-propshaft1[0-9]=www/ruby-propshaft
# Redmine 7.0 on Rails 8.1; the parsers and net-imap that only Redmine 6 used.
EMBERBSD_VERSION_FAMILIES+=	devel/ruby-redmine6[0-9]=devel/ruby-redmine70
EMBERBSD_VERSION_FAMILIES+=	textproc/ruby-commonmarker0=textproc/ruby-commonmarker
EMBERBSD_VERSION_FAMILIES+=	textproc/ruby-commonmarker23=textproc/ruby-commonmarker
EMBERBSD_VERSION_FAMILIES+=	net/ruby-net-imap=lang/ruby40
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
# EventMachine adapters for Faraday 1; Faraday 2 has none.
EMBERBSD_VERSION_DEPENDENTS+=	www/ruby-faraday-em_http
EMBERBSD_VERSION_DEPENDENTS+=	www/ruby-faraday-em_synchrony
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
