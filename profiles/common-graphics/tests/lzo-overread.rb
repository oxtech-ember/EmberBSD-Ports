#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), regression for the upstream LZO1F fix.
require 'digest'
require 'fileutils'
require 'open3'
require 'timeout'

abort 'usage: lzo-overread.rb LZO_2_10_ARCHIVE NEW_WORK' unless ARGV.length == 2
archive = File.realpath(ARGV[0])
abort 'wrong upstream archive' unless Digest::SHA256.file(archive).hexdigest ==
  'c0f892943208266f9b6543b3ae308fab6284c5c90e627931446fb49b4221a072'
work = File.expand_path(ARGV[1])
abort 'NEW_WORK must be new and absolute' unless ARGV[1].start_with?('/') && !File.exist?(work)
cc = File.realpath(ENV.fetch('HOST_CC', '/usr/bin/clang'))
patches = File.expand_path('../../../pkgsrc/archivers/lzo/patches', __dir__)
FileUtils.mkdir_p(work)
File.write("#{work}/case.c", <<~'C')
  #include <lzo/lzo1f.h>
  #include <stdio.h>
  #include <stdlib.h>
  int main(void) {
      unsigned char *input = malloc(1), output[64];
      lzo_uint length = sizeof(output);
      int error;
      if (input == NULL) return 2;
      input[0] = 32;
      error = lzo1f_decompress_safe(input, 1, output, &length, NULL);
      free(input);
      printf("LZO1F truncated match: error=%d output=%lu\n", error, (unsigned long)length);
      return error == LZO_E_INPUT_OVERRUN && length == 0 ? 0 : 1;
  }
C
%w[original patched].each do |variant|
  dir = "#{work}/#{variant}"
  FileUtils.mkdir_p(dir)
  out, status = Open3.capture2e('tar', '-xf', archive, '-C', dir,
    'lzo-2.10/include', 'lzo-2.10/src', 'lzo-2.10/COPYING')
  abort "extract failed: #{out}" unless status.success?
  root = "#{dir}/lzo-2.10"
  selected = ['patch-aa']
  selected << 'patch-src_lzo1f__d.ch' if variant == 'patched'
  selected.each do |name|
    out, status = Open3.capture2e('patch', '--batch', '-F0', '-p0', '-i', "#{patches}/#{name}", chdir: root)
    File.write("#{dir}/#{name}.log", out)
    abort "patch failed: #{name}" unless status.success? && !out.match?(/offset|fuzz/i)
  end
  command = [cc, '-O1', '-g', '-fsanitize=address', "-I#{root}/include", "-I#{root}",
    "#{root}/src/lzo1f_d2.c", "#{work}/case.c", '-o', "#{dir}/case"]
  out, status = Open3.capture2e(*command)
  File.write("#{dir}/compile.log", out)
  abort "compile failed: #{variant}" unless status.success?
  pid = Process.spawn("#{dir}/case", out: "#{dir}/run.log", err: [:child, :out])
  begin
    _, result = Timeout.timeout(15) { Process.wait2(pid) }
  rescue Timeout::Error
    Process.kill('KILL', pid)
    Process.wait(pid)
    abort "case timed out: #{variant}"
  end
  log = File.read("#{dir}/run.log")
  if variant == 'original'
    abort 'upstream overread did not reproduce' if result.success? || !log.include?('AddressSanitizer: heap-buffer-overflow')
    puts 'RED: upstream LZO1F safe decoder reads beyond the one-byte input'
  else
    abort "patched decoder failed: #{log}" unless result.success? && !log.include?('AddressSanitizer')
    puts 'GREEN: the exact upstream fix returns LZO_E_INPUT_OVERRUN with no output'
  end
end
paths = [__FILE__, archive, cc, "#{patches}/patch-aa", "#{patches}/patch-src_lzo1f__d.ch"]
File.write("#{work}/inputs.sha256", paths.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: native sanitizer regression; target runtime acceptance is separate'
