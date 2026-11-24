# $NetBSD: buildlink3.mk,v 1.3 2022/11/01 17:33:32 gdt Exp $

BUILDLINK_TREE+=	lcms2

.if !defined(LCMS2_BUILDLINK3_MK)
LCMS2_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.lcms2+=	lcms2>=2.2
BUILDLINK_PKGSRCDIR.lcms2?=	../../graphics/lcms2

USE_TOOLS+=		readlink
BUILDLINK_TARGETS+=	buildlink-include-lcms2

.PHONY: buildlink-include-lcms2
buildlink-include-lcms2:
	${RUN} link=${BUILDLINK_DIR:Q}/include/lcms2/lcms2.h; \
	if [ -L "$$link" ]; then \
		target=$$(${TOOLS_CMDLINE.readlink} "$$link"); \
		[ "$$target" != ../lcms2.h ] || exit 0; \
		${RM} -f "$$link"; \
	elif [ -e "$$link" ]; then \
		exit 0; \
	fi; \
	${MKDIR} ${BUILDLINK_DIR:Q}/include/lcms2; \
	${ECHO_BUILDLINK_MSG} "Linking lcms2/lcms2.h to lcms2.h in ${BUILDLINK_DIR}/include"; \
	${LN} -s ../lcms2.h "$$link"
.endif # LCMS2_BUILDLINK3_MK

BUILDLINK_TREE+=	-lcms2
