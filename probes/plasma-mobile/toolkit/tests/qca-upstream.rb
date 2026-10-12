#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), bundle unchanged upstream target tests.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: qca-upstream.rb CONFIGURED_QCA_BUILD NEW_WORK' unless ARGV.size == 2
build = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
Dir.mkdir(work)
abort 'Cross hash data directory must be relative to the target test working directory' unless File.read(build + '/CMakeCache.txt').match?(/^QCA_TEST_DATA_DIR:(?:STRING|UNINITIALIZED)=\.$/)
text, status = Open3.capture2e(ENV.fetch('CTEST', 'ctest'), '--test-dir', build, '--show-only=json-v1')
abort text unless status.success?
tests = JSON.parse(text).fetch('tests')
abort 'Unexpected QCA test inventory' unless tests.size == 25
FileUtils.cp_r(build + '/bin', work + '/bin')
# Developer-mode qt.conf would select build-tree providers and invalidate the
# installed-package check. Refuse it rather than modifying its search paths.
abort 'Developer-mode QCA build is not an installed-provider test' if File.exist?(work + '/bin/qt.conf')
commands = tests.map do |test|
  command = test.fetch('command')
  cwd = test.fetch('properties').find { |p| p['name'] == 'WORKING_DIRECTORY' }.fetch('value')
  abort 'Upstream test layout changed' unless command.size == 1 && File.dirname(command[0]) == build + '/bin' && cwd == build + '/bin'
  [test.fetch('name'), File.basename(command[0])]
end
File.write(work + '/tests.tsv', commands.map { |name, exe| "#{name}\t#{exe}\n" }.join)
File.write(work + '/run.sh', <<~'SH')
  #!/bin/sh
  set -eu
  cd "$(dirname "$0")"
  unset LD_LIBRARY_PATH QCA_PLUGIN_PATH QT_PLUGIN_PATH
  export QTEST_FUNCTION_TIMEOUT=120000 LC_ALL=C.UTF-8
  mkdir results
  /usr/pkg/qt6/bin/qcatool-qt6 plugins > results/providers.log
  grep -q 'qca-ossl' results/providers.log
  failed=0
  while read -r name executable; do
      result=0
      (cd bin && "./$executable") > "results/$name.log" 2>&1 || result=$?
      printf '%s\n' "$result" > "results/$name.status"
      if [ "$result" = 0 ]; then
          echo "PASS $name"
      else
          echo "FAIL $name"
          failed=1
      fi
  done < tests.tsv
  exit "$failed"
SH
File.chmod(0755, work + '/run.sh')
files = Dir.glob(work + '/**/*').select { |p| File.file?(p) }.sort
File.write(work + '/SHA256SUMS', files.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(work + '/')}\n" }.join)
puts "Prepared #{commands.size} unchanged upstream invocations; run on target with normally installed QCA/OpenSSL"
