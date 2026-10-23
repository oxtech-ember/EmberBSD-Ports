# $NetBSD: builtin.mk,v 1.13 2025/04/30 21:09:49 tnn Exp $
# Origin: EmberBSD; AI-assisted qualified base provider selection.

_EDITLINE_RECIPE_DIR:= ${.PARSEDIR}
BUILTIN_PKG:= editline
PREFER.editline?= native
BUILTIN_FIND_LIBS:= edit
BUILTIN_FIND_HEADERS_VAR:= H_EDITLINE H_HISTEDIT
BUILTIN_FIND_HEADERS.H_EDITLINE= editline/readline.h readline/readline.h
BUILTIN_FIND_HEADERS.H_HISTEDIT= histedit.h
BUILTIN_FIND_FILES_VAR:= F_EDITLINE_DISTINFO F_EDITLINE_LIBRARY
BUILTIN_FIND_FILES.F_EDITLINE_DISTINFO= /usr/share/emberbsd/ports/editline.distinfo
BUILTIN_FIND_FILES.F_EDITLINE_LIBRARY= /usr/lib${LIBABISUFFIX}/libedit.so /usr/lib${LIBABISUFFIX}/libedit.a

.include "../../mk/buildlink3/bsd.builtin.mk"

# The generic readline detector can set IS_BUILTIN.editline before this file.
# Always check the source identity. Never accept that detector's version guess.
_EDITLINE_QUALIFIED= no
.if ${F_EDITLINE_DISTINFO:U} != "__nonexistent__" && \
    ${H_EDITLINE:U} != "__nonexistent__" && \
    ${H_HISTEDIT:U} != "__nonexistent__" && \
    !empty(H_EDITLINE:M/usr/include/*) && ${H_HISTEDIT:U} == "/usr/include/histedit.h" && \
    ${F_EDITLINE_LIBRARY:U} != "__nonexistent__" && \
    ${BUILTIN_LIB_FOUND.edit:U:tl} == "yes"
_EDITLINE_QUALIFIED!= if cmp -s ${TOOLS_CROSS_DESTDIR:Q}${F_EDITLINE_DISTINFO:Q} ${_EDITLINE_RECIPE_DIR:Q}/distinfo; then echo yes; else echo no; fi
.endif
IS_BUILTIN.editline= ${_EDITLINE_QUALIFIED}

.if ${IS_BUILTIN.editline} == "yes"
# Makefile is the only version authority. Do not use the consumer's DISTNAME.
BUILTIN_VERSION.editline!= ${AWK} '/^DISTNAME[ \t]*=/ { sub(/^[^=]*=[ \t]*/, ""); sub(/^libedit-/, ""); split($$0, v, "-"); print v[2] "." v[1] }' ${_EDITLINE_RECIPE_DIR:Q}/Makefile
BUILTIN_PKG.editline= editline-${BUILTIN_VERSION.editline}
.else
.undef BUILTIN_PKG.editline
.undef BUILTIN_VERSION.editline
.endif


_EDITLINE_API_OK= ${IS_BUILTIN.editline}
.if ${IS_BUILTIN.editline} == "yes"
.  for _dep_ in ${BUILDLINK_API_DEPENDS.editline}
.    if ${_EDITLINE_API_OK:tl} == "yes"
_EDITLINE_API_OK!= if ${PKG_ADMIN} pmatch ${_dep_:Q} ${BUILTIN_PKG.editline:Q}; then echo yes; else echo no; fi
.    endif
.  endfor
.endif
.if !defined(USE_BUILTIN.editline)
.  if ${PREFER.editline} == "pkgsrc"
USE_BUILTIN.editline= no
.  else
USE_BUILTIN.editline= ${_EDITLINE_API_OK}
.  endif
.endif
.if ${USE_BUILTIN.editline:tl} == "yes" && ${_EDITLINE_API_OK:tl} != "yes"
PKG_FAIL_REASON+= "The selected base libedit does not satisfy the requested API dependency."
.endif

# A marked target, exported tree, or EmberBSD profile must use the base library.
# Other systems retain the portable package fallback.
.if (${OPSYS:U} == "NetBSD" && (${EMBERBSD_PORTS:Uno:tl} == "yes" || \
    exists(${_EDITLINE_RECIPE_DIR}/../../EMBERBSD-PKGSRC-REVISION))) || \
    ${F_EDITLINE_DISTINFO:U} != "__nonexistent__"
