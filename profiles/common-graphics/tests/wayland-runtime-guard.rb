#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Labelled shell guard fixtures, not pkgDB tests.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: wayland-runtime-guard.rb NEW_WORK' unless ARGV.size == 1
work = File.expand_path(ARGV.first)
abort 'New absolute directory required.' unless ARGV.first.start_with?('/') && !File.exist?(work) && !File.symlink?(work)
Dir.mkdir(work)
runner = File.expand_path('../cross/run-wayland-tests.sh', __dir__)
source = File.read(runner)
guard = source[/^check_runtime_sdk_absent\(\) \{\n.*?^\}\n/m]
abort 'Actual runner guard missing.' unless guard
File.write(work + '/guard.sh', "#!/bin/sh\nset -eu\n" + guard + 'check_runtime_sdk_absent "$@"' + "\n")
tool = work + '/query-fixture'
File.write(tool, <<~SH)
  #!/bin/sh
  # This fixture models pkg_info outcomes; it is not a package provider.
  case "$GUARD_FIXTURE" in
    absent) exit 1;;
    present) echo wayland-devel-1.26.0nb2; exit 0;;
    db-error) echo 'fixture database read error' >&2; exit 1;;
    stdout-error) echo 'fixture unexpected output'; exit 1;;
    tool-error) exit 2;;
    *) exit 99;;
  esac
SH
File.chmod(0755, tool)
records = []
# Retain the prior expression to show the four false absence classifications.
File.write(work + '/prior.sh', <<~SH)
  #!/bin/sh
  [ ! -e "$1" ] && ! "$2" -e 'wayland-devel-[0-9]*' >/dev/null 2>&1
SH
%w[absent present db-error stdout-error tool-error scanner-file scanner-dangling].each do |name|
  directory = work + '/' + name
  Dir.mkdir(directory)
  scanner = directory + '/scanner'
  File.write(scanner, 'fixture') if name == 'scanner-file'
  File.symlink('missing-target-fixture', scanner) if name == 'scanner-dangling'
  outcome = name.start_with?('scanner-') ? 'absent' : name
  out, err, status = Open3.capture3({'GUARD_FIXTURE' => outcome}, '/bin/sh', work + '/guard.sh', scanner, tool, directory)
  File.write(directory + '/stdout', out); File.write(directory + '/stderr', err)
  abort 'Incorrect actual shell guard result: ' + name unless status.success? == (name == 'absent')
  _old_out, old_err, prior = Open3.capture3({'GUARD_FIXTURE' => outcome}, '/bin/sh', work + '/prior.sh', scanner, tool)
  File.write(directory + '/prior.stderr', old_err)
  expected_old = !%w[present scanner-file].include?(name)
  abort 'Prior expression did not reproduce: ' + name unless prior.success? == expected_old
  records << {case: name, status: status.exitstatus, prior_status: prior.exitstatus}
end
File.write(work + '/result.json', JSON.pretty_generate({scope: 'Extracted production shell guard with labelled query/filesystem fixtures; no package database or target execution.', runner_sha256: Digest::SHA256.file(runner).hexdigest, cases: records}) + "\n")
puts 'PASS: actual runtime guard accepts absence only; installed SDK, scanner, dangling link and query failures reject.'
