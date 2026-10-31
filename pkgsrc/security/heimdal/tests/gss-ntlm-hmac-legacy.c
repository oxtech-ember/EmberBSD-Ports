#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <hcrypto/hmac.h>
#include <hcrypto/rc4.h>
typedef uint32_t OM_uint32;
typedef struct {
	size_t length;
	void *value;
} gss_buffer_desc, *gss_buffer_t;
#define GSS_S_COMPLETE 0
#define GSS_S_BAD_MIC 393216
static void
gss_release_buffer(OM_uint32 *minor, gss_buffer_t b)
{
	*minor = 0;
	free(b->value);
	b->value = NULL;
	b->length = 0;
}
#include "functions.inc"
int
legacy_check(void)
{
	(void)v2_sign_message;
	(void)v2_verify_message;
	(void)v2_seal_message;
	(void)v2_unseal_message;
	return 0;
}
