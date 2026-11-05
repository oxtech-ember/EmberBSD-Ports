/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxslt/xslt.h>
#include <libxslt/xsltInternals.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>

static void
check(const char *source, const char *url, const char *expected)
{
	xmlDocPtr sheet, input, result;
	xsltStylesheetPtr style;
	xmlChar *text = NULL;
	int length = 0;

	sheet = xmlReadMemory(source, (int)strlen(source), url, NULL, 0);
	assert(sheet != NULL);
	style = xsltParseStylesheetDoc(sheet);
	assert(style != NULL);
	input = xmlReadMemory("<root/>", 7, NULL, NULL, 0);
	assert(input != NULL);
	result = xsltApplyStylesheet(style, input, NULL);
	assert(result != NULL);
	assert(xsltSaveResultToString(&text, &length, result, style) >= 0);
	assert(text != NULL && strstr((const char *)text, expected) != NULL);
	xmlFree(text);
	xmlFreeDoc(result);
	xmlFreeDoc(input);
	xsltFreeStylesheet(style);
}

int
main(void)
{
	check("<xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' "
	    "version='1.0'><xsl:template match='/'><result>"
	    "<xsl:attribute name='a' xml:space='preserve'>  </xsl:attribute>"
	    "</result></xsl:template></xsl:stylesheet>", NULL, "a=\"  \"");
	check("<xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' "
	    "version='1.0' xml:base='http://[invalid'><xsl:template match='/'>"
	    "<result><xsl:value-of select=\"count(document(''))\"/></result>"
	    "</xsl:template></xsl:stylesheet>", NULL, "<result>0</result>");
	xsltCleanupGlobals();
	xmlCleanupParser();
	puts("PASS: attribute ownership and document URI behavior");
	return 0;
}
