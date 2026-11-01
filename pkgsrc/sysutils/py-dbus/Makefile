# $NetBSD: Makefile,v 1.51 2026/10/13 08:50:12 wiz Exp $

DISTNAME=	dbus_python-1.5.1
PKGNAME=	${PYPKGPREFIX}-${DISTNAME:S/_python//}
CATEGORIES=	sysutils
MASTER_SITES=	https://dbus.freedesktop.org/releases/dbus-python/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.freedesktop.org/Software/dbus
COMMENT=	Python bindings for the D-BUS message bus system
LICENSE=	mit

USE_TOOLS+=		pkg-config

PY_PATCHPLIST=		yes

# Meson runs this interpreter to find the Python installation. In cross
# builds it is the build machine Python, which reports the target
# settings (pyversion.mk); PYTHONBIN is a target path there.
MESON_ARGS+=		-Dpython=${TOOL_PYTHONBIN}
# The doc build imports the built extension, which cannot load in a
# cross build, and the PLIST has no docs. The tests are not installed.
MESON_ARGS+=		-Ddoc=disabled
MESON_ARGS+=		-Dtests=disabled

# in dbus-python-common
post-install:
	${RM} -f ${DESTDIR}${PREFIX}/include/dbus-1.0/dbus/dbus-python.h
	${RM} -f ${DESTDIR}${PREFIX}/lib/pkgconfig/dbus-python.pc

MESON_REQD+=	0.60
.include "../../devel/meson/build.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../lang/python/batteries-included.mk"
.include "../../lang/python/extension.mk"
BUILDLINK_API_DEPENDS.dbus+=	dbus>=1.8
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../sysutils/dbus-python-common/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
