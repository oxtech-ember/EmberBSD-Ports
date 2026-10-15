#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile the actual backend with syscall doubles.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: host-contract.rb PATCHED_SOURCE NEW_OUTPUT' unless ARGV.length == 2
source, output = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(output)
FileUtils.mkdir_p(File.join(output, 'sys'))
File.write(File.join(output, 'config.h'), "/* The host fixture needs no configure features. */\n")
prototypes = <<~C
  #include <sys/types.h>
  ssize_t getxattr(const char *, const char *, void *, size_t);
  ssize_t lgetxattr(const char *, const char *, void *, size_t);
  ssize_t fgetxattr(int, const char *, void *, size_t);
  int setxattr(const char *, const char *, const void *, size_t, int);
  int lsetxattr(const char *, const char *, const void *, size_t, int);
  int fsetxattr(int, const char *, const void *, size_t, int);
  ssize_t listxattr(const char *, char *, size_t);
  ssize_t llistxattr(const char *, char *, size_t);
  ssize_t flistxattr(int, char *, size_t);
  int removexattr(const char *, const char *);
  int lremovexattr(const char *, const char *);
  int fremovexattr(int, const char *);
C
File.write(File.join(output, 'sys/xattr.h'), prototypes)
units = %w[get set list remove].map do |op|
  path = File.join(output, "#{op}.c")
  File.write(path, <<~C)
    /* Load host headers before selecting the real EmberBSD backend. */
    #include <sys/types.h>
    #include <errno.h>
    #include <fcntl.h>
    #include <limits.h>
    #include <stdio.h>
    #include <stdlib.h>
    #include <unistd.h>
    #include "sys/xattr.h"
    #define __NetBSD__ 1
    int attr_test_fchdir(int);
    #define fchdir attr_test_fchdir
    #include #{File.join(source, "libmisc/#{op}xattrat_compat.c").dump}
  C
  path
end
# Select only the private flag in the harness. It never reaches a host syscall.
command = Shellwords.split(ENV.fetch('CC', 'cc')) + %w[-std=c11 -D_DARWIN_C_SOURCE -Wall -Wextra -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer]
command += ["-I#{output}", "-I#{source}", "-I#{source}/include", '-DAT_EMPTY_PATH=0x1000']
command += units + [File.join(__dir__, 'host-contract.c'), '-o', File.join(output, 'host-contract')]
File.write(File.join(output, 'command.txt'), command.shelljoin + "\n")
stdout, stderr, status = Open3.capture3(*command)
File.write(File.join(output, 'build.log'), stdout + stderr)
abort stdout + stderr unless status.success?
stdout, stderr, status = Open3.capture3({ 'ASAN_OPTIONS' => 'halt_on_error=1', 'UBSAN_OPTIONS' => 'halt_on_error=1' }, File.join(output, 'host-contract'), chdir: output)
File.write(File.join(output, 'run.log'), stdout + stderr)
abort stdout + stderr unless status.success?
puts stdout
