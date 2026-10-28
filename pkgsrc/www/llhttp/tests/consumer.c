#include <llhttp.h>
#include <stdio.h>
#include <string.h>

static int
complete(llhttp_t *parser)
{
	int *count = parser->data;
	++*count;
	return 0;
}

int
main(void)
{
	llhttp_t parser;
	llhttp_settings_t settings;
	int count = 0;
	const char *a = "GET /hello HTTP/1.1\r\nHo";
	const char *b = "st: example.com\r\n\r\n";
	const char *bad = "POST / HTTP/1.1\r\nTransfer-Encoding: \r\n\r\n";

	llhttp_settings_init(&settings);
	settings.on_message_complete = complete;
	llhttp_init(&parser, HTTP_REQUEST, &settings);
	parser.data = &count;
	if (llhttp_execute(&parser, a, strlen(a)) != HPE_OK ||
	    llhttp_execute(&parser, b, strlen(b)) != HPE_OK || count != 1)
		return 1;
	llhttp_init(&parser, HTTP_REQUEST, &settings);
	parser.data = &count;
	if (llhttp_execute(&parser, bad, strlen(bad)) != HPE_INVALID_TRANSFER_ENCODING)
		return 2;
	return 0;
}
