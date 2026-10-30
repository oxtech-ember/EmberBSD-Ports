#include <openssl/evp.h>
#include <openssl/err.h>
#include <openssl/provider.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
extern const void *hc_EVP_ossl_rc2_cbc(void);
extern const void *hc_EVP_hcrypto_rc2_cbc(void);
extern const void *hc_EVP_ossl_md4(void);
extern const void *hc_EVP_hcrypto_md4(void);
static void *run(void *unused) { (void)unused; for (int i=0;i<1000;i++) if (hc_EVP_ossl_rc2_cbc()!=hc_EVP_hcrypto_rc2_cbc()) return (void *)1; return NULL; }
int main(void) {
 pthread_t t[2]; void *result; unsigned long before;
 ERR_raise(ERR_LIB_USER, 123); before=ERR_peek_last_error();
 if (hc_EVP_ossl_rc2_cbc()!=hc_EVP_hcrypto_rc2_cbc() || ERR_peek_last_error()!=before) return 1;
 if (hc_EVP_ossl_md4()!=hc_EVP_hcrypto_md4() || ERR_peek_last_error()!=before) return 2;
 for (int i=0;i<2;i++) if (pthread_create(&t[i],NULL,run,NULL)) return 3;
 for (int i=0;i<2;i++) if (pthread_join(t[i],&result) || result) return 4;
 if (!EVP_set_default_properties(NULL,"fips=yes") || hc_EVP_ossl_rc2_cbc()!=NULL || hc_EVP_ossl_md4()!=NULL) return 5;
 if (!EVP_set_default_properties(NULL,"provider=nonexistent") || hc_EVP_ossl_rc2_cbc()!=NULL) return 6;
 if (!EVP_set_default_properties(NULL,"") || hc_EVP_ossl_rc2_cbc()!=hc_EVP_hcrypto_rc2_cbc()) return 7;
 if (!OSSL_PROVIDER_load(NULL,"default") || !OSSL_PROVIDER_load(NULL,"legacy")) return 8;
 if (hc_EVP_ossl_rc2_cbc()==NULL || hc_EVP_ossl_rc2_cbc()==hc_EVP_hcrypto_rc2_cbc()) return 9;
 if (hc_EVP_ossl_md4()==NULL || hc_EVP_ossl_md4()==hc_EVP_hcrypto_md4()) return 10;
 puts("fallback/properties/provider/concurrency PASS"); return 0;
}
