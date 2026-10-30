#include <openssl/evp.h>
#include <openssl/err.h>
#include <stdlib.h>
#include <string.h>
EVP_CIPHER *EVP_CIPHER_fetch(OSSL_LIB_CTX *c, const char *n, const char *p) {
 const char *m=getenv("FETCH_CASE"); (void)c;(void)n;(void)p;
 if (m && strcmp(m,"mixed")==0) ERR_raise(ERR_LIB_EVP, ERR_R_MALLOC_FAILURE);
 if (m && strcmp(m,"stale")!=0) ERR_raise(ERR_LIB_EVP, ERR_R_UNSUPPORTED);
 return NULL;
}
