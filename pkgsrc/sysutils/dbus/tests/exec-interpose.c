#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int probe_execl(const char *path, const char *arg, ...)
{
  const char *out = getenv("EMBER_DBUS_EXEC_TRACE");
  if (out) { int fd = open(out, O_WRONLY | O_CREAT | O_TRUNC, 0600); if (fd >= 0) { (void)write(fd,path,strlen(path)); close(fd); } }
  (void)arg;
  _exit(77);
}
__attribute__((used,section("__DATA,__interpose")))
static const struct { const void *replacement; const void *replacee; } entry = { (const void *)&probe_execl, (const void *)&execl };
