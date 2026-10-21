/* SPDX-License-Identifier: BSD-2-Clause
 * AI-assisted EmberBSD API regressions. Upstream library licences are unchanged.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxml/tree.h>
#include <libxml/valid.h>
#include <libxml/xpath.h>
#include <libxslt/xslt.h>
#include <libxslt/xsltInternals.h>
#include <libxslt/transform.h>
#include <libxslt/variables.h>
#include <libxslt/xsltutils.h>
#include <libexslt/exslt.h>

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static const char style[] = "<xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' version='1.0'><xsl:template match='/'/></xsl:stylesheet>";
static xmlDocPtr read_doc(const char *s) { return xmlReadMemory(s, (int)strlen(s), "test.xml", NULL, XML_PARSE_NONET); }
static xsltStylesheetPtr make_style(void) { return xsltParseStylesheetDoc(read_doc(style)); }

static int registered(const char *kind, int xpath_only) {
    xsltStylesheetPtr s = make_style(); xmlDocPtr input = read_doc("<input/>");
    xsltTransformContextPtr c = xsltNewTransformContext(s, input);
    xmlDocPtr a = xsltCreateRVT(c), b = xsltCreateRVT(c);
    REQUIRE(s && input && c && a && b);
    xmlDocSetRootElement(a, xmlNewNode(NULL, BAD_CAST "a"));
    xmlDocSetRootElement(b, xmlNewNode(NULL, BAD_CAST "b"));
    int (*reg)(xsltTransformContextPtr, xmlDocPtr) = xsltRegisterPersistRVT;
    if (!strcmp(kind, "local")) reg = xsltRegisterLocalRVT;
    if (!strcmp(kind, "tmp")) reg = xsltRegisterTmpRVT;
    REQUIRE(reg(c, a) == 0 && reg(c, b) == 0);
    if (xpath_only) {
        xmlXPathContextPtr xp = xmlXPathNewContext(a); REQUIRE(xp);
        xp->node = (xmlNodePtr)a;
        xmlXPathObjectPtr result = xmlXPathEvalExpression(BAD_CAST "count(preceding::*) + count(following::*)", xp);
        REQUIRE(result && result->type == XPATH_NUMBER && result->floatval == 0);
        xmlXPathFreeObject(result); xmlXPathFreeContext(xp);
    } else { REQUIRE(a->prev == NULL && a->next == NULL && b->prev == NULL && b->next == NULL); }
    xsltFreeTransformContext(c); xsltFreeStylesheet(s); xmlFreeDoc(input); return 0;
}

static int release_case(const char *kind) {
    if (!strcmp(kind, "null")) { xsltReleaseRVT(NULL, xmlNewDoc(BAD_CAST "1.0")); return 0; }
    xsltStylesheetPtr s = make_style(); xmlDocPtr input = read_doc("<input/>");
    xsltTransformContextPtr c = xsltNewTransformContext(s, input); REQUIRE(s && input && c);
    int n = !strcmp(kind, "full") ? 45 : 1;
    for (int i = 0; i < n; ++i) {
        xmlDocPtr d = xmlNewDoc(BAD_CAST "1.0"); REQUIRE(d);
        xmlDocSetRootElement(d, xmlNewNode(NULL, BAD_CAST "old"));
        xsltReleaseRVT(c, d);
    }
    REQUIRE(c->cache->nbRVT == (n > 40 ? 40 : n));
    for (int i = 0; i < (n > 40 ? 40 : n); ++i) {
        xmlDocPtr d = xsltCreateRVT(c); REQUIRE(d && !d->children && !d->prev && !d->next);
        xmlFreeDoc(d);
    }
    REQUIRE(c->cache->nbRVT == 0);
    xsltFreeTransformContext(c); xsltFreeStylesheet(s); xmlFreeDoc(input); return 0;
}

static int id_cleanup(void) {
    REQUIRE(LIBXML_VERSION >= 21504 && atoi(xmlParserVersion) >= 21504);
    xsltStylesheetPtr s = make_style(); xmlDocPtr d = read_doc("<n xml:id='id1'/>");
    xsltTransformContextPtr c = xsltNewTransformContext(s, d); REQUIRE(s && d && c);
    xmlAttrPtr attr = xmlGetID(d, BAD_CAST "id1"); REQUIRE(attr);
    /* libxslt stores source flags in these high bits of atype.
     * Check the paired libxml2 ID cleanup contract independently. */
    attr->atype = (xmlAttributeType)((unsigned)attr->atype | (1u << 27));
    REQUIRE(attr->atype != XML_ATTRIBUTE_ID && xmlGetID(d, BAD_CAST "id1") == attr);
    REQUIRE(xmlRemoveProp(attr) == 0);
    REQUIRE(xmlGetID(d, BAD_CAST "id1") == NULL);
    xsltFreeTransformContext(c); xsltFreeStylesheet(s); xmlFreeDoc(d); return 0;
}

static int exslt_case(void) {
    static const char xsl[] =
    "<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform' "
    "xmlns:exsl='http://exslt.org/common' xmlns:func='http://exslt.org/functions' xmlns:m='urn:test' "
    "extension-element-prefixes='exsl func' exclude-result-prefixes='m'>"
    "<xsl:output method='text'/><xsl:key name='k' match='n' use='@v'/>"
    "<xsl:variable name='global'><n v='global'/></xsl:variable>"
    "<func:function name='m:f'><xsl:variable name='local'><n v='local'/></xsl:variable>"
    "<func:result select='exsl:node-set($local)/n'/></func:function>"
    "<xsl:template match='/'><xsl:for-each select='exsl:node-set($global)'>"
    "<xsl:value-of select=\"key('k','global')/@v\"/></xsl:for-each>"
    "<xsl:text>:</xsl:text><xsl:value-of select='m:f()/@v'/></xsl:template></xsl:stylesheet>";
    xsltStylesheetPtr s = xsltParseStylesheetDoc(read_doc(xsl)); REQUIRE(s);
    for (int i = 0; i < 100; ++i) {
        xmlDocPtr d = read_doc("<input/>"); xmlDocPtr result = xsltApplyStylesheet(s, d, NULL);
        REQUIRE(d && result); xmlChar *out = NULL; int len = 0;
        REQUIRE(xsltSaveResultToString(&out, &len, result, s) == 0);
        REQUIRE(len == 12 && !memcmp(out, "global:local", 12));
        xmlFree(out); xmlFreeDoc(result); xmlFreeDoc(d);
    }
    xsltFreeStylesheet(s); return 0;
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    xmlInitParser(); exsltRegisterAll(); int rc = 2;
    if (!strncmp(argv[1], "registered-", 11)) rc = registered(argv[1]+11, 0);
    else if (!strncmp(argv[1], "xpath-", 6)) rc = registered(argv[1]+6, 1);
    else if (!strncmp(argv[1], "release-", 8)) rc = release_case(argv[1]+8);
    else if (!strcmp(argv[1], "id-cleanup")) rc = id_cleanup();
    else if (!strcmp(argv[1], "exslt")) rc = exslt_case();
    else if (!strcmp(argv[1], "null-rvt")) { xsltReleaseRVT(NULL, NULL); rc = 0; }
    xsltCleanupGlobals(); xmlCleanupParser(); return rc;
}
