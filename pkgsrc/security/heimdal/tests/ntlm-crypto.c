#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/rand.h>
#include <openssl/md4.h>
#include <openssl/provider.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define HNTLM_ERR_CRYPTO 1001
#define HNTLM_ERR_RAND 1002
#define HNTLM_ERR_INVALID_LENGTH 1003
struct ntlm_buf { size_t length; void *data; };
static int check_wipe, observed_wipe;
static void *wipe_target;
static void heim_ntlm_free_buf(struct ntlm_buf *b) { if (check_wipe && b->data == wipe_target && b->length == 16) { unsigned char *p = b->data; int zero = 1; for (size_t i=0;i<16;i++) zero &= p[i] == 0; observed_wipe |= zero; } free(b->data); b->data=NULL; b->length=0; }
static int memset_s(void *p, size_t n, int v, size_t l) { (void)n; memset(p,v,l); return 0; }
static int fail_alloc, fail_update, update_calls, fail_rand, fail_cipher;
static int ntest_rand(unsigned char *p, int n) { if (fail_rand) { wipe_target=p; memset(p, 0xa5, n); return 0; } return RAND_bytes(p,n); }
static int ntest_cipher(EVP_CIPHER_CTX *c, unsigned char *out, const unsigned char *in, unsigned int n) { if (fail_cipher) { wipe_target=out; memset(out, 0xa5, n); return 0; } return EVP_Cipher(c,out,in,n); }
#define RAND_bytes ntest_rand
#define EVP_Cipher ntest_cipher
static HMAC_CTX *ntest_hmac_new(void) { return fail_alloc ? NULL : HMAC_CTX_new(); }
static int ntest_update(HMAC_CTX *c, const unsigned char *p, size_t n) { if (fail_update && ++update_calls == fail_update) return 0; return HMAC_Update(c,p,n); }
#define HMAC_Update ntest_update
#define NTLM_HMAC_DECLARE(name) HMAC_CTX *name
#define NTLM_HMAC_INIT(name) (((name) = ntest_hmac_new()) != NULL)
#define NTLM_HMAC_FREE(name) HMAC_CTX_free(name)
#define NTLM_HMAC_OK(expr) ((expr) == 1)
#define NTLM_CIPHER_DECLARE(name) EVP_CIPHER_CTX *name
#define NTLM_CIPHER_INIT(name) (((name) = EVP_CIPHER_CTX_new()) != NULL)
#define NTLM_CIPHER_FREE(name) EVP_CIPHER_CTX_free(name)
static int ascii2ucs2le(const char *input, int upper, struct ntlm_buf *out) {
    (void)upper; size_t n = strlen(input); out->length = n * 2;
    out->data = calloc(1, out->length ? out->length : 1);
    if (!out->data) return ENOMEM;
    for (size_t i=0;i<n;i++) ((unsigned char *)out->data)[i*2]=(unsigned char)input[i];
    return 0;
}
#include "functions.inc"
int main(void) {
    OSSL_PROVIDER *a=OSSL_PROVIDER_load(NULL,"default"), *b=OSSL_PROVIDER_load(NULL,"legacy");
    if (!a || !b) return 1;
    unsigned char key[16]={0}, challenge[8]={1}, nonce[8]={2}, out[16], expected[16];
    unsigned char msg[16]; memcpy(msg,challenge,8);memcpy(msg+8,nonce,8);
    unsigned int n=0;
    if (!HMAC(EVP_md5(),key,16,msg,sizeof msg,expected,&n) || n!=16) return 2;
    if (heim_ntlm_derive_ntlm2_sess(key,nonce,8,challenge,out) || memcmp(out,expected,16)) return 3;
    memset(out,0xa5,16);fail_update=1; update_calls=0;
    if (heim_ntlm_derive_ntlm2_sess(key,nonce,8,challenge,out)!=HNTLM_ERR_CRYPTO) return 4;
    for (int i=0;i<16;i++) if (out[i]) return 5;
    struct ntlm_buf failed_answer={0};
    unsigned char v2key[16];
    fail_update=3; update_calls=0;
    if (heim_ntlm_calculate_lm2(key,16,"u","t",challenge,v2key,&failed_answer)!=HNTLM_ERR_CRYPTO ||
        failed_answer.data != NULL || failed_answer.length != 0) return 10;
    fail_update=0; fail_alloc=1;
    if (heim_ntlm_derive_ntlm2_sess(key,nonce,8,challenge,out)!=ENOMEM) return 6;
    memset(v2key, 0xa5, 16);
    if (heim_ntlm_ntlmv2_key(key,16,"u","t",0,v2key)!=ENOMEM) return 11;
    for (int i=0;i<16;i++) if (v2key[i]) return 12;
    fail_alloc=0;
    struct ntlm_buf base={16,key}, session={0}, encrypted={0}, recovered={0};
    if (heim_ntlm_keyex_wrap(&base,&session,&encrypted)) return 7;
    if (heim_ntlm_keyex_unwrap(&base,&encrypted,&recovered)) return 8;
    if (session.length!=16 || recovered.length!=16 || memcmp(session.data,recovered.data,16)) return 9;
    heim_ntlm_free_buf(&session);heim_ntlm_free_buf(&recovered);
    check_wipe=1; fail_rand=1; observed_wipe=0;
    if (heim_ntlm_keyex_wrap(&base,&session,&recovered)!=HNTLM_ERR_RAND || !observed_wipe) return 13;
    fail_rand=0; fail_cipher=1; observed_wipe=0;
    if (heim_ntlm_keyex_unwrap(&base,&encrypted,&recovered)!=HNTLM_ERR_CRYPTO || !observed_wipe) return 14;
    check_wipe=0; heim_ntlm_free_buf(&encrypted);
    OSSL_PROVIDER_unload(b); OSSL_PROVIDER_unload(a);
    puts("NTLM HMAC and key wrap valid-data/failure tests PASS"); return 0;
}
