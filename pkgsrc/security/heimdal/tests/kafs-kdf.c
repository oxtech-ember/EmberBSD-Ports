#include <openssl/hmac.h>
#include <openssl/des.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#define EMBERBSD_BASE_HEIMDAL 1
#define HAVE_HCRYPTO_W_OPENSSL 1
#define KRB5DES_WEAK_KEY 1234
static int wipes;
static int memset_s(void *p, size_t n, int v, size_t len) { (void)n; wipes++; memset(p, v, len); return 0; }
static int fail_alloc, alloc_calls, force_weak;
static HMAC_CTX *test_new(void) { if (fail_alloc && ++alloc_calls == fail_alloc) return NULL; return HMAC_CTX_new(); }
static int test_weak(const_DES_cblock *key) { if (force_weak) return 1; return DES_is_weak_key(key); }
#define DES_is_weak_key test_weak
#define HMAC_CTX_new test_new
static int fail_update;
static int test_update(HMAC_CTX *c, const unsigned char *p, size_t n) {
    if (fail_update) return 0;
    return HMAC_Update(c, p, n);
}
#define HMAC_Update test_update
#include "kafs.inc"
int main(void) {
    unsigned char in[16], out[8];
    static const unsigned char expected[8]={0x07,0x83,0x8c,0x58,0xc1,0x1c,0x64,0xab};
    for (int i=0;i<16;i++) in[i]=(unsigned char)i;
    if (rxkad_derive_des_key(in,sizeof in,(char *)out) || memcmp(out,expected,8)) return 1;
    fail_update=1; memset(out, 0xa5, sizeof out);
    if (rxkad_derive_des_key(in,sizeof in,(char *)out)!=EINVAL) return 3;
    for (int i=0;i<8;i++) if (out[i]!=0xa5) return 4;
    fail_update=0; fail_alloc=2; alloc_calls=0; force_weak=1; wipes=0;
    if (rxkad_derive_des_key(in,sizeof in,(char *)out)!=ENOMEM || wipes<2) return 2;
    puts("KAFS KDF and allocation failure PASS"); return 0;
}