.  if ${IS_BUILTIN.editline} != "yes"
PKG_FAIL_REASON+= "Rebuild EmberBSD base libedit from the current Ports recipe before building consumers."
.  elif ${USE_BUILTIN.editline:tl} != "yes"
PKG_FAIL_REASON+= "Use the qualified EmberBSD base libedit; a second package provider is not supported."
.  endif
.endif
.if ${USE_BUILTIN.editline:tl} == "yes" && ${IS_BUILTIN.editline} != "yes"
PKG_FAIL_REASON+= "USE_BUILTIN.editline requires a matching EmberBSD source marker and base headers/library."
.endif
MAKEVARS+= IS_BUILTIN.editline USE_BUILTIN.editline BUILTIN_PKG.editline BUILTIN_VERSION.editline

CHECK_BUILTIN.editline?=	no
.if ${CHECK_BUILTIN.editline:tl} == no

.  if !empty(_PKG_USE_READLINE:U:M[yY][eE][sS])
BUILDLINK_TRANSFORM+=	l:history:edit:${BUILTIN_LIBNAME.termcap}
BUILDLINK_TRANSFORM+=	l:readline:edit:${BUILTIN_LIBNAME.termcap}
.  endif

.  if ${USE_BUILTIN.editline:tl} == yes
BUILDLINK_TARGETS+=	ensure-libedit-pc
.PHONY: ensure-libedit-pc
ensure-libedit-pc:
	${RUN}								\
	dst="${BUILDLINK_DIR}/lib/pkgconfig/libedit.pc";			\
	src="${TOOLS_CROSS_DESTDIR}${BUILDLINK_PREFIX.editline}/lib${LIBABISUFFIX}/pkgconfig/libedit.pc"; \
	if [ ! -f "$${dst}" ]; then					\
		${MKDIR} "${BUILDLINK_DIR}/lib/pkgconfig";		\
		if [ -f "$${src}" ]; then					\
			${ECHO_BUILDLINK_MSG} "Symlinking $${src}";	\
			${LN} -sf "$${src}" "$${dst}";			\
		else							\
			${ECHO_BUILDLINK_MSG} "Creating $${dst}";	\
			{						\
			${ECHO} "prefix=${BUILDLINK_PREFIX.editline}";	\
			${ECHO} "exec_prefix=\$${prefix}";		\
			${ECHO} "libdir=\$${exec_prefix}/lib";		\
			${ECHO} "includedir=\$${prefix}/include";	\
			${ECHO} "";					\
			${ECHO} "Name: libedit";			\
			${ECHO} "Description: command line editor library providing generic line editing, history, and tokenization functions.";	\
			${ECHO} "Version: ${BUILTIN_VERSION.editline}";				\
			${ECHO} "Libs: ${COMPILER_RPATH_FLAG}\$${libdir} -L\$${libdir} -ledit";	\
			${ECHO} "Libs.private: -ltermcap";		\
			${ECHO} "Cflags: -I\$${includedir} -I\$${includedir}/readline";		\
			} > "$${dst}";					\
		fi;							\
	fi

.    if !empty(H_EDITLINE:M*/editline/readline.h)
BUILDLINK_TARGETS+=	buildlink-readline-readline-h
BUILDLINK_TARGETS+=	buildlink-readline-history-h
.    endif

.    if !target(buildlink-readline-readline-h)
.PHONY: buildlink-readline-readline-h
buildlink-readline-readline-h:
	${RUN}								\
	src=${TOOLS_CROSS_DESTDIR:Q}${H_EDITLINE:Q};						\
	dest="${BUILDLINK_DIR}/include/readline/readline.h";		\
	if ${TEST} ! -f "$$dest" -a -f "$$src"; then			\
		fname=`${BASENAME} "$$src"`;				\
		${ECHO_BUILDLINK_MSG} "Linking $$fname -> readline.h.";	\
		${MKDIR} "`${DIRNAME} "$$dest"`";				\
		${LN} -s "$$src" "$$dest";				\
	fi
.    endif

.    if !target(buildlink-readline-history-h)
.PHONY: buildlink-readline-history-h
buildlink-readline-history-h:
	${RUN}								\
	src=${TOOLS_CROSS_DESTDIR:Q}${H_EDITLINE:Q};						\
	dest="${BUILDLINK_DIR}/include/readline/history.h";		\
	if ${TEST} ! -f "$$dest" -a -f "$$src"; then			\
		fname=`${BASENAME} "$$src"`;				\
		${ECHO_BUILDLINK_MSG} "Linking $$fname -> history.h.";	\
		${MKDIR} "`${DIRNAME} "$$dest"`";				\
		${LN} -s "$$src" "$$dest";				\
	fi
.    endif
.  endif
.endif	# CHECK_BUILTIN.editline
