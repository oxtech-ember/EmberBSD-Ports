/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Lists serial ports through libserialport
 * to validate the NetBSD backend of the diagnostics kit.
 */
#include <stdio.h>
#include <libserialport.h>

int
main(void)
{
	struct sp_port **ports;
	enum sp_return rc;
	int i, n = 0;

	rc = sp_list_ports(&ports);
	if (rc != SP_OK) {
		fprintf(stderr, "sp-list: sp_list_ports: %d\n", rc);
		return 1;
	}
	for (i = 0; ports[i] != NULL; i++) {
		printf("%s\t%s\t%s\n",
		    sp_get_port_name(ports[i]),
		    sp_get_port_transport(ports[i]) == SP_TRANSPORT_NATIVE ?
		    "native" : "other",
		    sp_get_port_description(ports[i]) != NULL ?
		    sp_get_port_description(ports[i]) : "");
		n++;
	}
	sp_free_port_list(ports);
	fprintf(stderr, "sp-list: %d port(s)\n", n);
	return 0;
}
