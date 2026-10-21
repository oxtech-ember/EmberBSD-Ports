/* SPDX-License-Identifier: BSD-2-Clause */
/* Functional error paths use valid arguments and the actual configured sources. */
#include "libexslt/common.c"
#include "libexslt/strings.c"
#include "libexslt/dynamic.c"
#include "libexslt/functions.c"
#include "libxslt-alloc-common.h"
int main(int argc,char **argv) {
    CHECK(argc==3);
    int faulting=strcmp(argv[2],"ok")!=0;
    CHECK(xmlMemSetup(test_free,test_malloc,test_realloc,test_strdup)==0);
    xmlInitParser(); exsltFuncRegister();
    const char *function_style="<xsl:stylesheet version='1.0' xmlns:xsl='http://www.w3.org/1999/XSL/Transform' xmlns:func='http://exslt.org/functions' xmlns:m='urn:test' extension-element-prefixes='func'><func:function name='m:f'><func:result><n/></func:result></func:function><xsl:template match='/'/></xsl:stylesheet>";
    xsltStylesheetPtr style;
    if (!strcmp(argv[1],"result")) {
        xmlDocPtr sd=xmlReadMemory(function_style,(int)strlen(function_style),"func.xsl",NULL,XML_PARSE_NONET);
        CHECK(sd); style=xsltParseStylesheetDoc(sd);
    } else style=make_test_style();
    CHECK(style);
    xmlDocPtr input=xmlReadMemory("<input/>",8,"input.xml",NULL,XML_PARSE_NONET); CHECK(input);
    xsltTransformContextPtr c=xsltNewTransformContext(style,input); CHECK(c);
    c->node=xmlDocGetRootElement(input);
    c->initialContextDoc=input; c->xpathCtxt->doc=input; c->xpathCtxt->node=c->node;
    xmlXPathParserContextPtr xp=xmlXPathNewParserContext(BAD_CAST "",c->xpathCtxt); CHECK(xp);
    exsltFuncData *data=NULL; xmlNodePtr inst=NULL; exsltFuncResultPreComp comp={0};
    if (!strcmp(argv[1],"result")) {
        data=xsltGetExtData(c,EXSLT_FUNCTIONS_NAMESPACE); CHECK(data);
        inst=xmlDocGetRootElement(style->doc)->children->children; CHECK(inst && inst->children);
    } else if (!strcmp(argv[1],"map")) {
        valuePush(xp,xmlXPathNewNodeSet(c->node));
        valuePush(xp,xmlXPathNewString(BAD_CAST "'v'"));
    } else if (strcmp(argv[1],"return-string")) {
        valuePush(xp,xmlXPathNewString(BAD_CAST "a b"));
    }
    int before=live_docs;
    denied_hits=0; doc_seen=0; deny_list_after_doc=faulting;
    if (!strcmp(argv[1],"node-set")) exsltNodeSetFunction(xp,1);
    else if (!strcmp(argv[1],"tokenize")) exsltStrTokenizeFunction(xp,1);
    else if (!strcmp(argv[1],"split")) exsltStrSplitFunction(xp,1);
    else if (!strcmp(argv[1],"return-string")) exsltStrReturnString(xp,BAD_CAST "v",1);
    else if (!strcmp(argv[1],"map")) exsltDynMapFunction(xp,2);
    else if (!strcmp(argv[1],"result")) exsltFuncResultElem(c,c->node,inst,(xsltElemPreCompPtr)&comp);
    else return 2;
    deny_list_after_doc=0;
    printf("denied=%d docs_delta=%d xpath_error=%d function_error=%d\n",denied_hits,live_docs-before,xp->error,data ? data->error : 0);
    if (faulting) {
        CHECK(denied_hits==1);
        CHECK(data ? data->error!=0 : xp->error==XPATH_MEMORY_ERROR);
        CHECK(live_docs==before);
    } else {
        CHECK(denied_hits==0 && xp->error==0 && (!data || data->error==0));
        CHECK(live_docs==before+1);
        xmlXPathObjectPtr value=data ? data->result : xp->value;
        CHECK(value && value->nodesetval && value->nodesetval->nodeNr>0);
        if (!strcmp(argv[1],"tokenize") || !strcmp(argv[1],"split")) CHECK(value->nodesetval->nodeNr==2);
        xmlChar *text=xmlXPathCastToString(value); CHECK(text);
        const char *expected=data ? "" : (!strcmp(argv[1],"node-set") ? "a b" :
            ((!strcmp(argv[1],"tokenize") || !strcmp(argv[1],"split")) ? "a" : "v"));
        CHECK(!strcmp((const char *)text,expected)); xmlFree(text);
    }
    if (data && data->result) { xmlXPathFreeObject(data->result); data->result=NULL; }
    xmlXPathFreeParserContext(xp); xsltFreeTransformContext(c);
    xsltFreeStylesheet(style); xmlFreeDoc(input);
    xsltCleanupGlobals(); xmlCleanupParser(); CHECK(live_docs==0 && live_lists==0); return 0;
}
