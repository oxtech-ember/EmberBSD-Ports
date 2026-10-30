#include <string.h>
#include "crypto/aria.h"
int main(void) {
    static const unsigned char key[16] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15};
    static const unsigned char plain[16] = {0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff};
    static const unsigned char expected[16] = {0xd7,0x18,0xfb,0xd6,0xab,0x64,0x4c,0x73,0x9d,0xa9,0x5f,0x3b,0xe6,0x45,0x17,0x78};
    unsigned char out[16], recovered[16]; ARIA_KEY enc, dec;
    if (ossl_aria_set_encrypt_key(key, 128, &enc) || ossl_aria_set_decrypt_key(key, 128, &dec)) return 1;
    ossl_aria_encrypt(plain, out, &enc); ossl_aria_encrypt(out, recovered, &dec);
    return memcmp(out, expected, 16) || memcmp(recovered, plain, 16);
}
