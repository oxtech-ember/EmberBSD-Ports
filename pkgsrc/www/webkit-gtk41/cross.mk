# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native generators and real target introspection.
CMAKE_CONFIGURE_ARGS+= -DGI_SCANNER_EXE:FILEPATH=${TOOLBASE}/bin/g-ir-scanner
CMAKE_CONFIGURE_ARGS+= -DGI_COMPILER_EXE:FILEPATH=${TOOLBASE}/bin/g-ir-compiler
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
CMAKE_CONFIGURE_ARGS+= -DGI_LDD_WRAPPER:FILEPATH=${EMBERBSD_GI_FILESDIR}/elf-needed.sh
CMAKE_CONFIGURE_ARGS+= -DGI_TARGET_GIR_DIR:PATH=${CROSS_DESTDIR}${CROSS_LOCALBASE}/share/gir-1.0
MAKE_ENV+= GI_GIR_PATH=${CROSS_DESTDIR}${CROSS_LOCALBASE}/share/gir-1.0
CONFIGURE_ENV+= GI_CROSS_LAUNCHER=${EMBERBSD_CROSS_BUILD_PYTHON:Q}\ -E\ -S\ ${EMBERBSD_GI_FILESDIR:Q}/target-query.py
CONFIGURE_ENV+= EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q}
CONFIGURE_ENV+= EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q}
CONFIGURE_ENV+= EMBERBSD_GI_TARGET=${_EMBER_GI_TARGET:Q}
CONFIGURE_ENV+= EMBERBSD_GI_READELF=${TOOLDIR:Q}/bin/${_EMBER_GI_TRIPLET}-readelf

pre-configure: emberbsd-webkit-atomic
.PHONY: emberbsd-webkit-atomic
emberbsd-webkit-atomic:
	${RUN}${SETENV} ${CONFIGURE_ENV} ${SH} ${.CURDIR}/../../www/webkit-gtk41/files/check-gcc16-atomic.sh \
	    ${CROSS_DESTDIR:Q} ${MACHINE_GNU_PLATFORM:Q} \
	    ${TOOLDIR:Q}/bin/${MACHINE_GNU_PLATFORM}-readelf \
	    ${WRAPPER_BINDIR:Q}/c++ --sysroot=${CROSS_DESTDIR:Q} ${CXXFLAGS}
.endif
