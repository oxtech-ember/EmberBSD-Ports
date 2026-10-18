#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real native Unix-socket protocol contract.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require 'socket'

abort 'Usage: socket-protocol.rb LIBRARY_PREFIX GCC16_CC NEW_WORK' unless ARGV.size == 3
prefix, cc = ARGV.take(2).map { |path| File.realpath(path) }
out = File.expand_path(ARGV[2])
abort 'Output exists.' if File.exist?(out) || File.symlink?(out)
abort 'Socket path is too long.' if (out + '/fd-zero-legacy-memory.sock').bytesize >= 104
FileUtils.mkdir_p(out)
commands = []
run = lambda do |name, argv, env = {}|
  stdout, stderr, status = Open3.capture3(env, *argv, rlimit_core: 0)
  File.write(out + '/' + name + '.stdout', stdout)
  File.write(out + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, env: env, status: status.exitstatus, signal: status.termsig }
  File.write(out + '/commands.json', JSON.pretty_generate(commands) + "\n")
  [stdout, status]
end
version, status = run.call('compiler-version', [cc, '-dumpfullversion'])
abort 'Use GCC16.' unless status.success? && version.strip.match?(/\A16\./)
input = __dir__ + '/socket-client.c'
argv = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
        *Shellwords.split(ENV.fetch('CPPFLAGS', '')), '-I' + prefix + '/include', input,
        *Shellwords.split(ENV.fetch('LDFLAGS', '')), '-L' + prefix + '/lib',
        '-Wl,-rpath,' + prefix + '/lib', '-lspnav', '-o', out + '/client']
_, status = run.call('compile', argv)
abort 'Compile failed.' unless status.success?
memory = ['valgrind', '--tool=memcheck', '--leak-check=full', '--show-leak-kinds=all',
          '--errors-for-leak-kinds=all', '--track-origins=yes', '--error-exitcode=99']
run.call('failed-open-memory', memory + ['--log-file=' + out + '/failed-open-memory.log', out + '/client', 'failed-open'], { 'SPNAV_SOCKET' => out + '/absent' })
run.call('closed-state', [out + '/client', 'closed-state'])
%w[fd-zero fd-zero-legacy events].each do |mode|
  [false, true].each do |memcheck|
    name = mode + (memcheck ? '-memory' : '')
    path = out + '/' + name + '.sock'
    listener = UNIXServer.new(path)
    peer_error = nil
    peer = Thread.new do
      begin
        (mode == 'events' ? 2 : 1).times do
          socket = listener.accept
          begin
            bytes = socket.read(4)
            raise 'Unexpected protocol negotiation.' unless bytes && bytes.unpack1('l') == 0x7faa5501
            socket.write([mode == 'fd-zero-legacy' ? 0x7faa5500 : 0x7faa5501].pack('l'))
            if mode == 'fd-zero-legacy'
              value = socket.read(4)
              raise 'Wrong legacy sensitivity.' unless value && value.unpack1('f') == 1.25
            else
              socket.write([0, 11, -12, 13, -14, 15, -16, 17].pack('l8'))
              socket.write([1, 4, 0, 0, 0, 0, 0, 0].pack('l8'))
            end
          ensure
            socket.close
          end
        end
      rescue StandardError => error
        peer_error = error.message
      end
    end
    argv = ['timeout', '8']
    argv += memory + ['--log-file=' + out + '/' + name + '.log'] if memcheck
    argv += [out + '/client', mode]
    run.call(name, argv, { 'SPNAV_SOCKET' => path })
    unless peer.join(1)
      peer.kill
      peer.join
      peer_error = 'Peer did not complete.'
    end
    listener.close
    File.unlink(path)
    File.write(out + '/' + name + '-peer.json', JSON.pretty_generate({ error: peer_error }) + "\n")
    commands << { name: name + '-peer', status: peer_error ? 1 : 0 }
  end
end
result = {
  scope: 'Actual native Unix-socket negotiation, values, failed opens, fd0 and reconnect; no device or X11 runtime acceptance.',
  input_sha256: Digest::SHA256.file(input).hexdigest,
  library_sha256: Digest::SHA256.file(File.realpath(prefix + '/lib/libspnav.so')).hexdigest,
  commands: commands
}
File.write(out + '/result.json', JSON.pretty_generate(result) + "\n")
abort 'Contract failed; see raw statuses.' unless commands.all? { |command| command[:status] == 0 }
puts 'PASS: actual Unix-socket contract, descriptor-zero lifecycles and strict memory checks.'
