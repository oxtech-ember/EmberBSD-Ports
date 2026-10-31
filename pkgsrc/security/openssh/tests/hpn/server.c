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
	ServerOptions in, out;
	struct sshbuf *buf = NULL;
	struct include_list includes;
	int active = 1;
	char zero[] = "HPNBufferSize 0";
	initialize_server_options(&in);
	initialize_server_options(&out);
	in.none_enabled = 1;
	in.hpn_disabled = 0;
	in.hpn_buffer_size = 4096 * 1024;
	in.tcp_rcv_buf_poll = 1;
	fill_default_server_options(&in);
	if (in.hpn_buffer_size != 4194304)
		abort();
	if (serialise_server_options(&in, &buf) != 0 ||
	    deserialise_server_options(buf, &out) != 0 ||
	    out.none_enabled != in.none_enabled ||
	    out.hpn_disabled != in.hpn_disabled ||
	    out.hpn_buffer_size != in.hpn_buffer_size ||
	    out.tcp_rcv_buf_poll != in.tcp_rcv_buf_poll)
		abort();
	free_server_options(&in);
	free_server_options(&out);
	sshbuf_free(buf);
	initialize_server_options(&in);
	in.hpn_disabled = 0;
	TAILQ_INIT(&includes);
	if (process_server_config_line(&in, zero, "fixture", 1,
	    &active, NULL, &includes) != 0)
		abort();
	fill_default_server_options(&in);
	if (in.hpn_buffer_size != 1024)
		abort();
	free_server_options(&in);
	return 0;
}
