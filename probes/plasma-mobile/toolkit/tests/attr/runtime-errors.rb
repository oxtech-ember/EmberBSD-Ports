#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real consumer's first-call errors.
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: runtime-errors.rb CONSUMER_SOURCE STAGED_PREFIX NEW_OUTPUT' unless ARGV.length == 3
source, prefix, output = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(output)
FileUtils.mkdir_p(File.join(output, 'sys'))
File.write(File.join(output, 'sys/xattr.h'), <<~C)
  #ifndef ATTR_TEST_XATTR_H
  #define ATTR_TEST_XATTR_H
  #define XATTR_CREATE 1
  #define XATTR_REPLACE 2
  #endif
C
unit = File.join(output, 'errors.c')
File.write(unit, <<~C)
  #include <sys/types.h>
  #include <sys/xattr.h>
  #include <attr/attributes.h>
  #include <attr/libattr.h>
  #include <assert.h>
  #include <errno.h>
  #include <fcntl.h>
  #include <stdio.h>
  #include <stdlib.h>
  #include <string.h>
  #include <unistd.h>
  /* Match the distinct errno values in the target sys/errno.h. */
  #undef ENOTSUP
  #undef EOPNOTSUPP
  #define ENOTSUP 86
  #define EOPNOTSUPP 45
  static int unexpected(void) { abort(); }
  static int first_xattr(int fd, const char *name, const void *value,
      size_t size, int flags)
  {
      assert(fcntl(fd, F_GETFD) != -1);
      assert(strcmp(name, "user.ember-abi") == 0);
      assert(size == 5 && memcmp(value, "first", 5) == 0);
      assert(flags == XATTR_CREATE);
      errno = atoi(getenv("ATTR_TEST_ERRNO"));
      return -1;
  }
  #define fsetxattr first_xattr
  #define setxattr(...) unexpected()
  #define getxattr(...) unexpected()
  #define fgetxattr(...) unexpected()
  #define fremovexattr(...) unexpected()
  #define removexattr(...) unexpected()
  #define attr_copy_file(...) unexpected()
  #define attr_copy_fd(...) unexpected()
  #include #{source.dump}
C
command = Shellwords.split(ENV.fetch('CC', 'cc')) + %w[-std=c11 -Wall -Wextra -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer]
command += ["-I#{output}", "-I#{prefix}/include", unit, '-o', File.join(output, 'errors')]
out, err, status = Open3.capture3(*command)
File.write(File.join(output, 'build.log'), out + err)
abort out + err unless status.success?
results = {}
{ 'ENOTSUP' => [86, 77], 'EOPNOTSUPP' => [45, 77], 'ENOSYS' => [78, 77], 'EACCES' => [13, 1] }.each do |name, (number, expected)|
  dir = File.join(output, name)
  Dir.mkdir(dir)
  env = { 'ATTR_TEST_ERRNO' => number.to_s, 'ASAN_OPTIONS' => 'halt_on_error=1', 'UBSAN_OPTIONS' => 'halt_on_error=1' }
  out, err, status = Open3.capture3(env, File.join(output, 'errors'), File.join(dir, 'source'), File.join(dir, 'destination'))
  results[name] = { exit: status.exitstatus, stdout: out, stderr: err }
  File.write(File.join(output, 'results.json'), JSON.pretty_generate(results) + "\n")
  abort "Unexpected #{name} result: #{results[name].inspect}" unless status.exitstatus == expected && out.empty? && (expected == 77 ? err.include?('UNSUPPORTED: filesystem xattrs:') : err.include?('fsetxattr create:'))
end
File.write(File.join(output, 'command.txt'), command.shelljoin + "\n")
puts 'PASS: distinct unsupported errno values return 77; permission errors remain failures'
