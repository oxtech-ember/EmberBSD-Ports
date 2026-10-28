// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include <openssl/evp.h>
#include <assert.h>
int main() {
  const char *names[] = {"aes-128-cfb", "aes-256-cfb", "bf-cbc", "bf-cfb", "bf-ecb", "des-ede3", "rc2-40-cbc"};
  for (const char *name : names) assert(EVP_get_cipherbyname(name) != nullptr);
}
