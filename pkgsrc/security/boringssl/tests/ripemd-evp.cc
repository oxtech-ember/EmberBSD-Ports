// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include <openssl/digest.h>
#include <openssl/nid.h>
#include <assert.h>
#include <string.h>

int main() {
  const unsigned char expected[20] = {0x8e,0xb2,0x08,0xf7,0xe0,0x5d,0x98,0x7a,0x9b,0x04,
                                      0x4a,0x8e,0x98,0xc6,0xb0,0x87,0xf1,0x5a,0x0b,0xfc};
  const EVP_MD *md = EVP_ripemd160();
  assert(md && EVP_get_digestbyname("ripemd160") == md && EVP_get_digestbynid(NID_ripemd160) == md);
  assert(EVP_MD_size(md) == 20 && EVP_MD_block_size(md) == 64);
  EVP_MD_CTX *ctx = EVP_MD_CTX_new();
  assert(ctx && EVP_DigestInit_ex(ctx, md, nullptr));
  assert(EVP_DigestUpdate(ctx, "a", 1) && EVP_DigestUpdate(ctx, "bc", 2));
  unsigned char result[EVP_MAX_MD_SIZE]; unsigned int size = 0;
  assert(EVP_DigestFinal_ex(ctx, result, &size) && size == 20 && memcmp(result, expected, 20) == 0);
  EVP_MD_CTX_free(ctx);
}
