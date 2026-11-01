#include <sys/types.h>
#include <stdlib.h>
#include <string.h>
#include "sshbuf.h"

int
main(void)
{
	const unsigned char payload[] = { 0x60, 0x03, 0x00, 0x01, 0x02 };
	struct sshbuf *b;
	unsigned char *copy = NULL;
	size_t len = 0;

	if ((b = sshbuf_new()) == NULL ||
	    sshbuf_put_string(b, payload, sizeof(payload)) != 0 ||
	    sshbuf_get_string(b, &copy, &len) != 0 ||
	    len != sizeof(payload) || memcmp(payload, copy, len) != 0)
		abort();
	free(copy);
	sshbuf_free(b);
	return 0;
}
