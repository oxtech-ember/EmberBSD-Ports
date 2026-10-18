#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual peer accept/wait deadline controls.
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: peer-timeout.rb PEER NEGATIVE_CLIENT NEW_WORK' unless ARGV.size == 3
peer, client = ARGV.take(2).map { |path| File.realpath(path) }
out = File.expand_path(ARGV[2])
abort 'Output exists.' if File.exist?(out) || File.symlink?(out)
FileUtils.mkdir_p(out)
commands = []
%w[accept waitpid].each do |phase|
  socket = out + '/' + phase + '.sock'
  argv = ['timeout', '12', peer, client, 'events', socket]
  started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  stdout, stderr, status = Open3.capture3({ 'SPNAV_NEGATIVE_PHASE' => phase }, *argv, rlimit_core: 0)
  elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started
  File.write(out + '/' + phase + '.stdout', stdout)
  File.write(out + '/' + phase + '.stderr', stderr)
  commands << { phase: phase, argv: argv, status: status.exitstatus, signal: status.termsig, elapsed_seconds: elapsed }
  File.write(out + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort 'Peer did not enforce its own deadline.' unless status.exitstatus == 1 && elapsed >= 7.5 && elapsed < 11.5 && stderr.include?('timeout=1 child_status=9')
  abort 'Peer left its socket.' if File.exist?(socket) || File.symlink?(socket)
end
File.write(out + '/result.json', JSON.pretty_generate({ scope: 'Real silent/nonexiting clients, own periodic deadline, forced child termination/reaping and socket cleanup.', commands: commands }) + "\n")
puts 'PASS: peer bounds accept/wait, reaps an uncooperative child and removes its socket.'
