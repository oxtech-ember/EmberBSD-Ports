#include <ada_c.h>
#include <string.h>
int main(void) {
  const char *src = "https://b\xC3\xBC" "cher.de/path";
  ada_url url = ada_parse(src, strlen(src));
  if (!url || !ada_is_valid(url)) return 1;
  ada_string host = ada_get_hostname(url);
  if (host.length != strlen("xn--bcher-kva.de") ||
      memcmp(host.data, "xn--bcher-kva.de", host.length)) return 2;
  ada_free(url);
  src = "https://[broken";
  url = ada_parse(src, strlen(src));
  if (!url || ada_is_valid(url)) return 3;
  ada_free(url);
  return 0;
}
