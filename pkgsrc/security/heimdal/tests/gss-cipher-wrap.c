#include <openssl/evp.h>
#include <openssl/des.h>
#include <openssl/provider.h>
#include <stdint.h>
#include <errno.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
typedef unsigned char u_char;
typedef unsigned int OM_uint32;
typedef int krb5_error_code;
typedef int gss_qop_t;
typedef void *krb5_context;
typedef struct {struct { void *data; size_t length; } keyvalue;} krb5_keyblock;
typedef struct gss_buffer {size_t length; void *value;} *gss_buffer_t;
typedef struct gss_context {int ctx_id_mutex; int32_t seq; void *auth_context; int more_flags;} *gsskrb5_ctx;
#define LOCAL 1
#define GSS_S_FAILURE 1
#define GSS_S_COMPLETE 0
#define GSS_KRB5_MECHANISM 0
#define KRB5_KU_USAGE_SIGN 0
#define HEIMDAL_MUTEX_lock(p) do {if (*(p)) abort(); *(p)=1;} while(0)
#define HEIMDAL_MUTEX_unlock(p) do {if (!*(p)) abort(); *(p)=0;} while(0)
static int memset_s(void *p,size_t s,int v,size_t n) {(void)s;memset(p,v,n);return 0;}
static void _gsskrb5_encap_length(int n,size_t *l,size_t *t,int m) {(void)n;(void)m;*l=n;*t=n+32;}
static void *_gssapi_make_mech_header(void *p,size_t n,int m) {(void)n;(void)m;return p;}
static int arcfour_mic_cksum(krb5_context c,krb5_keyblock *k,int u,void *out,size_t n,void *a,size_t an,void *b,size_t bn,void *d,size_t dn) {(void)c;(void)k;(void)u;(void)a;(void)an;(void)b;(void)bn;(void)d;(void)dn;memset(out,0,n);return 0;}
static int arcfour_mic_key(krb5_context c,krb5_keyblock *k,void *in,size_t n,void *out,size_t on) {(void)c;(void)k;(void)in;(void)n;memset(out,0,on);return 0;}
static void _gsskrb5_release_buffer(OM_uint32 *m,gss_buffer_t b) {(void)m;free(b->value);b->value=NULL;b->length=0;}
static void krb5_auth_con_getlocalseqnumber(krb5_context c,void *a,int32_t *n) {(void)c;*n=((gsskrb5_ctx)a)->seq;}
static void krb5_auth_con_setlocalseqnumber(krb5_context c,void *a,int32_t n) {(void)c;((gsskrb5_ctx)a)->seq=n;}
static void _gsskrb5_encode_be_om_uint32(int32_t n,u_char *p) {p[0]=n>>24;p[1]=n>>16;p[2]=n>>8;p[3]=n;}
static int fail_new,fail_init,fail_update;
static int new_calls;
static EVP_CIPHER_CTX *t_new(void) {return fail_new && ++new_calls==fail_new?NULL:EVP_CIPHER_CTX_new();}
static int t_init(EVP_CIPHER_CTX *c,const EVP_CIPHER *cipher,ENGINE *e,const unsigned char *key,const unsigned char *iv,int enc) {return fail_init?0:EVP_CipherInit_ex(c,cipher,e,key,iv,enc);}
static int t_update(EVP_CIPHER_CTX *c,unsigned char *out,const unsigned char *in,unsigned int n) {return fail_update?0:EVP_Cipher(c,out,in,n);}
#define EVP_CIPHER_CTX_new t_new
#define EVP_CipherInit_ex t_init
#define EVP_Cipher t_update
#include "helper.inc"

#define IS_DCE_STYLE(ctx) 0
static void *_gsskrb5_make_header(void *p,size_t n,const char *type,int mech) {(void)n;(void)type;(void)mech;return (unsigned char *)p+2;}
static void krb5_generate_random_block(void *p,size_t n) {memset(p,3,n);}
#include "wrap-caller.inc"
int main(void) {
 OSSL_PROVIDER *a=OSSL_PROVIDER_load(NULL,"default"),*b=OSSL_PROVIDER_load(NULL,"legacy");
 struct gss_context state={0};unsigned char keydata[8]={1,2,3,4,5,6,7,8}, bytes[8]={1};krb5_keyblock key={{keydata,8}};
 struct gss_buffer msg={sizeof bytes,bytes},token={0};OM_uint32 minor=0;
 if(!a||!b)return 1;state.auth_context=&state;fail_new=2;new_calls=0;
 if(wrap_des(&minor,&state,NULL,1,0,&msg,NULL,&token,&key)!=GSS_S_FAILURE||state.seq||state.ctx_id_mutex||token.value)return 2;
 fail_new=0;new_calls=0;
 if(wrap_des(&minor,&state,NULL,1,0,&msg,NULL,&token,&key)!=GSS_S_COMPLETE||state.seq!=1||state.ctx_id_mutex||!token.value)return 3;
 free(token.value);OSSL_PROVIDER_unload(b);OSSL_PROVIDER_unload(a);puts("GSS DES wrap second-context failure/retry PASS");return 0;
}
