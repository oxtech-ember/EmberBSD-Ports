/* SPDX-License-Identifier: BSD-2-Clause
 * AI-assisted EmberBSD structure-layout regression. */
#include <stdio.h>
#include <stddef.h>
#include <libxslt/xsltInternals.h>
int main(void) {
 printf("stack=%zu cache=%zu ctxt=%zu\n",sizeof(xsltStackElem),sizeof(xsltTransformCache),sizeof(xsltTransformContext));
 printf("fragment=%zu cache-count=%zu flags=%zu contextVariable=%zu localBase=%zu\n",offsetof(xsltStackElem,fragment),offsetof(xsltTransformCache,nbRVT),offsetof(xsltTransformContext,ctxtflags),offsetof(xsltTransformContext,contextVariable),offsetof(xsltTransformContext,localRVTBase));
#ifdef FIXED
 printf("cache=%zu tmp=%zu persistent=%zu local=%zu\n",offsetof(xsltTransformCache,rvtList),offsetof(xsltTransformContext,tmpRVTList),offsetof(xsltTransformContext,persistRVTList),offsetof(xsltTransformContext,localRVTList));
#else
 printf("cache=%zu tmp=%zu persistent=%zu local=%zu\n",offsetof(xsltTransformCache,RVT),offsetof(xsltTransformContext,tmpRVT),offsetof(xsltTransformContext,persistRVT),offsetof(xsltTransformContext,localRVT));
#endif
 return 0;
}
