#include "includes.h"
#include <limits.h>
#include <pwd.h>
#include <stdlib.h>
#include "ssh.h"
#include "sshkey.h"
#include "misc.h"
#include "log.h"
#include "readconf.h"
void
pkcs11_key_free(struct sshkey *k)
{
	(void)k;
	abort();
}

int
main(void)
{
	Options opts;
	struct passwd pw = {0};
	int active = 1;
	char a[] = "HPNBufferSize 4096";
	char b[] = "TCPRcvBufPoll yes";
	char c[] = "HPNDisabled no";
	char zero[] = "HPNBufferSize 0";
	char large[] = "TCPRcvBuf 2147483647";

	initialize_options(&opts);
	if (process_config_line(&opts, &pw, "host", "host", NULL, a,
	    "test", 1, &active, 0) != 0 ||
	    process_config_line(&opts, &pw, "host", "host", NULL, b,
	    "test", 2, &active, 0) != 0 ||
	    process_config_line(&opts, &pw, "host", "host", NULL, c,
	    "test", 3, &active, 0) != 0 ||
	    opts.hpn_buffer_size != 4096 || opts.tcp_rcv_buf_poll != 1 ||
	    opts.hpn_disabled != 0)
		abort();
	if (fill_default_options(&opts) != 0 || opts.hpn_buffer_size != 4194304)
		abort();
	free_options(&opts);
	initialize_options(&opts);
	active = 1;
	if (process_config_line(&opts, &pw, "host", "host", NULL, zero,
	    "test", 4, &active, 0) != 0 ||
	    process_config_line(&opts, &pw, "host", "host", NULL, large,
	    "test", 5, &active, 0) != 0 || fill_default_options(&opts) != 0 ||
	    opts.hpn_buffer_size != 1024 || opts.tcp_rcv_buf != INT_MAX)
		abort();
	free_options(&opts);
	return 0;
}
