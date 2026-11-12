# Shared source identity and complete Ports patch set for Mesa and its
# build-host generator package.
MESA_SOURCE_VERSION= 26.2.6
MESA_PORT_REVISION= 24
MESA_GENERATORS_VERSION= ${MESA_SOURCE_VERSION}nb${MESA_PORT_REVISION}
DISTNAME= mesa-${MESA_SOURCE_VERSION}
EXTRACT_SUFX= .tar.xz
MASTER_SITES= https://archive.mesa3d.org/
PATCHDIR= ${.CURDIR}/../MesaLib/patches
DISTINFO_FILE= ${.CURDIR}/../MesaLib/distinfo
