#!/usr/bin/env python3
"""Exercise the base PKCS#11 key ownership and public attribute selection.

This is a mock PKCS#11 backend using OpenSSL's real RSA methods; it does not
claim to validate a hardware token or Heimdal's ASN.1 decoder.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True, help='prepared Heimdal source')
parser.add_argument('--cc', type=Path, required=True, help='native C compiler')
parser.add_argument('--openssl-prefix', type=Path, required=True)
parser.add_argument('--sanitizers', action='store_true')
parser.add_argument('--analyze', action='store_true', help='also run Clang static analyzer')
args = parser.parse_args()
s=(args.source/'lib/hx509/ks_p11.c').read_text()
def take(a,b): return s[s.index(a):s.index(b,s.index(a))]
pre=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <openssl/rsa.h>
#include <openssl/bn.h>
#include <openssl/crypto.h>
#include <openssl/ec.h>
#include <openssl/obj_mac.h>
typedef void *hx509_context;typedef unsigned long CK_SESSION_HANDLE;typedef unsigned long CK_OBJECT_HANDLE;typedef unsigned long CK_ATTRIBUTE_TYPE;
typedef unsigned long CK_ULONG;typedef unsigned long CK_RV;typedef unsigned long CK_KEY_TYPE;typedef unsigned char CK_BYTE;typedef struct {CK_ULONG mechanism;void *parameter;CK_ULONG length;} CK_MECHANISM;typedef struct {unsigned long type;void *pValue;size_t ulValueLen;} CK_ATTRIBUTE;
#define CKR_OK 0
#define CKR_ATTRIBUTE_SENSITIVE 17
#define CKR_ATTRIBUTE_TYPE_INVALID 18
#define CK_UNAVAILABLE_INFORMATION ((unsigned long)-1)
#define P11FUNC(module,f,args) mock_##f args
#define CKM_RSA_PKCS 1
typedef struct {void *data;size_t length;} heim_octet_string;
#define CKA_MODULUS 1
#define CKA_PUBLIC_EXPONENT 2
#define CKA_KEY_TYPE 3
#define CKK_RSA 0
#define CKK_EC 3
struct p11_module {unsigned ref;};struct p11_slot {int dummy;};struct p11_rsa {struct p11_module *p;struct p11_slot *slot;CK_OBJECT_HANDLE private_key,public_key;};
struct key_ops {const void *key_oid;};struct key {unsigned ref;struct key_ops *ops;union {void *keydata;RSA *rsa;void *ecdsa;} private_key;void (*backend_free)(void *);};typedef struct key *hx509_private_key;
#define EMBERBSD_BASE_HEIMDAL 1
#define ASN1_OID_ID_PKCS1_RSAENCRYPTION ((void *)1)
#define ASN1_OID_ID_ECPUBLICKEY ((void *)2)
static int der_heim_oid_cmp(const void *a,const void *b){if(b==ASN1_OID_ID_PKCS1_RSAENCRYPTION)return *(const int *)a!=1;return a!=b;}
static void _hx509_private_eckey_free(void *a){free(a);}
struct hx509_collector {hx509_private_key key;};static BIGNUM *token_n,*token_e;static int fail_token;static CK_KEY_TYPE token_type=CKK_RSA;
static void _hx509_abort(const char *s){fputs(s,stderr);abort();}
static void p11_release_module(struct p11_module *p){if(!p->ref)abort();p->ref--;}
static CK_RV mock_GetAttributeValue(CK_SESSION_HANDLE session,CK_OBJECT_HANDLE object,CK_ATTRIBUTE *q,int count){(void)session;(void)object;(void)count;if(fail_token&&q->type!=CKA_KEY_TYPE)return 5;if(q->type==CKA_KEY_TYPE){if(!q->pValue||q->ulValueLen!=sizeof(token_type))return 1;memcpy(q->pValue,&token_type,sizeof(token_type));return CKR_OK;}BIGNUM *b=q->type==CKA_MODULUS?token_n:token_e;if(!b)return CKR_ATTRIBUTE_TYPE_INVALID;int n=BN_num_bytes(b);if(!q->pValue)q->ulValueLen=(size_t)n;else {if(q->ulValueLen<(size_t)n)return 1;BN_bn2bin(b,q->pValue);q->ulValueLen=(size_t)n;}return CKR_OK;}
static int hx509_private_key_init(hx509_private_key *k,void *a,void *b){(void)a;(void)b;*k=calloc(1,sizeof(**k));if(*k)(*k)->ref=1;return *k?0:ENOMEM;}
static void hx509_private_key_assign_rsa(hx509_private_key k,RSA *r){k->private_key.rsa=r;}
static int hx509_private_key_free(hx509_private_key *);
static void hx509_set_error_string(hx509_context ctx,int a,int b,const char *s){(void)ctx;(void)a;(void)b;(void)s;}
static int p11_rsa_public_encrypt(int a,const unsigned char*b,unsigned char*c,RSA*d,int e){(void)a;(void)b;(void)c;(void)d;(void)e;return -1;}
static int p11_rsa_public_decrypt(int a,const unsigned char*b,unsigned char*c,RSA*d,int e){return p11_rsa_public_encrypt(a,b,c,d,e);}
static RSA *mock_signing_key; static int mock_sign_calls;
static int p11_get_session(hx509_context c,struct p11_module *p,struct p11_slot *s,void *l,CK_SESSION_HANDLE *out){(void)c;(void)p;(void)s;(void)l;*out=1;return 0;}
static int p11_put_session(struct p11_module *p,struct p11_slot *s,CK_SESSION_HANDLE h){(void)p;(void)s;(void)h;return 0;}
static CK_RV mock_SignInit(CK_SESSION_HANDLE h,CK_MECHANISM *m,CK_OBJECT_HANDLE k){(void)h;(void)k;return m->mechanism==CKM_RSA_PKCS?CKR_OK:1;}
static CK_RV mock_Sign(CK_SESSION_HANDLE h,CK_BYTE *data,CK_ULONG len,CK_BYTE *out,CK_ULONG *size){(void)h;if(!mock_signing_key)return 1;int n=RSA_private_encrypt((int)len,data,out,mock_signing_key,RSA_PKCS1_PADDING);if(n<0||(CK_ULONG)n>*size)return 1;*size=(CK_ULONG)n;mock_sign_calls++;return CKR_OK;}
static CK_RV mock_DecryptInit(CK_SESSION_HANDLE h,CK_MECHANISM *m,CK_OBJECT_HANDLE k){(void)h;(void)m;(void)k;return 1;}
static CK_RV mock_Decrypt(CK_SESSION_HANDLE h,CK_BYTE *data,CK_ULONG len,CK_BYTE *out,CK_ULONG *size){(void)h;(void)data;(void)len;(void)out;(void)size;return 1;}
'''
asn=r"""
typedef struct {unsigned char *data;size_t length;int negative;} heim_integer;
typedef struct {heim_integer modulus,publicExponent;} RSAPublicKey;
typedef struct {struct {int algorithm;} algorithm;struct {unsigned char *data;size_t length;} subjectPublicKey;} SubjectPublicKeyInfo;
typedef struct {struct {SubjectPublicKeyInfo subjectPublicKeyInfo;} tbsCertificate;unsigned ref;hx509_private_key private_key;} Certificate;
typedef Certificate *hx509_cert;
static const Certificate *_hx509_get_cert(hx509_cert c){return c;}
static hx509_cert hx509_cert_ref(hx509_cert c){c->ref++;return c;}
static void hx509_cert_free(hx509_cert c){if(!c||!c->ref)abort();c->ref--;if(!c->ref&&c->private_key)hx509_private_key_free(&c->private_key);}
static hx509_private_key _hx509_private_key_ref(hx509_private_key k){k->ref++;return k;}
static int decode_RSAPublicKey(const void *data,size_t len,RSAPublicKey *out,size_t *used){
 const unsigned char *p=data;RSA *r=d2i_RSAPublicKey(NULL,&p,len);if(!r)return EINVAL;const BIGNUM *n,*e;RSA_get0_key(r,&n,&e,NULL);
 out->modulus.length=BN_num_bytes(n);out->publicExponent.length=BN_num_bytes(e);out->modulus.negative=out->publicExponent.negative=0;
 out->modulus.data=malloc(out->modulus.length);out->publicExponent.data=malloc(out->publicExponent.length);if(!out->modulus.data||!out->publicExponent.data)abort();
 BN_bn2bin(n,out->modulus.data);BN_bn2bin(e,out->publicExponent.data);*used=(size_t)(p-(const unsigned char*)data);RSA_free(r);return 0;}
