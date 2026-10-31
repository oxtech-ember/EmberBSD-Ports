#include <stddef.h>
#include <hcrypto/hmac.h>
#include "kx509-macros.inc"

int
legacy_hmac(const void *key, size_t keylen, const void *data, size_t datalen,
    void *out)
{
	HMAC_CTX storage, *ctx = &storage;
	unsigned int size;

	HMAC_CTX_init(ctx);
	if (!KX509_HMAC_OK(HMAC_Init_ex(ctx, key, keylen, EVP_sha1(), NULL)) ||
	    !KX509_HMAC_OK(HMAC_Update(ctx, data, datalen)) ||
	    !KX509_HMAC_OK(HMAC_Final(ctx, out, &size)))
		return -1;
	KX509_HMAC_FREE(ctx);
	return 0;
}
