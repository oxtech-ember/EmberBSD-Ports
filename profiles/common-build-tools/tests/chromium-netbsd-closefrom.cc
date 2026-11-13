// Exercise Chromium's actual CloseSuperfluousFds from launch_posix.o.
// Link with --gc-sections; build with -DFIXED and --wrap=closefrom to test
// failures.
#include "base/posix/file_descriptor_shuffle.h"
#include <cerrno>
#include <climits>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>
namespace base {
void CloseSuperfluousFds(const InjectiveMultimap &);
}
#ifdef FIXED
static bool fail_closefrom;
extern "C" int __real_closefrom(int);
extern "C" int __wrap_closefrom(int fd) {
  if (fail_closefrom) {
    errno = EIO;
    return -1;
  }
  return __real_closefrom(fd);
}
#endif
int main(int argc, char **argv) {
  if (argc == 2 && !std::strcmp(argv[1], "child")) {
    if (fcntl(0, F_GETFD) < 0 || fcntl(1, F_GETFD) < 0 ||
        fcntl(2, F_GETFD) < 0 || fcntl(220, F_GETFD) < 0 ||
        fcntl(221, F_GETFD) < 0 || fcntl(171, F_GETFD) != -1 ||
        errno != EBADF || fcntl(300, F_GETFD) != -1 || errno != EBADF)
      return 4;
    if (write(221, "R", 1) != 1)
      return 5;
    char c;
    return read(220, &c, 1) == 1 && c == 'X' ? 0 : 6;
  }
  int s[2], control[2], report[2];
  if (socketpair(AF_UNIX, SOCK_STREAM, 0, s) || pipe(control) || pipe(report))
    return 7;
  if (dup2(s[0], 171) != 171 || dup2(s[0], 300) != 300)
    return 8;
  pid_t p = fork();
  if (p < 0)
    return 9;
  if (!p) {
    if (dup2(control[0], 220) != 220 || dup2(report[1], 221) != 221)
      _exit(10);
    base::InjectiveMultimap keep;
    keep.emplace_back(220, 220, false);
    keep.emplace_back(221, 221, false);
    base::CloseSuperfluousFds(keep);
    execl(argv[0], argv[0], "child", nullptr);
    _exit(11);
  }
  close(s[0]);
  close(171);
  close(300);
  close(control[0]);
  close(report[1]);
  struct pollfd rp = {report[0], POLLIN, 0};
  if (poll(&rp, 1, 5000) != 1)
    return 12;
  char c = 0;
  if (read(report[0], &c, 1) != 1 || c != 'R') {
    int st;
    waitpid(p, &st, 0);
    std::fprintf(stderr, "child status %d\n", st);
    return 13;
  }
  struct pollfd sp = {s[1], POLLIN, 0};
  if (poll(&sp, 1, 5000) != 1 || read(s[1], &c, 1) != 0)
    return 14;
  if (write(control[1], "X", 1) != 1)
    return 15;
  int st;
  if (waitpid(p, &st, 0) < 0 || !WIFEXITED(st) || WEXITSTATUS(st))
    return 16;
#ifdef FIXED
  for (int mode = 0; mode < 3; ++mode) {
    p = fork();
    if (p < 0)
      return 17;
    if (!p) {
      base::InjectiveMultimap map;
      if (mode == 0)
        map.emplace_back(-1, -1, false);
      if (mode == 1)
        map.emplace_back(INT_MAX, INT_MAX, false);
      fail_closefrom = (mode == 2);
      base::CloseSuperfluousFds(map);
      _exit(18);
    }
    if (waitpid(p, &st, 0) < 0 || !WIFEXITED(st) || WEXITSTATUS(st) != 127)
      return 19 + mode;
  }
#endif
  return 0;
}
