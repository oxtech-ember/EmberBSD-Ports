#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Refuse altered identity without touching the guest.
require 'digest'
require 'json'
require 'open3'
require 'rbconfig'
abort 'usage: check-stop-identity.rb WORK' unless ARGV.size == 1
work = File.realpath(ARGV.first)
path = work + '/artifacts/run.json'
original = File.binread(path)
record = JSON.parse(original)
pid = Integer(File.read(work + '/runner.pid'), 10)
process = "/proc/#{pid}"
abort 'the recorded guest must be running' unless File.binread(process + '/cmdline').split("\0") == record.fetch('argv') &&
  File.read(process + '/stat').rpartition(') ').last.split.fetch(19) == record.fetch('process_start_time')
['argv0', 'start-time'].each do |name|
  altered = JSON.parse(original)
  if name == 'argv0'
    altered['argv'][0] = '/usr/bin/true'
    altered['qemu_sha256'] = Digest::SHA256.file('/usr/bin/true').hexdigest
  else
    altered['process_start_time'] = (Integer(record.fetch('process_start_time'), 10) + 1).to_s
  end
  begin
    File.write(path, JSON.pretty_generate(altered) + "\n")
    output, status = Open3.capture2e(RbConfig.ruby, File.join(__dir__, 'stop.rb'), work)
    File.write(work + '/logs/refused-stop-' + name + '.log', "exit=#{status.exitstatus}\n" + output)
    abort "#{name} was not refused before SSH" unless status.exitstatus == 1 && output.include?('recorded PID is not the owned QEMU guest')
  ensure
    File.binwrite(path, original)
  end
  abort 'the correct guest changed during refusal' unless File.binread(process + '/cmdline').split("\0") == record.fetch('argv') &&
    File.read(process + '/stat').rpartition(') ').last.split.fetch(19) == record.fetch('process_start_time')
end
puts 'PASS: altered executable and start-time metadata cannot halt the correct guest'
