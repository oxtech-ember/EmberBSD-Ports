# Use the common source snapshot with the build flags selected by each consumer.
.include "../../devel/gvdb-source/version.mk"

TOOL_DEPENDS+=	gvdb-source-${GVDB_VERSION}{,nb[0-9]*}:../../devel/gvdb-source
GVDB_SOURCE_DIR?=	${TOOLBASE}/share/gvdb-source

pre-configure: gvdb-install-source
gvdb-install-source:
	${RUN} ${TEST} -f ${GVDB_SOURCE_DIR:Q}/gvdb/gvdb-reader.c
	${RUN} ${RM} -rf ${WRKSRC}/subprojects/gvdb
	${RUN} ${CP} -R ${GVDB_SOURCE_DIR:Q} ${WRKSRC}/subprojects/gvdb
