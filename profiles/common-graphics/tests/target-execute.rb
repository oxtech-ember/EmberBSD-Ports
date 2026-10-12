#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real target stdout/stderr/status and cleanup.
require 'json'
require 'fileutils'
require 'open3'
require 'rbconfig'
abort 'Usage: target-execute.rb CC SYSROOT QUERY_CONFIG NEW_WORK' unless ARGV.size == 4
cc, sysroot, config_path, work = ARGV.map { |p| File.expand_path(p) }
abort 'Work already exists' if File.exist?(work)
config = JSON.parse(File.read(config_path))
FileUtils.mkdir_p(work)
helper = File.expand_path('../recipes/devel/gobject-introspection/files/target-query.rb', __dir__)
File.write(work + '/probe.c', <<'C')
#include <stdio.h>
int main(void) {
    fputs("target stdout\n", stdout);
    fputs("target stderr\n", stderr);
    return RESULT;
}
C
[0, 7].each do |result|
  binary = work + '/probe-' + result.to_s
  out, status = Open3.capture2e(cc, '--sysroot=' + sysroot, '-Wall', '-Wextra', '-Werror',
    '-DRESULT=' + result.to_s, work + '/probe.c', '-o', binary)
  abort out unless status.success?
  before = Dir.glob(config.fetch('cache') + '/gi-query-*')
  out, err, status = Open3.capture3({'EMBERBSD_GI_QUERY_CONFIG' => config_path, 'EMBERBSD_GI_FAILURE_MARKER' => work + '/failure'},
    RbConfig.ruby, helper, '--execute', binary)
  File.write(work + '/result-' + result.to_s + '.log', "exit=#{status.exitstatus}\nstdout=#{out.inspect}\nstderr=#{err.inspect}\n")
  abort "Target result #{result} differs" unless out == "target stdout\n" && err == "target stderr\n" && status.exitstatus == result
  created = Dir.glob(config.fetch('cache') + '/gi-query-*') - before
  # Other builds may concurrently use the executor; select by this binary's receipt.
  receipts = created.select { |d| File.file?(d + '/sources.sha256') && File.read(d + '/sources.sha256').include?(File.realpath(binary)) }
  abort 'Missing or ambiguous provenance' unless receipts.size == 1
  receipt = receipts.first
  abort 'Target cleanup failed' unless File.read(receipt + '/cleanup.log').start_with?("0\n")
  abort 'Temporary bundle survived' if File.exist?(receipt + '/stage') || File.exist?(receipt + '/input.tar.gz')
end
abort 'Unexpected failure marker' if File.exist?(work + '/failure')
puts 'PASS: real target streams, success/failure status, provenance and cleanup'
