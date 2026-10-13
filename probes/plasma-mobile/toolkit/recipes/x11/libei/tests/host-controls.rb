#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Test bundle failure paths without target execution.
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'

abort 'Usage: host-controls.rb NEW_RESULTS' unless ARGV.size == 1
work = File.expand_path(ARGV.fetch(0))
Dir.mkdir(work)
prepare = File.join(__dir__, 'prepare.rb')
runner = File.join(__dir__, 'run.sh')
results = []

def rejected(results, work, name, command, expected)
  out, err, status = Open3.capture3(*command)
  File.write(File.join(work, name + '.log'), out + err)
  raise "Unexpected failure: #{name}: #{err}" unless !status.success? && err.include?(expected)
  results << {case: name, status: status.exitstatus}
end

invoke = lambda do |name, expected|
  output = File.join(work, name)
  rejected(results, work, name,
           [{'READELF' => '/usr/bin/false'}, RbConfig.ruby, prepare,
            File.join(work, 'missing-source'), File.join(work, 'missing-sysroot'), output], expected)
  output
end

marker = File.join(work, 'existing-temporary.tar.gz.preparing')
File.write(marker, 'preserve this existing archive')
invoke.call('existing-temporary', 'File exists')
raise 'Existing temporary archive changed' unless File.read(marker) == 'preserve this existing archive'
raise 'Failed staging remains' if File.exist?(File.join(work, 'existing-temporary.preparing'))

%w[.tar.gz .tar.gz.sha256].each_with_index do |suffix, index|
  name = "dangling-final-#{index}"
  link = File.join(work, name + suffix)
  File.symlink('missing-original', link)
  invoke.call(name, 'Output exists')
  raise 'Existing final link changed' unless File.symlink?(link) && File.readlink(link) == 'missing-original'
end

staging = File.join(work, 'existing-staging.preparing')
Dir.mkdir(staging)
File.write(File.join(staging, 'marker'), 'preserve staging')
invoke.call('existing-staging', 'File exists')
raise 'Existing staging changed' unless File.read(File.join(staging, 'marker')) == 'preserve staging'

output = invoke.call('incomplete-source', 'No such file or directory')
['', '.preparing', '.tar.gz', '.tar.gz.preparing', '.tar.gz.sha256'].each do |suffix|
  raise "Failed preparation left #{suffix}" if File.exist?(output + suffix) || File.symlink?(output + suffix)
end

# The real runner executes its guard. Only the external UID response is a fixture.
# This does not claim an actual privileged execution or execute any target binary.
root_results = File.join(work, 'root-results')
rejected(results, work, 'root-guard',
         ['/bin/sh', '-c', 'id() { printf "0\\n"; }; result=$1; runner=$2; set -- "$result"; . "$runner"',
          'host-control', root_results, runner], 'Run the tests as an ordinary user, not root')
raise 'Root rejection created results' if File.exist?(root_results)
File.write(File.join(work, 'results.json'), JSON.pretty_generate(results))
puts "PASS: #{results.size} host failure controls; UID 0 is a fixture, not a privileged run"
