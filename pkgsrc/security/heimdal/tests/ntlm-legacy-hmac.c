#include <stddef.h>
#include <string.h>
#include <hcrypto/hmac.h>
#include "ntlm-macros.inc"
int check(const void *key, size_t len, const void *data, size_t n, void *out) {
    NTLM_HMAC_DECLARE(c); unsigned int size;
    if (!NTLM_HMAC_INIT(c)) return -1;
    if (!NTLM_HMAC_OK(HMAC_Init_ex(c,key,len,NULL,NULL)) ||
        !NTLM_HMAC_OK(HMAC_Update(c,data,n)) ||
        !NTLM_HMAC_OK(HMAC_Final(c,out,&size))) return -1;
    NTLM_HMAC_FREE(c); return 0;
}
int check_cipher(void) {
    NTLM_CIPHER_DECLARE(c);
    if (!NTLM_CIPHER_INIT(c)) return -1;
    NTLM_CIPHER_FREE(c); return 0;
}
