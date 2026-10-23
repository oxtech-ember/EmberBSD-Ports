# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), link DocBook XSL for relative imports.
BUILDLINK_TREE+=	docbook-xsl

.if !defined(DOCBOOK_XSL_BUILDLINK3_MK)
DOCBOOK_XSL_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.docbook-xsl+=	docbook-xsl>=1.79.2nb8
BUILDLINK_PKGSRCDIR.docbook-xsl?=	../../textproc/docbook-xsl
# Relocatable stylesheets import these files relative to their own path.
BUILDLINK_CONTENTS_FILTER.docbook-xsl?=	${GREP} '^share/xsl/docbook/'
.endif	# DOCBOOK_XSL_BUILDLINK3_MK

BUILDLINK_TREE+=	-docbook-xsl
