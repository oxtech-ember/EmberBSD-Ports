/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include "zxcvbn-dictionary.h"
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t nodes[]={1,0}, children32[]={1};
static uint16_t children16[]={1}, ranks[]={0,1};
static uint8_t ends[]={2}, maps[]={0,1}, small[]={1,1}, large[]={0,0};
static char charset[]="a";
static ZxcvbnDictionaryData valid(void) {
 ZxcvbnDictionaryData d={ZXCVBN_DICTIONARY_ABI,sizeof(d),nodes,2,ends,1,children16,1,2,ranks,2,maps,2,1,large,0,small,2,charset,2,0};return d;
}
static void reject(const char *name, ZxcvbnDictionaryData *d){errno=0;ZxcvbnDictionary *p=ZxcvbnDictionaryCreate(d); if(p||errno!=EINVAL){fprintf(stderr,"FAIL: %s accepted errno=%d\n",name,errno);exit(1);}}
#define BAD(n,field,value) do {ZxcvbnDictionaryData d=valid(); d.field=(value);reject(n,&d);}while(0)
struct thread_args { ZxcvbnDictionary *dict; double default_score, custom_score; };
static void *worker(void *v){struct thread_args *a=v; for(int i=0;i<1000;i++){double x=ZxcvbnMatch("password",NULL,NULL), y=ZxcvbnMatchWithDictionary(a->dict,"a",NULL,NULL);if(x!=a->default_score||y!=a->custom_score) abort();} return NULL;}
int main(void){
 ZxcvbnDictionaryData d=valid(); ZxcvbnDictionary *p=ZxcvbnDictionaryCreate(&d); if(!p){perror("valid16");return 1;} ZxcvbnDictionaryFree(p);
 d.Children=children32;d.ChildWidth=4;p=ZxcvbnDictionaryCreate(&d);if(!p){perror("valid32");return 2;}
 struct thread_args args={p,ZxcvbnMatch("password",NULL,NULL),ZxcvbnMatchWithDictionary(p,"a",NULL,NULL)};
 pthread_t threads[4];for(int i=0;i<4;i++)if(pthread_create(&threads[i],NULL,worker,&args))return 3;for(int i=0;i<4;i++)pthread_join(threads[i],NULL);ZxcvbnDictionaryFree(p);
 BAD("abi",AbiVersion,2); BAD("structsize",StructSize,0); BAD("null-nodes",Nodes,NULL); BAD("nodes-count",NodeCount,1);

 BAD("child-width",ChildWidth,3); BAD("child-count",ChildCount,0); BAD("word-bytes",WordEndBytes,0); BAD("rank-count",RankCount,1); BAD("short-small",SmallCount,1); BAD("root",Root,2); BAD("charset-size",CharSetSize,1); BAD("map-width",ChildMapWidth,0); BAD("map-bytes",ChildMapBytes,1);
 {d=valid();d.LargeCount=1;d.LargeCounts=NULL;reject("missing-large",&d);}
 charset[0]=0;d=valid();reject("charset-nul",&d);charset[0]='a';
 maps[1]=2;d=valid();reject("map-padding",&d);maps[1]=1;
 nodes[0]=2;d=valid();reject("map-index",&d);nodes[0]=1;
 nodes[0]=(2u<<14)|1;d=valid();reject("child-slice",&d);nodes[0]=1;
 children16[0]=2;d=valid();reject("child-node",&d);children16[0]=0;d=valid();reject("cycle",&d);children16[0]=1;
 small[1]=2;d=valid();reject("subtree-count",&d);small[1]=1;
 ranks[1]=0;d=valid();reject("zero-rank",&d);ranks[1]=1;
 ends[0]=0;d=valid();reject("rank-mismatch",&d);ends[0]=2;

 {uint32_t dn[]={1,0}, dc[]={1,1}; uint16_t dr[]={0,1,2}; uint8_t de[]={2}, dm[]={0,3}, ds[]={2,1}; const char *chars="ab";
  d=valid(); d.Nodes=dn; d.Children=dc; d.ChildWidth=4; d.ChildCount=2; d.Ranks=dr;d.RankCount=3;d.WordEnds=de;d.ChildMap=dm;d.SmallCounts=ds;d.CharSet=chars;d.CharSetSize=3;
  p=ZxcvbnDictionaryCreate(&d);if(!p){perror("valid shared DAG");return 7;}ZxcvbnDictionaryFree(p); dc[1]=0; reject("shared DAG backedge",&d);
 }
 puts("validator invalid-data matrix, shared DAG and concurrent interleaving: PASS"); return 0;
}