static void free_RSAPublicKey(RSAPublicKey *p){free(p->modulus.data);free(p->publicExponent.data);}
"""
crypto=(args.source/'lib/hx509/crypto.c').read_text(); realfree=crypto[crypto.index('int\nhx509_private_key_free('):crypto.index('\nvoid\nhx509_private_key_assign_rsa(',crypto.index('int\nhx509_private_key_free('))]
certcode=(args.source/'lib/hx509/cert.c').read_text(); realassign=certcode[certcode.index('int\n_hx509_cert_assign_key('):certcode.index('\n/**',certcode.index('int\n_hx509_cert_assign_key('))]
callbacks=take('static int\np11_rsa_private_encrypt(', 'static int\np11_rsa_init(')
method=take('static int\np11_rsa_init(', '#if !defined(HEIMDAL_P11_OPAQUE_OPENSSL)')+take('/* The method is immutable once published', '\n#endif')
optional=take('static int\np11_getattr_bn_optional(', '/* Certificates are visited')
cache=take('struct p11_cert_pub {','\n#endif\n\n#if defined(HEIMDAL_P11_OPAQUE_OPENSSL)\nstatic int\np11_collect_private_native(')
collect=take('static int\np11_collect_private_native(', '\n#endif\n\nstatic int\ncollect_private_key(')
post=r'''
static void run_case(int have_n, int have_e, int fail_token_value,
                     int ambiguous, int mismatch) {
    struct p11_module p={1}; struct p11_slot slot={0};
    struct hx509_collector collector={0}; struct p11_collect_state st={&collector,NULL};
    Certificate cert={.ref=1}; char id='a'; CK_ATTRIBUTE q[1]={{0,&id,1}};
    token_type=CKK_RSA;
    struct p11_cert_pub *entry=calloc(1,sizeof(*entry)); if(!entry)abort();
    entry->id=malloc(1); if(!entry->id)abort(); entry->id[0]=id; entry->id_len=1;
    entry->n=BN_new(); entry->e=BN_new(); if(!entry->n||!entry->e)abort();
    BN_set_word(entry->n,3233); BN_set_word(entry->e,17);
    entry->cert=hx509_cert_ref(&cert); entry->ambiguous=ambiguous; st.public_keys=entry;
    token_n=have_n?BN_dup(entry->n):NULL; token_e=have_e?BN_dup(entry->e):NULL;
    if(mismatch&&token_n)BN_add_word(token_n,2); fail_token=fail_token_value;
    int ret=p11_collect_private_native(NULL,&p,&slot,0,0,&st,q);
    if(ambiguous||mismatch){if(ret!=EINVAL||cert.private_key||p.ref!=1)abort();}
    else if(fail_token){if(ret!=EIO||cert.private_key||p.ref!=1)abort();}
    else {
        const BIGNUM *n,*e; if(ret||!cert.private_key||p.ref!=2)abort();
        RSA_get0_key(cert.private_key->private_key.rsa,&n,&e,NULL);
        if(BN_cmp(n,entry->n)||BN_cmp(e,entry->e))abort();
        hx509_private_key extra=cert.private_key; extra->ref++;
        hx509_private_key_free(&extra); if(!extra||p.ref!=2)abort();
        hx509_private_key_free(&cert.private_key); if(cert.private_key||p.ref!=1)abort();
    }
    BN_free(token_n); BN_free(token_e); token_n=token_e=NULL;
    p11_free_cert_pubs(&st); if(cert.ref!=1)abort(); fail_token=0;
}
static void cache_test(void) {
    struct p11_collect_state st={0}; Certificate rsa_cert={.ref=1}, ec_cert={.ref=1}, other={.ref=1};
    char id='a'; rsa_cert.tbsCertificate.subjectPublicKeyInfo.algorithm.algorithm=1;
    RSA *rsa=RSA_new(); BIGNUM *n=BN_new(),*e=BN_new(); if(!rsa||!n||!e)abort();
    BN_set_word(n,3233); BN_set_word(e,17); if(!RSA_set0_key(rsa,n,e,NULL))abort();
    unsigned char *der=NULL; int len=i2d_RSAPublicKey(rsa,&der); if(len<=0)abort();
    rsa_cert.tbsCertificate.subjectPublicKeyInfo.subjectPublicKey.data=der;
    rsa_cert.tbsCertificate.subjectPublicKeyInfo.subjectPublicKey.length=(size_t)len*8;
    if(p11_cache_cert_pub(&st,&id,1,&rsa_cert)||p11_cache_cert_pub(&st,&id,1,&rsa_cert)||!st.public_keys||st.public_keys->ambiguous)abort();
    OPENSSL_free(der); RSA_free(rsa);
    EC_KEY *ec=EC_KEY_new_by_curve_name(NID_X9_62_prime256v1); if(!ec||EC_KEY_generate_key(ec)!=1)abort();
    unsigned char *point=NULL; int plen=i2o_ECPublicKey(ec,&point); if(plen<=0)abort();
    ec_cert.tbsCertificate.subjectPublicKeyInfo.algorithm.algorithm=2;
    ec_cert.tbsCertificate.subjectPublicKeyInfo.subjectPublicKey.data=point;
    ec_cert.tbsCertificate.subjectPublicKeyInfo.subjectPublicKey.length=(size_t)plen*8;
    if(p11_cache_cert_pub(&st,&id,1,&ec_cert)||st.public_keys->ambiguous)abort();
    OPENSSL_free(point); EC_KEY_free(ec);
    struct p11_module module={1}; struct p11_slot slot={0}; struct hx509_collector collector={0};
    st.collector=&collector; CK_ATTRIBUTE query[1]={{0,&id,1}};
    token_type=CKK_EC;
    if(p11_collect_private_native(NULL,&module,&slot,0,0,&st,query)||rsa_cert.private_key||ec_cert.private_key||module.ref!=1)abort();
    token_type=CKK_RSA; token_n=BN_dup(st.public_keys->n); token_e=BN_dup(st.public_keys->e);
    if(p11_collect_private_native(NULL,&module,&slot,0,0,&st,query)||!rsa_cert.private_key||ec_cert.private_key||module.ref!=2)abort();
    hx509_private_key_free(&rsa_cert.private_key); if(module.ref!=1)abort(); BN_free(token_n); BN_free(token_e); token_n=token_e=NULL;
    rsa=RSA_new(); n=BN_new(); e=BN_new(); if(!rsa||!n||!e)abort();
    BN_set_word(n,3235); BN_set_word(e,17); if(!RSA_set0_key(rsa,n,e,NULL))abort();
    der=NULL; len=i2d_RSAPublicKey(rsa,&der); if(len<=0)abort();
    other.tbsCertificate.subjectPublicKeyInfo.algorithm.algorithm=1;
    other.tbsCertificate.subjectPublicKeyInfo.subjectPublicKey.data=der;
    other.tbsCertificate.subjectPublicKeyInfo.subjectPublicKey.length=(size_t)len*8;
    if(p11_cache_cert_pub(&st,&id,1,&other)||!st.public_keys->ambiguous)abort();
    OPENSSL_free(der); RSA_free(rsa); p11_free_cert_pubs(&st);
    if(rsa_cert.ref!=1||ec_cert.ref!=1||other.ref!=1)abort();
}
static void signing_test(void) {
    struct p11_module p={1}; struct p11_slot slot={0}; struct hx509_collector collector={0};
    struct p11_collect_state st={&collector,NULL}; Certificate cert={.ref=1}; char id='s';
    CK_ATTRIBUTE q[1]={{0,&id,1}}; struct p11_cert_pub *entry=calloc(1,sizeof(*entry));
    BIGNUM *exponent=BN_new(); mock_signing_key=RSA_new(); if(!entry||!exponent||!mock_signing_key)abort();
    BN_set_word(exponent,RSA_F4); if(RSA_generate_key_ex(mock_signing_key,2048,exponent,NULL)!=1)abort(); BN_free(exponent);
    const BIGNUM *n,*e; RSA_get0_key(mock_signing_key,&n,&e,NULL); entry->n=BN_dup(n); entry->e=BN_dup(e);
    entry->id=malloc(1); if(!entry->n||!entry->e||!entry->id)abort(); entry->id[0]=id; entry->id_len=1;
    entry->cert=hx509_cert_ref(&cert); st.public_keys=entry; token_type=CKK_RSA;
    token_n=BN_dup(n); token_e=BN_dup(e); if(!token_n||!token_e)abort();
    if(p11_collect_private_native(NULL,&p,&slot,0,0,&st,q)||!cert.private_key||p.ref!=2)abort();
    const unsigned char message[]="ordinary token signing"; unsigned char sig[256],plain[256];
    int signed_len=RSA_private_encrypt(sizeof(message)-1,message,sig,cert.private_key->private_key.rsa,RSA_PKCS1_PADDING);
    if(signed_len<=0||mock_sign_calls!=1)abort();
    int plain_len=RSA_public_decrypt(signed_len,sig,plain,mock_signing_key,RSA_PKCS1_PADDING);
    if(plain_len!=(int)sizeof(message)-1||memcmp(plain,message,(size_t)plain_len))abort();
    hx509_private_key_free(&cert.private_key); if(p.ref!=1)abort(); p11_free_cert_pubs(&st); if(cert.ref!=1)abort();
    BN_free(token_n);BN_free(token_e);token_n=token_e=NULL;RSA_free(mock_signing_key);mock_signing_key=NULL;
}
static void unmatched_test(void) {
    struct p11_module p={1}; struct p11_slot slot={0}; struct p11_collect_state st={0};
    CK_ATTRIBUTE q[1]={{0,NULL,0}}; token_type=CKK_RSA; fail_token=1; token_n=BN_new(); token_e=BN_new();
    if(!token_n||!token_e)abort(); BN_set_word(token_n,3233); BN_set_word(token_e,17);
    if(p11_collect_private_native(NULL,&p,&slot,0,0,&st,q)||p.ref!=1)abort();
    BN_free(token_n); BN_free(token_e); token_n=token_e=NULL; fail_token=0;
}
int main(void) {
    unmatched_test(); cache_test(); signing_test(); run_case(1,1,0,0,0); run_case(0,1,0,0,0); run_case(1,0,0,0,0);
    run_case(0,0,0,0,0); run_case(1,1,1,0,0); run_case(0,0,0,1,0); run_case(1,1,0,0,1);
    puts("P11 mixed RSA/EC, attributes, signing and ownership PASS"); return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='heimdal-p11-test-') as temp:
    fixture = Path(temp) / 'fixture.c'
    binary = Path(temp) / 'fixture'
    fixture.write_text(pre+asn+realfree+realassign+callbacks+method+optional+cache+collect+post)
    prefix = args.openssl_prefix
    command = [str(args.cc), '-I'+str(prefix/'include'), '-L'+str(prefix/'lib'),
               '-Wl,-rpath,'+str(prefix/'lib'), str(fixture), '-lcrypto', '-o', str(binary)]
    if args.sanitizers:
        command[1:1] = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    subprocess.run(command, check=True)
    subprocess.run([str(binary)], check=True)
    if args.analyze:
        subprocess.run([str(args.cc), '--analyze', '-I'+str(prefix/'include'),
                        str(fixture), '-o', '/dev/null'], check=True)
