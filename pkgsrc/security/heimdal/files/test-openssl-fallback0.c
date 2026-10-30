#include <openssl/err.h>
extern const void *hc_EVP_ossl_rc2_cbc(void);
extern const void *hc_EVP_ossl_md4(void);
int main(void) { return hc_EVP_ossl_rc2_cbc()!=0 || hc_EVP_ossl_md4()!=0; }
