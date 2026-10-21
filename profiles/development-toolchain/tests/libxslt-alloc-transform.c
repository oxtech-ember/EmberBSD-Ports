/* SPDX-License-Identifier: BSD-2-Clause */
/* Include the actual configured source to exercise the internal transfer path. */
#include "transform.c"
#include "libxslt-alloc-common.h"
int main(int argc,char **argv) {
    CHECK(argc==2);
    CHECK(xmlMemSetup(test_free,test_malloc,test_realloc,test_strdup)==0);
    xmlInitParser(); xsltStylesheetPtr style=make_test_style(); CHECK(style);
    xmlDocPtr input=xmlReadMemory("<input/>",8,"input.xml",NULL,XML_PARSE_NONET); CHECK(input);
    xsltTransformContextPtr c=xsltNewTransformContext(style,input); CHECK(c);
    xmlDocPtr d=xsltCreateRVT(c); CHECK(d);
    CHECK(xsltRegisterLocalRVT(c,d)==0);
    d->compression=!strcmp(argv[1],"global") ? XSLT_RVT_GLOBAL : XSLT_RVT_FUNC_RESULT;
    xsltStackElem var={0};
    if (!strcmp(argv[1],"func-select")) { var.flags=(1<<1); c->contextVariable=&var; }
    denied_size=sizeof(xsltRVTList); denied_hits=0;
    xsltReleaseLocalRVTs(c,NULL);
    denied_size=0;
    CHECK(denied_hits==0);
    xsltRVTListPtr list=!strcmp(argv[1],"global") ? c->persistRVTList :
        (!strcmp(argv[1],"func-select") ? var.fragment : c->localRVTList);
    CHECK(list && list->RVT==d && !list->next);
    if (var.fragment) { xsltReleaseRVTList(c,var.fragment); var.fragment=NULL; }
    c->contextVariable=NULL;
    xsltFreeTransformContext(c); xsltFreeStylesheet(style); xmlFreeDoc(input);
    xsltCleanupGlobals(); xmlCleanupParser(); CHECK(live_docs==0 && live_lists==0); return 0;
}
