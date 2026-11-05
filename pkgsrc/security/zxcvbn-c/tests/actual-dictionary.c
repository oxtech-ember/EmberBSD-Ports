/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "zxcvbn-dictionary.h"
#include "dict-src.h"
#define COUNT(a) (sizeof(a)/sizeof((a)[0]))
static const ZxcvbnDictionaryData data = {
 ZXCVBN_DICTIONARY_ABI, sizeof(ZxcvbnDictionaryData),
 DictNodes, COUNT(DictNodes), WordEndBits, sizeof(WordEndBits),
 ChildLocs, COUNT(ChildLocs), sizeof(ChildLocs[0]), Ranks, COUNT(Ranks),
 ChildMap, sizeof(ChildMap), SizeChildMapEntry, EndCountLge, sizeof(EndCountLge),
 EndCountSml, sizeof(EndCountSml), CharSet, sizeof(CharSet), ROOT_NODE_LOC
};
int main(void) {
 const char *pwds[]={"password","p@ssw0rd","parol","privet","vitannya","ukrayina","Example!123", "0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789", "01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890",NULL};
 ZxcvbnDictionary *d=ZxcvbnDictionaryCreate(&data); if (!d) {perror("dictionary"); return 1;}
 for (int i=0;pwds[i];i++) {ZxcMatch_t *a=NULL,*b=NULL; double x=ZxcvbnMatch(pwds[i],NULL,&a), y=ZxcvbnMatchWithDictionary(d,pwds[i],NULL,&b); if(x!=y)return 2; ZxcMatch_t *p=a,*q=b; while(p && q){if(p->Begin!=q->Begin||p->Length!=q->Length||p->Type!=q->Type||p->Entrpy!=q->Entrpy||p->MltEnpy!=q->MltEnpy)return 3;p=p->Next;q=q->Next;} if(p||q)return 4; ZxcvbnFreeInfo(a);ZxcvbnFreeInfo(b);}
 ZxcMatch_t *bad=(ZxcMatch_t*)1; errno=0; if(ZxcvbnMatchWithDictionary(NULL,"x",NULL,&bad)!=-1||bad||errno!=EINVAL)return 5;
 bad=(ZxcMatch_t*)1; errno=0; if(ZxcvbnMatchWithDictionary(d,NULL,NULL,&bad)!=-1||bad||errno!=EINVAL)return 6;
 ZxcvbnDictionaryFree(d); puts("default and explicit dictionary scores/details, null handling: PASS");
}
