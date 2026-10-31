# Origin: EmberBSD (AI-assisted).
#
# Meson cross file for a pkgsrc cross build: ${MESON_CROSS_FILE} describes
# the target machine. devel/meson/build.mk passes it to "meson setup";
# lang/python/wheel.mk passes it to meson-python wheel builds.
#
# Included only when USE_CROSS_COMPILE is yes, after bsd.prefs.mk.

.if !defined(MESON_CROSS_FILE_MK)
MESON_CROSS_FILE_MK=	# defined

MESON_CPU_FAMILY.amd64=		x86_64
MESON_CPU_FAMILY.arm26?=	arm
MESON_CPU_FAMILY.arm32?=	arm
MESON_CPU_FAMILY.earm?=		arm
MESON_CPU_FAMILY.earmeb?=	arm
MESON_CPU_FAMILY.earmhf?=	arm
MESON_CPU_FAMILY.earmhfeb?=	arm
MESON_CPU_FAMILY.earmv4?=	arm
MESON_CPU_FAMILY.earmv4eb?=	arm
MESON_CPU_FAMILY.earmv5?=	arm
MESON_CPU_FAMILY.earmv5eb?=	arm
MESON_CPU_FAMILY.earmv6?=	arm
MESON_CPU_FAMILY.earmv6eb?=	arm
MESON_CPU_FAMILY.earmv6hf?=	arm
MESON_CPU_FAMILY.earmv6hfeb?=	arm
MESON_CPU_FAMILY.earmv7?=	arm
MESON_CPU_FAMILY.earmv7eb?=	arm
MESON_CPU_FAMILY.earmv7hf?=	arm
MESON_CPU_FAMILY.earmv7hfeb?=	arm
MESON_CPU_FAMILY.i386=		x86
MESON_CPU_FAMILY.i486=		x86
MESON_CPU_FAMILY.i586=		x86
MESON_CPU_FAMILY.i686=		x86
MESON_CPU_FAMILY.hppa=		parisc
MESON_CPU_FAMILY.m68000=	m68k
MESON_CPU_FAMILY.mips64eb=	mips
MESON_CPU_FAMILY.mips64el=	mips
MESON_CPU_FAMILY.mipseb=	mips
MESON_CPU_FAMILY.mipsel=	mips
MESON_CPU_FAMILY.powerpc64=	ppc64
MESON_CPU_FAMILY.powerpc=	ppc
MESON_CPU_FAMILY.sh3eb=		sh3
MESON_CPU_FAMILY.sh3el=		sh3

MESON_CPU_ENDIAN.earmeb?=	big
MESON_CPU_ENDIAN.earmhfeb?=	big
MESON_CPU_ENDIAN.earmv4eb?=	big
MESON_CPU_ENDIAN.earmv5eb?=	big
MESON_CPU_ENDIAN.earmv6eb?=	big
MESON_CPU_ENDIAN.earmv6hfeb?=	big
MESON_CPU_ENDIAN.earmv7eb?=	big
MESON_CPU_ENDIAN.earmv7hfeb?=	big
MESON_CPU_ENDIAN.mips64eb=	big
MESON_CPU_ENDIAN.mipseb=	big
MESON_CPU_ENDIAN.powerpc64=	big
MESON_CPU_ENDIAN.powerpc=	big
MESON_CPU_ENDIAN.sh3eb=		big
MESON_CPU_ENDIAN.sparc64=	big
MESON_CPU_ENDIAN.sparc=		big

MESON_CPU_FAMILY=	${MESON_CPU_FAMILY.${MACHINE_ARCH}:U${MACHINE_ARCH}}
MESON_CPU=		${MACHINE_ARCH}
MESON_CPU_ENDIAN=	${MESON_CPU_ENDIAN.${MACHINE_ARCH}:Ulittle}

# Select the host-executable SDK target archiver explicitly. Otherwise Meson
# may discover a target llvm-ar in the buildlink PATH and try to execute it.
.if !empty(EMBERBSD_CROSS_COMPILER_FAMILY:U)
.  if empty(MESON_BINARIES:Mar)
MESON_BINARIES+=	ar
.  endif
MESON_BINARY.ar?=	${TOOLS_PATH.ar}
.endif

MESON_CROSS_VARS+=	sys_root
MESON_CROSS.sys_root=	'${_CROSS_DESTDIR}'

MESON_CROSS_FILE=	${WRKDIR}/.meson_cross
${MESON_CROSS_FILE}:
	@${STEP_MSG} Creating meson cross file
.if !empty(EMBERBSD_CROSS_COMPILER_FAMILY:U)
	${RUN}case ${MESON_BINARY.ar:Q}"" in /*) ;; *) ${ERROR_MSG} "Select an absolute cross archiver"; exit 1;; esac; \
	    ${TEST} -x ${MESON_BINARY.ar:Q}"" || { ${ERROR_MSG} "Cross archiver is not executable"; exit 1; }
.endif
	${RUN}${RM} -f ${.TARGET}.tmp
	${RUN}${ECHO} '[properties]' >${.TARGET}.tmp
.  for _v_ in ${MESON_CROSS_VARS}
.    if defined(MESON_CROSS.${_v_})
	${RUN}${ECHO} ${_v_} = ${MESON_CROSS.${_v_}:Q} >>${.TARGET}.tmp
.    endif
.  endfor
.  for _v_ in ${MESON_CROSS_OPSYS_VARS}
.    if defined(MESON_CROSS.${OPSYS}.${_v_})
	${RUN}${ECHO} ${_v_} = ${MESON_CROSS.${OPSYS}.${_v_}:Q} \
		>>${.TARGET}.tmp
.    endif
.  endfor
.  for _v_ in ${MESON_CROSS_ARCH_VARS}
.    if defined(MESON_CROSS.${MACHINE_ARCH}.${_v_})
	${RUN}${ECHO} ${_v_} = ${MESON_CROSS.${MACHINE_ARCH}.${_v_}:Q} \
		>>${.TARGET}.tmp
.    endif
.  endfor
	${RUN}${ECHO} '[host_machine]' >>${.TARGET}.tmp
	${RUN}${ECHO} "system = '${LOWER_OPSYS}'" >>${.TARGET}.tmp
	${RUN}${ECHO} "cpu_family = '${MESON_CPU_FAMILY}'" >>${.TARGET}.tmp
	${RUN}${ECHO} "cpu = '${MESON_CPU}'" >>${.TARGET}.tmp
	${RUN}${ECHO} "endian = '${MESON_CPU_ENDIAN}'" >>${.TARGET}.tmp
	${RUN}${ECHO} '[binaries]' >>${.TARGET}.tmp
.  for _v_ in ${MESON_BINARIES:O:u}
.    if !defined(MESON_BINARY.${_v_})
.      error MESON_BINARIES lists ${_v_} but MESON_BINARY.${_v_} is undefined
.    endif
	${RUN}${ECHO} ${MESON_BINARY_KEY.${_v_}:U${_v_}} = \'${MESON_BINARY.${_v_}:Q}\' \
		>>${.TARGET}.tmp
.  endfor
	${RUN}${MV} -f ${.TARGET}.tmp ${.TARGET}

.endif	# MESON_CROSS_FILE_MK
