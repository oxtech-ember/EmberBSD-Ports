#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real target identity, argv and transport.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'
abort 'usage: check.rb WORK TARGET_QUERY_RB READELF' unless ARGV.size == 3
work, launcher, readelf = ARGV.map { |p| File.realpath(p) }
input = JSON.parse(File.read(work + '/artifacts/input.json'))
ssh = [work + '/bin/ssh', 'ember-e14-query']
receipts = []
run = lambda do |name, expected, *command, **options|
  stdout, stderr, status = Open3.capture3(*command, **options)
  File.write(work + '/logs/check-' + name + '.log', "exit=#{status.exitstatus}\n" + stdout + stderr)
  receipts << {name: name, exit: status.exitstatus, expected: expected}
  abort "#{name}: expected #{expected}, got #{status.exitstatus}" unless status.exitstatus == expected
  stdout
end
identity = run.call('identity', 0, *ssh, <<~SH)
  set -eu
  test "$(uname -s)" = NetBSD
  test "$(uname -p)" = aarch64
  test "$HOME" = /root
  test "$USER" = root
  test "$(id -u)" = 0
  test "$(getent group tty)" = tty:*:4:root
  test -c /dev/ptmx
  test -d /usr/lib/i18n
  test -d /usr/share/i18n
  test -d /usr/share/locale
  test ! -e /usr/bin/gcc
  test ! -e /usr/bin/cc
  test ! -e /usr/pkg/bin/gcc
  uname -a
  id
  locale -a
  /sbin/mount
  df -ki /
SH
abort 'ptyfs not mounted' unless identity.include?('on /dev/pts type ptyfs')
libc = input.fetch('sources_sha256').keys.find { |path| path.match?(%r{/lib/libc\.so\.\d+\.\d+\z}) }
abort 'base libc inventory missing' unless libc
(%w[/bin/sh /usr/bin/uname /usr/bin/sha256 /usr/sbin/sshd /sbin/chown /usr/sbin/chown /usr/bin/chgrp] + [libc.delete_prefix(input.fetch('base'))]).each do |relative|
  path = input.fetch('base') + relative
  expected = input.fetch('sources_sha256').fetch(path)
  abort "unverified base source: #{path}" unless expected.is_a?(String) && Digest::SHA256.file(path).hexdigest == expected
  actual = run.call('hash-' + File.basename(relative), 0, *ssh, 'sha256 -q ' + relative.shellescape).strip
  abort "guest base differs: #{relative}" unless actual == expected
end
run.call('package-directory-ownership', 0, *ssh, <<~SH)
  set -eu
  probe=$(mktemp /tmp/e14-ownership.XXXXXXXX)
  trap 'rm -f "$probe"' EXIT HUP INT TERM
  /usr/sbin/chown root "$probe"
  /usr/bin/chgrp wheel "$probe"
SH
pty = run.call('pty', 0, work + '/bin/ssh', '-tt', 'ember-e14-query', 'test -t 0 && tty && stty -a')
abort 'real target PTY missing' unless pty.include?('/dev/pts/')
run.call('status37', 37, *ssh, 'exit 37')
failure = run.call('set-e-failure', 1, *ssh, "sh -c 'set -e; false; echo UNREACHED'")
abort 'shell failure was hidden' if failure.include?('UNREACHED')
wrong_hosts = work + '/keys/wrong_known_hosts'
type, data = File.read(work + '/keys/client.pub').split.first(2)
File.write(wrong_hosts, "ember-e14-query #{type} #{data}\n", mode: 'w', perm: 0600)
run.call('wrong-host', 255, work + '/bin/ssh', '-o', 'UserKnownHostsFile=' + wrong_hosts, 'ember-e14-query', 'true')
shell = work + '/probes/sh'
FileUtils.cp(input.fetch('base') + '/bin/sh', shell)
File.chmod(0755, shell)
config = work + '/query-check.json'
File.write(config, JSON.pretty_generate({target: 'aarch64', build_root: work + '/probes', sysroot: input.fetch('base'),
  cache: work + '/cache', readelf: readelf, ssh: 'ember-e14-query', library_dirs: []}) + "\n")
env = {'EMBERBSD_GI_QUERY_CONFIG'=>config, 'PATH'=>work + '/bin:' + ENV.fetch('PATH'),
       'EMBERBSD_GI_FAILURE_MARKER'=>work + '/probes/transport-failed'}
abort 'an earlier transport failure needs review' if File.exist?(env.fetch('EMBERBSD_GI_FAILURE_MARKER'))
run.call('query-config', 0, env, RbConfig.ruby, launcher, '--check', work + '/probes', input.fetch('base'), readelf)
values = ['two words', "single'quote", 'double"quote', '', '$(touch /tmp/ember-query-injection)', '; exit 99']
body = "test \"$#\" = #{values.size} || exit 41\n"
values.each { |value| body += "test \"$1\" = #{value.shellescape} || exit 42\nshift\n" }
body += "printf '%s\\n' ARGV_OK\nexit 37\n"
output = run.call('query-literal-argv', 37, env, RbConfig.ruby, launcher, '--execute', shell, '-c', body, 'query', *values)
abort 'literal argv oracle failed' unless output == "ARGV_OK\n"
run.call('query-success', 0, env, RbConfig.ruby, launcher, '--execute', shell, '-c', 'printf TARGET_OK')
run.call('query-negative', 1, env, RbConfig.ruby, launcher, '--execute', shell, '-c', 'false')
abort 'legitimate target status became a transport failure' if File.exist?(env.fetch('EMBERBSD_GI_FAILURE_MARKER'))
bad = run.call('dump-args-still-rejected', 1, env.reject { |key, _| key == 'EMBERBSD_GI_FAILURE_MARKER' }, RbConfig.ruby, launcher, shell, 'literal')
abort 'dump mode unexpectedly accepted literal args' unless File.read(work + '/logs/check-dump-args-still-rejected.log').include?('only an optional introspect-dump')
run.call('cleanup', 0, *ssh, <<~SH)
  set -eu
  test ! -e /tmp/ember-query-injection
  for path in /tmp/ember-gir.*; do
    test ! -e "$path"
  done
SH
capacity = run.call('capacity', 0, *ssh, 'df -ki /')
data = capacity.lines.find { |line| line.start_with?('/dev/ld4a') }.to_s.split
abort 'insufficient free target inodes' unless data.size >= 8 && Integer(data[6]) >= 16000
File.write(work + '/artifacts/acceptance.json', JSON.pretty_generate({checks: receipts, free_kib: Integer(data[3]),
  free_inodes: Integer(data[6]), launcher_sha256: Digest::SHA256.file(launcher).hexdigest,
  allocated_disk_bytes: File.stat(work + '/query.ffs').blocks * 512}) + "\n")
puts 'PASS: real EmberBSD SSH, PTY, literal query argv, status, provider hashes and cleanup'
