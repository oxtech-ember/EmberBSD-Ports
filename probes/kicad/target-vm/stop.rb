#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Halt only the recorded private guest.
require 'json'
require 'open3'
require 'digest'
abort 'usage: stop.rb WORK' unless ARGV.size == 1
work = File.realpath(ARGV.first)
pid = Integer(File.read(work + '/runner.pid'), 10)
abort 'invalid runner PID' unless pid > 1
record = JSON.parse(File.read(work + '/artifacts/run.json'))
expected = record.fetch('argv')
start_time = record.fetch('process_start_time')
abort 'QEMU executable changed since launch' unless Digest::SHA256.file(expected.first).hexdigest == record.fetch('qemu_sha256')
process_path = "/proc/#{pid}/cmdline"
abort 'recorded runner is absent; inspect its console log' unless File.file?(process_path)
argv = File.binread(process_path).split("\0")
same_start = lambda { File.read("/proc/#{pid}/stat").rpartition(') ').last.split.fetch(19) == start_time }
abort 'recorded PID is not the owned QEMU guest' unless argv == expected && same_start.call &&
  argv.include?("file=#{work}/query.ffs,if=none,format=raw,id=root")
acknowledgment = 'EMBER_QUERY_HALT_REQUEST_ACCEPTED'
deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 45
stdout, stderr, status = Open3.capture3('/usr/bin/timeout', '--foreground', '--kill-after=5', '35',
  work + '/bin/ssh', 'ember-e14-query',
  "set -eu; printf '%s\\n' #{acknowledgment}; sync; /sbin/halt -p")
File.write(work + '/logs/stop.log', "ssh_exit=#{status.exitstatus}\n" + stdout + stderr)
abort 'owned SSH halt request timed out; QEMU retained' if [124, 137].include?(status.exitstatus)
abort 'guest did not acknowledge the halt request' unless stdout.lines.map(&:chomp).include?(acknowledgment)
loop do
  break unless File.exist?(process_path)
  begin
    current = File.binread(process_path).split("\0")
    break if current.empty? # A terminated child may remain as a zombie until reaped.
    abort 'runner identity changed during halt' unless current == expected && same_start.call
  rescue Errno::ENOENT
    break
  end
  abort 'graceful halt timed out; guest retained for inspection' if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
  sleep 0.25
end
File.write(work + '/artifacts/stopped.json', JSON.pretty_generate({pid: pid, ssh_exit: status.exitstatus,
  halt_request_acknowledged: true, recorded_process_exited: true}) + "\n")
puts 'The guest acknowledged the halt request and the recorded process exited.'
