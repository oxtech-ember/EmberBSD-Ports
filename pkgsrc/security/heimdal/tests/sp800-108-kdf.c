#include <openssl/hmac.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int memset_s(void *p, size_t n, int v, size_t len) { (void)n; memset(p, v, len); return 0; }
typedef void *krb5_context;
typedef int krb5_error_code;
typedef struct { size_t length; void *data; } krb5_data;
#define heim_assert(x, s) assert(x)
#define EMBERBSD_BASE_HEIMDAL 1
#define HAVE_HCRYPTO_W_OPENSSL 1
static int krb5_enomem(krb5_context c) { (void)c; return ENOMEM; }
static void _krb5_put_int(unsigned char *p, size_t n, int len) { for (int i=len-1;i>=0;i--) {p[i]=n&255;n>>=8;} }
static int fail_alloc;
static HMAC_CTX *test_new(void) { return fail_alloc ? NULL : HMAC_CTX_new(); }
#define HMAC_CTX_new test_new
static int fail_update, updates;
static int test_update(HMAC_CTX *c, const unsigned char *p, size_t n) {
 if (fail_update && ++updates == fail_update) return 0;
 return HMAC_Update(c, p, n);
}
#define HMAC_Update test_update
#include "kdf.inc"
int main(void) {
 unsigned char key[]={0,1,2,3}, label[]="label", ctx[]="context", out[48];
 krb5_data k={sizeof key,key}, l={sizeof label-1,label}, x={sizeof ctx-1,ctx}, o={sizeof out,out};
 if (_krb5_SP800_108_HMAC_KDF(NULL,&k,&l,&x,EVP_sha256(),&o)) return 1;
 static const unsigned char expected[48] = {
  0xd4,0xaa,0x7d,0xb1,0xda,0x16,0x89,0x35,0x90,0xb1,0x0c,0x62,0x27,0xa2,0x27,0xbb,
  0xfd,0x04,0x77,0x47,0x74,0x45,0x3b,0xbb,0xd9,0x08,0xee,0xb9,0xbf,0x8e,0x4e,0xfa,
  0x22,0xec,0x49,0xba,0x32,0x29,0x0c,0x55,0x1b,0x0d,0x2b,0x58,0x1a,0x6c,0xcf,0x30 };
 if (memcmp(out, expected, sizeof out)) return 3;
 fail_update=6; updates=0; memset(out, 0xa5, sizeof out);
 if (_krb5_SP800_108_HMAC_KDF(NULL,&k,&l,&x,EVP_sha256(),&o)!=EINVAL) return 4;
 for (size_t i=0;i<sizeof out;i++) if (out[i] != 0) return 5;
 fail_update=0; fail_alloc=1;
 if (_krb5_SP800_108_HMAC_KDF(NULL,&k,&l,&x,EVP_sha256(),&o)!=ENOMEM) return 2;
 puts("SP800-108 HMAC KDF and allocation failure PASS"); return 0;
}
