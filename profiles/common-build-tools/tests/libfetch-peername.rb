#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
require 'tmpdir'
require 'fileutils'
abort 'usage: libfetch-peername.rb EXPORTED_PKGSRC HOST_PREFIX [--sanitize]' unless (2..3).cover?(ARGV.length)
export, prefix = ARGV.first(2).map { |p| File.realpath(p) }
abort 'unknown option' if ARGV[2] && ARGV[2] != '--sanitize'
source = File.read(File.join(export, 'net/libfetch/files/common.c'))
helper = source[/static int\nfetch_ssl_set_peername\(SSL \*ssl, const char \*host\)\n\{.*?\n\}/m]
abort 'export lacks the real peer-name helper' unless helper
abort 'caller does not stop on configuration failure' unless source.include?("if (!fetch_ssl_set_peername(conn->ssl, URL->host)) {\n\t\tfprintf(stderr, \"TLS peer name configuration failed\\n\");\n\t\treturn (-1);")
Dir.mktmpdir('libfetch-peername-') do |work|
  File.write(File.join(work, 'peername.inc'), helper + "\n")
  binary = File.join(work, 'check')
  flags = ARGV[2] ? ['-fsanitize=undefined', '-fno-sanitize-recover=all'] : []
  command = [File.join(prefix, 'bin/clang'), '-std=c11', '-Wall', '-Wextra', '-Werror',
             *flags, '-I' + work, '-I' + File.join(prefix, 'include'),
             File.join(__dir__, 'libfetch-peername.c'), '-L' + File.join(prefix, 'lib'),
             '-Wl,-rpath,' + File.join(prefix, 'lib'), '-lssl', '-lcrypto', '-o', binary]
  abort 'peer-name fixture compilation failed' unless system(*command)
  abort 'peer-name fixture failed' unless system(binary)
end
