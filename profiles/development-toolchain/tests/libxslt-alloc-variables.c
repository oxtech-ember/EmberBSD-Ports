/* SPDX-License-Identifier: BSD-2-Clause */
#include "variables.c"
#include "libxslt-alloc-common.h"
int main(int argc,char **argv) {
    CHECK(argc==2);
    CHECK(xmlMemSetup(test_free,test_malloc,test_realloc,test_strdup)==0);
    xmlInitParser(); xsltStylesheetPtr style=make_test_style(); CHECK(style);
    xmlDocPtr input=xmlReadMemory("<input/>",8,"input.xml",NULL,XML_PARSE_NONET); CHECK(input);
    xsltTransformContextPtr c=xsltNewTransformContext(style,input); CHECK(c);
    if (!strncmp(argv[1],"stack-",6)) {
        xsltStackElemPtr v=xsltNewStackElem(c); CHECK(v);
        xmlDocPtr d=xsltCreateRVT(c); CHECK(d);
        c->contextVariable=v;
        CHECK(xsltRegisterTmpRVT(c,d)==0);
        c->contextVariable=NULL; d->compression=XSLT_RVT_FUNC_RESULT;
        xsltStackElem selected={0};
        if (!strcmp(argv[1],"stack-select")) { selected.flags=(1<<1); c->contextVariable=&selected; }
        denied_size=sizeof(xsltRVTList); denied_hits=0;
        xsltFreeStackElem(v); denied_size=0;
        CHECK(denied_hits==0);
        xsltRVTListPtr list=selected.fragment ? selected.fragment : c->localRVTList;
        CHECK(list && list->RVT==d);
        if (selected.fragment) { xsltReleaseRVTList(c,selected.fragment); selected.fragment=NULL; }
        c->contextVariable=NULL;
    } else {
        xsltStackElemPtr v=xsltNewStackElem(c); CHECK(v);
        v->name=BAD_CAST "v";
        v->tree=xmlDocGetRootElement(style->doc)->children->children->children;
        CHECK(v->tree);
        int cached=!strcmp(argv[1],"eval-cached");
        if (cached) { xmlDocPtr d=xsltCreateRVT(c); CHECK(d); xsltReleaseRVT(c,d); }
        int docs_before=live_docs;
        denied_size=!strcmp(argv[1],"eval-doc") ? sizeof(xmlDoc) : sizeof(xsltRVTList);
        denied_hits=0;
        xmlXPathObjectPtr result=xsltEvalVariable(c,v,NULL); denied_size=0;
        CHECK(denied_hits>0 && !result && !v->fragment);
        CHECK(live_docs==docs_before);
        xsltFreeStackElem(v);
    }
    xsltFreeTransformContext(c); xsltFreeStylesheet(style); xmlFreeDoc(input);
    xsltCleanupGlobals(); xmlCleanupParser(); CHECK(live_docs==0 && live_lists==0); return 0;
}
