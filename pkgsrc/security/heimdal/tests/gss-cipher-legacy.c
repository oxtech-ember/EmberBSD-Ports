#include <stddef.h>
#include <errno.h>
#include <hcrypto/evp.h>
#include "helper-legacy.inc"
int check(const EVP_CIPHER *cipher, const void *key, void *out) { return gsskrb5_cipher_once(cipher,key,NULL,1,out,out,8); }
