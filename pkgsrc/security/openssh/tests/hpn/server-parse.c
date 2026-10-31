#include "includes.h"
#include <stdlib.h>
#include "log.h"
#include "misc.h"
#include "servconf.h"
#include "sshbuf.h"
struct sshbuf *cfg;
int
auth2_methods_valid(const char *methods, int need_enable)
{
	(void)methods;
	(void)need_enable;
	return 1;
}
int
main(void)
{
	ServerOptions in;
	struct include_list includes;
	struct connection_info info = {0};
	const char match[] = "Match User alice\nHPNBufferSize 2048\n";
	const char match_zero[] = "Match User alice\nHPNBufferSize 0\n";
	int active = 1;
	char a[] = "HPNBufferSize 4096";
	char b[] = "TcpRcvBufPoll yes";
	char c[] = "HPNDisabled no";

	TAILQ_INIT(&includes);
	initialize_server_options(&in);
	if (process_server_config_line(&in, a, "fixture", 1, &active,
	    NULL, &includes) != 0 ||
	    process_server_config_line(&in, b, "fixture", 2, &active,
	    NULL, &includes) != 0 ||
	    process_server_config_line(&in, c, "fixture", 3, &active,
	    NULL, &includes) != 0 ||
	    in.hpn_buffer_size != 4096 * 1024 || in.tcp_rcv_buf_poll != 1 ||
	    in.hpn_disabled != 0)
		abort();
	if ((cfg = sshbuf_new()) == NULL ||
	    sshbuf_put(cfg, match, sizeof(match) - 1) != 0)
		abort();
	info.user = "alice";
	parse_server_match_config(&in, &includes, &info);
	if (in.hpn_buffer_size != 2048 * 1024)
		abort();
	sshbuf_reset(cfg);
	if (sshbuf_put(cfg, match_zero, sizeof(match_zero) - 1) != 0)
		abort();
	parse_server_match_config(&in, &includes, &info);
	if (in.hpn_buffer_size != 1024)
		abort();
	sshbuf_free(cfg);
	free_server_options(&in);
	return 0;
}
