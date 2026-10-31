#include <openssl/evp.h>
#include <openssl/provider.h>
#include <errno.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
static int fail_new, fail_init, fail_update;
static EVP_CIPHER_CTX *t_new(void) { return fail_new ? NULL : EVP_CIPHER_CTX_new(); }
static int t_init(EVP_CIPHER_CTX *c, const EVP_CIPHER *cipher, ENGINE *e, const unsigned char *k, const unsigned char *iv, int enc) { return fail_init ? 0 : EVP_CipherInit_ex(c,cipher,e,k,iv,enc); }
static int t_update(EVP_CIPHER_CTX *c, unsigned char *out, const unsigned char *in, unsigned int n) { return fail_update ? 0 : EVP_Cipher(c,out,in,n); }
#define EVP_CIPHER_CTX_new t_new
#define EVP_CipherInit_ex t_init
#define EVP_Cipher t_update
#include "helper.inc"
int main(void) {
 OSSL_PROVIDER *a=OSSL_PROVIDER_load(NULL,"default"),*b=OSSL_PROVIDER_load(NULL,"legacy");
 unsigned char key[16]={0}, plain[17]={1,2,3,4}, a1[17], b1[17], recovered[17];
 if (!a||!b) return 1;
 if (gsskrb5_cipher_once(EVP_rc4(),key,NULL,1,a1,plain,sizeof plain)) return 2;
 gsskrb5_cipher_ctx c; if(gsskrb5_cipher_init(&c,EVP_rc4(),key,NULL,1)) return 3;
 if(gsskrb5_cipher_update(&c,b1,plain,8) || gsskrb5_cipher_update(&c,b1+8,plain+8,9)) return 4;
 gsskrb5_cipher_free(&c);if(memcmp(a1,b1,sizeof a1)) return 5;
 if(gsskrb5_cipher_once(EVP_rc4(),key,NULL,0,recovered,a1,sizeof a1)||memcmp(recovered,plain,sizeof plain)) return 6;
 fail_new=1;if(gsskrb5_cipher_init(&c,EVP_rc4(),key,NULL,1)!=ENOMEM) return 7;fail_new=0;
 fail_init=1;if(gsskrb5_cipher_init(&c,EVP_rc4(),key,NULL,1)!=EINVAL) return 8;fail_init=0;
 if(gsskrb5_cipher_init(&c,EVP_rc4(),key,NULL,1)) return 9;fail_update=1;
 if(gsskrb5_cipher_update(&c,b1,plain,sizeof plain)!=EINVAL) return 10;gsskrb5_cipher_free(&c);
 OSSL_PROVIDER_unload(b);OSSL_PROVIDER_unload(a);puts("GSS cipher helper tests PASS");return 0;
}
