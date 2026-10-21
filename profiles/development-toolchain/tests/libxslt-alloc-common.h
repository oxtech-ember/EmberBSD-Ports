/* SPDX-License-Identifier: BSD-2-Clause
 * AI-assisted functional allocation-error tests for owned, valid documents. */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <libxml/xmlmemory.h>
static size_t denied_size;
static int denied_hits;
static int live_docs;
static int live_lists;
struct tracked { void *ptr; size_t size; };
static struct tracked tracked[32768];
static void track(void *p, size_t n) {
    if (!p) return;
    for (size_t i=0; i<sizeof(tracked)/sizeof(tracked[0]); ++i) {
        if (!tracked[i].ptr) {
            tracked[i].ptr=p; tracked[i].size=n;
            if (n==sizeof(xmlDoc)) ++live_docs;
            if (n==sizeof(xsltRVTList)) ++live_lists;
            return;
        }
    }
    abort();
}
static void untrack(void *p) {
    if (!p) return;
    for (size_t i=0; i<sizeof(tracked)/sizeof(tracked[0]); ++i) {
        if (tracked[i].ptr==p) {
            if (tracked[i].size==sizeof(xmlDoc)) --live_docs;
            if (tracked[i].size==sizeof(xsltRVTList)) --live_lists;
            tracked[i].ptr=NULL; return;
        }
    }
    abort();
}
static void *test_malloc(size_t n) {
    if (denied_size && n==denied_size) { ++denied_hits; return NULL; }
    void *p=malloc(n); track(p,n); return p;
}
static void test_free(void *p) { untrack(p); free(p); }
static void *test_realloc(void *p,size_t n) {
    size_t count=sizeof(tracked)/sizeof(tracked[0]), slot=count;
    if (denied_size && n==denied_size) { ++denied_hits; return NULL; }
    if (p) {
        for (size_t i=0; i<count; ++i) if (tracked[i].ptr==p) { slot=i; break; }
        if (slot==count) abort();
    }
    void *q=realloc(p,n);
    if (q || !n) {
        if (slot<count) {
            if (tracked[slot].size==sizeof(xmlDoc)) --live_docs;
            if (tracked[slot].size==sizeof(xsltRVTList)) --live_lists;
            tracked[slot].ptr=NULL;
        }
        track(q,n);
    }
    return q;
}
static char *test_strdup(const char *s) {
    size_t n=strlen(s)+1; char *p=test_malloc(n);
    if (p)
        memcpy(p,s,n);
    return p;
}
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while(0)
static const char test_style[]="<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform'><xsl:template match='/'><xsl:variable name='v'><n/></xsl:variable></xsl:template></xsl:stylesheet>";
static xsltStylesheetPtr make_test_style(void) {
    xmlDocPtr d=xmlReadMemory(test_style,(int)strlen(test_style),"test.xsl",NULL,XML_PARSE_NONET);
    return xsltParseStylesheetDoc(d);
}
