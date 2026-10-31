/* Ordinary cipher roundtrips; see cipher-roundtrip.py for inputs. */
#include <sys/types.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cipher.h"

int
main(void)
{
	const struct sshcipher *c;
	struct sshcipher_ctx *enc = NULL, *dec = NULL;
	const u_char key[16] = {1, 2, 3}, iv[12] = {4, 5, 6};
	const u_char ctr_iv[16] = {4, 5, 6};
	const u_char input[36] = "AAD! ordinary local payload data";
	u_char encrypted[52] = {0}, output[52] = {0};

	c = cipher_by_name("aes128-gcm@openssh.com");
	if (c == NULL ||
	    cipher_init(&enc, c, key, sizeof(key), iv, sizeof(iv), 1) != 0 ||
	    cipher_init(&dec, c, key, sizeof(key), iv, sizeof(iv), 0) != 0)
		abort();
	if (cipher_crypt(enc, 0, encrypted, input, 32, 4, 16) != 0 ||
	    cipher_crypt(dec, 0, output, encrypted, 32, 4, 16) != 0 ||
	    memcmp(input, output, sizeof(input)) != 0)
		abort();
	cipher_free(enc);
	cipher_free(dec);

	c = cipher_by_name("aes128-ctr");
	enc = dec = NULL;
	if (c == NULL ||
	    cipher_init(&enc, c, key, sizeof(key), ctr_iv, sizeof(ctr_iv), 1) != 0 ||
	    cipher_init(&dec, c, key, sizeof(key), ctr_iv, sizeof(ctr_iv), 0) != 0)
		abort();
	if (cipher_crypt(enc, 0, encrypted, input, 32, 0, 0) != 0 ||
	    cipher_crypt(dec, 0, output, encrypted, 32, 0, 0) != 0 ||
	    memcmp(input, output, 32) != 0)
		abort();
	cipher_free(enc);
	cipher_free(dec);
	puts("OpenSSH AES-GCM and AES-CTR ordinary roundtrips PASS");
	return 0;
}
