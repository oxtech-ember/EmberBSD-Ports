/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Exercise the public libxml/libxslt contracts used by Blink's XSLT glue. */
#include <assert.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxml/xpathInternals.h>
#include <libxslt/xslt.h>
#include <libxslt/xsltutils.h>
#include <libxslt/transform.h>
#include <libxslt/variables.h>
#include <libxslt/security.h>

static int called;
static void
sort_values(xsltTransformContextPtr ctxt, xmlNodePtr *sorts, int count)
{
    assert(count == 1 && ctxt->nodeList && ctxt->nodeList->nodeNr == 2);
    xmlXPathObjectPtr *values = xsltComputeSortResult(ctxt, sorts[0]);
    assert(values && values[0] && values[1]);
    assert(xmlStrEqual(values[0]->stringval, BAD_CAST "b"));
    assert(xmlStrEqual(values[1]->stringval, BAD_CAST "a"));
    xmlXPathFreeObject(values[0]);
    xmlXPathFreeObject(values[1]);
    xmlFree(values);
    called++;
}

int
main(void)
{
    const char *sheet = "<xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' version='1.0'>"
        "<xsl:param name='prefix'/><xsl:template match='/'><out><xsl:value-of select='$prefix'/>"
        "<xsl:for-each select='root/item'><xsl:sort select='.'/><xsl:value-of select='.'/></xsl:for-each>"
        "</out></xsl:template></xsl:stylesheet>";
    const char *input = "<root><item>b</item><item>a</item></root>";
    xmlDocPtr doc=xmlReadMemory(sheet, (int)strlen(sheet), NULL, NULL, 0);
    assert(doc);
    xsltStylesheetPtr style=xsltParseStylesheetDoc(doc);
    assert(style);
    xmlDocPtr source=xmlReadMemory(input, (int)strlen(input), NULL, NULL, 0);
    assert(source);
    xsltTransformContextPtr ctxt=xsltNewTransformContext(style, source);
    xsltSecurityPrefsPtr security=xsltNewSecurityPrefs();
    assert(ctxt && security);
    assert(xsltSetSecurityPrefs(security, XSLT_SECPREF_WRITE_FILE, xsltSecurityForbid) == 0);
    assert(xsltSetCtxtSecurityPrefs(security, ctxt) == 0);
    xsltSetCtxtSortFunc(ctxt, sort_values);
    const char *params[] = {"prefix", "value:", NULL};
    assert(xsltQuoteUserParams(ctxt, params) == 0);
    xmlDocPtr result=xsltApplyStylesheetUser(style, source, NULL, NULL, NULL, ctxt);
    assert(result && called == 1);
    xmlChar *text=NULL; int length=0;
    assert(xsltSaveResultToString(&text, &length, result, style) >= 0);
    assert(text && strstr((const char *)text, "<out>value:ba</out>"));
    xmlFree(text);
    xmlFreeDoc(result);
    xsltFreeTransformContext(ctxt);
    xsltFreeSecurityPrefs(security);
    xmlFreeDoc(source);
    xsltFreeStylesheet(style);
    xsltCleanupGlobals();
    xmlCleanupParser();
    return 0;
}
