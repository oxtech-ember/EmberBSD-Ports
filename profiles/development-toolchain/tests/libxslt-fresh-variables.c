/* SPDX-License-Identifier: BSD-2-Clause */
#include "variables.c"
#include "libxslt-alloc-common.h"
int main(int argc,char **argv) {
    CHECK(argc==3);
    int faulting=strcmp(argv[2],"ok")!=0;
    CHECK(xmlMemSetup(test_free,test_malloc,test_realloc,test_strdup)==0);
    xmlInitParser(); xsltStylesheetPtr style=make_test_style(); CHECK(style);
    xmlDocPtr input=xmlReadMemory("<input/>",8,"input.xml",NULL,XML_PARSE_NONET); CHECK(input);
    xsltTransformContextPtr c=xsltNewTransformContext(style,input); CHECK(c);
    c->node=xmlDocGetRootElement(input); c->initialContextDoc=input;
    c->xpathCtxt->doc=input; c->xpathCtxt->node=c->node;
    xsltStackElemPtr v=xsltNewStackElem(c); CHECK(v);
    v->name=BAD_CAST "v"; v->tree=xmlDocGetRootElement(style->doc)->children->children->children; CHECK(v->tree);
    int before=live_docs; denied_hits=0; doc_seen=0; deny_list_after_doc=faulting;
    xmlXPathObjectPtr result=xsltEvalGlobalVariable(v,c);
    deny_list_after_doc=0;
    printf("denied=%d docs_delta=%d result=%d state=%d\n",denied_hits,live_docs-before,result!=NULL,c->state);
    if (faulting) {
        CHECK(denied_hits==1 && !result && c->state==XSLT_STATE_STOPPED);
        CHECK(live_docs==before);
    } else {
        CHECK(denied_hits==0 && result && v->computed && c->state==XSLT_STATE_OK);
        CHECK(live_docs==before+1);
        CHECK(result->nodesetval && result->nodesetval->nodeNr==1);
    }
    xsltFreeStackElem(v); xsltFreeTransformContext(c); xsltFreeStylesheet(style); xmlFreeDoc(input);
    xsltCleanupGlobals(); xmlCleanupParser(); CHECK(live_docs==0 && live_lists==0); return 0;
}
