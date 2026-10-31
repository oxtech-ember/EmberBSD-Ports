#include <stdint.h>
#include <errno.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
typedef unsigned char u_char; typedef unsigned int OM_uint32; typedef int krb5_error_code; typedef int gss_qop_t; typedef void *krb5_context;
typedef struct {int keytype; struct {void *data; size_t length;} keyvalue;} krb5_keyblock;
typedef struct gss_buffer {size_t length; void *value;} *gss_buffer_t;
typedef struct gss_context {int ctx_id_mutex; int32_t seq; void *auth_context; int more_flags;} *gsskrb5_ctx;
typedef struct {int x;} EVP_CIPHER_CTX; typedef struct {int x;} EVP_CIPHER;
static const EVP_CIPHER *EVP_rc4(void) {static EVP_CIPHER c;return &c;}
static void EVP_CIPHER_CTX_init(EVP_CIPHER_CTX *c) {(void)c;}
static void EVP_CIPHER_CTX_cleanup(EVP_CIPHER_CTX *c) {(void)c;}
static int EVP_CipherInit_ex(EVP_CIPHER_CTX *c,const EVP_CIPHER *a,void *e,const void *k,const void *iv,int enc) {(void)c;(void)a;(void)e;(void)k;(void)iv;(void)enc;return 1;}
static int EVP_Cipher(EVP_CIPHER_CTX *c,void *o,const void *in,size_t n) {(void)c;memmove(o,in,n);return 1;}
#define LOCAL 1
#define GSS_S_FAILURE 1
#define GSS_S_COMPLETE 0
#define GSS_KRB5_MECHANISM 0
#define KRB5_KU_USAGE_SEAL 0
#define GSS_ARCFOUR_WRAP_TOKEN_SIZE 32
#define IS_DCE_STYLE(ctx) 0
#define HEIMDAL_MUTEX_lock(p) do {if (*(p)) abort(); *(p)=1;} while(0)
#define HEIMDAL_MUTEX_unlock(p) do {if (!*(p)) abort(); *(p)=0;} while(0)
static int memset_s(void *p,size_t s,int v,size_t n) {(void)s;memset(p,v,n);return 0;}
static void _gssapi_encap_length(size_t n,size_t *l,size_t *t,int m) {(void)m;*l=n;*t=n+32;}
static void *_gssapi_make_mech_header(void *p,size_t n,int m) {(void)n;(void)m;return p;}
static int force_cksum, force_key;
static int arcfour_mic_cksum(krb5_context c,krb5_keyblock *k,int u,void *out,size_t n,void *a,size_t an,void *b,size_t bn,void *d,size_t dn) {(void)c;(void)k;(void)u;(void)a;(void)an;(void)b;(void)bn;(void)d;(void)dn;memset(out,0,n);return force_cksum?EIO:0;}
static int arcfour_mic_key(krb5_context c,krb5_keyblock *k,void *in,size_t n,void *out,size_t on) {(void)c;(void)k;(void)in;(void)n;memset(out,0,on);return force_key?EIO:0;}
static void _gsskrb5_release_buffer(OM_uint32 *m,gss_buffer_t b) {(void)m;free(b->value);b->value=NULL;b->length=0;}
static void krb5_auth_con_getlocalseqnumber(krb5_context c,void *a,int32_t *n) {(void)c;*n=((gsskrb5_ctx)a)->seq;}
static void krb5_auth_con_setlocalseqnumber(krb5_context c,void *a,int32_t n) {(void)c;((gsskrb5_ctx)a)->seq=n;}
static void _gsskrb5_encode_be_om_uint32(int32_t n,u_char *p) {p[0]=n>>24;p[1]=n>>16;p[2]=n>>8;p[3]=n;}
static void krb5_generate_random_block(void *p,size_t n) {memset(p,3,n);}
#include "helper-legacy.inc"
#include "legacy-wrap.inc"
int main(void) {
 struct gss_context state={0}; unsigned char keydata[16]={0},bytes[8]={0};krb5_keyblock key={0,{keydata,16}};
 struct gss_buffer msg={sizeof bytes,bytes},token={0};OM_uint32 minor=0;state.auth_context=&state;
 force_cksum=1;if(_gssapi_wrap_arcfour(&minor,&state,NULL,1,0,&msg,NULL,&token,&key)!=GSS_S_FAILURE||state.ctx_id_mutex||state.seq!=1||token.value)return 1;
 force_cksum=0;force_key=1;if(_gssapi_wrap_arcfour(&minor,&state,NULL,1,0,&msg,NULL,&token,&key)!=GSS_S_FAILURE||state.ctx_id_mutex||state.seq!=2||token.value)return 2;
 puts("GSS legacy wrap failure mutex PASS");return 0;
}
