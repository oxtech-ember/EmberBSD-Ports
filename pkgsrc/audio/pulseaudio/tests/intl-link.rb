#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the selected gettext declaration and ABI.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

archive, cross_cc, sysroot, out = ARGV
abort 'Usage: intl-link.rb PULSEAUDIO_17_ARCHIVE AMD64_CC SYSROOT NEW_OUTPUT' unless
  ARGV.length == 4 && ARGV.all? { |p| p.start_with?('/') }
abort 'Output already exists' if File.exist?(out)
recipe = File.expand_path('..', __dir__)
media = File.expand_path('../../../..', __dir__)
pin = File.readlines(media + '/sources.tsv').map { |l| l.chomp.split("\t") }
          .find { |row| row[1] == 'pulseaudio-17.0.tar.xz' }
abort 'Archive digest mismatch' unless pin && Digest::SHA256.file(archive).hexdigest == pin[2]
meson = ENV.fetch('MESON', 'meson')
ninja = ENV.fetch('NINJA', 'ninja')
native_cc = ENV.fetch('CC', 'cc')
FileUtils.mkdir_p(out)
commands = []
run = lambda do |name, args, env = {}|
  stdout, stderr, status = Open3.capture3(env, *args)
  File.write(out + '/' + name + '.log', stdout + stderr)
  commands << { name: name, command: args, environment: env, status: status.exitstatus }
  File.write(out + '/commands.json', JSON.pretty_generate(commands) + "\n")
  [status.success?, stdout + stderr]
end
upstream, error, status = Open3.capture3('tar', '-xOf', archive, 'pulseaudio-17.0/meson.build')
abort error unless status.success?
File.write(out + '/upstream-meson.build', upstream)

extract = lambda do |source|
  lines = source.lines
  first = lines.index { |line| line.start_with?("if cc.has_function('dgettext'") }
  abort 'Unique dgettext block missing' unless first && lines.count { |l| l.start_with?("if cc.has_function('dgettext'") } == 1
  depth = 0
  block = []
  lines[first..].each do |line|
    depth += 1 if line.start_with?('if ', '  if ')
    block << line
    depth -= 1 if line.strip == 'endif'
    break if depth.zero?
  end
  abort 'Unterminated dgettext block' unless depth.zero?
  block.join
end

patches = { 'after' => recipe + '/patches/patch-meson.build' }
patches['before'] = ENV.fetch('BASELINE_PATCH') if ENV.key?('BASELINE_PATCH')
blocks = {}
patches.each do |name, patch|
  directory = out + '/' + name + '-source'
  FileUtils.mkdir_p(directory)
  File.write(directory + '/meson.build', upstream)
  stdout, stderr, status = Open3.capture3('patch', '--batch', '--forward', '--fuzz=0', '-p0', '-d', directory,
                                         stdin_data: File.binread(patch))
  File.write(out + '/' + name + '-patch.log', stdout + stderr)
  abort "#{name} patch failed" unless status.success?
  blocks[name] = extract.call(File.read(directory + '/meson.build'))
end

consumer = <<~C
  #include <libintl.h>
  #include <stdio.h>
  #include <string.h>
  int main(void)
  {
      const char *text = dgettext("emberbsd-intl-probe", "gettext contract");
      if (text == NULL || strcmp(text, "gettext contract") != 0)
          return 1;
      puts(text);
      return 0;
  }
C
File.write(out + '/consumer.c', consumer)
gcc_runtime = sysroot + '/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/'
cross_args = ['--sysroot=' + sysroot, '-B' + gcc_runtime, '-D_NETBSD_SOURCE']
cross = out + '/cross.ini'
abort 'Unsupported quote in compiler path or sysroot' if ([cross_cc] + cross_args).any? { |s| s.match?(/['\r\n]/) }
meson_compiler = '[' + ([cross_cc] + cross_args).map { |s| "'#{s}'" }.join(', ') + ']'
File.write(cross, <<~MESON)
  [binaries]
  c = #{meson_compiler}
  [host_machine]
  system = 'netbsd'
  cpu_family = 'x86_64'
  cpu = 'x86_64'
  endian = 'little'
  [properties]
  needs_exe_wrapper = true
MESON

# These links use each real selected header. No target executable is run here.
native_link, = run.call('native-without-intl', [native_cc, out + '/consumer.c', '-o', out + '/native-consumer'])
target_link, = run.call('amd64-without-intl', [cross_cc, *cross_args, out + '/consumer.c', '-o', out + '/amd64-without-intl'])
abort 'Expected native libc and target external-libintl controls' unless native_link && !target_link
native_run, = run.call('native-consumer', [out + '/native-consumer'])
abort 'Native gettext call failed' unless native_run

blocks.each do |revision, block|
  %w[native amd64].each do |mode|
    name = revision + '-' + mode
    directory = out + '/' + name
    FileUtils.mkdir_p(directory)
    File.write(directory + '/consumer.c', consumer)
    File.write(directory + '/meson.build', <<~MESON)
      project('pulse-intl-contract', 'c')
      cc = meson.get_compiler('c')
      #{block}
      executable('consumer', 'consumer.c', dependencies : libintl_dep)
    MESON
    args = [meson, 'setup', directory + '/build', directory, '--wrap-mode=nodownload']
    args << '--cross-file=' + cross if mode == 'amd64'
    success, output = run.call(name + '-configure', args, { 'CC' => native_cc })
    if revision == 'before' && mode == 'native'
      abort 'Previous native failure changed' if success || !output.match?(/library ['"]intl['"] not found/)
      next
    end
    abort "#{name} configuration failed" unless success
    success, = run.call(name + '-build', [ninja, '-C', directory + '/build'])
    abort "#{name} link failed" unless success
    if mode == 'native'
      success, = run.call(name + '-run', [directory + '/build/consumer'])
      abort 'Native configured consumer failed' unless success
    else
      readelf = cross_cc.sub(/gcc\z/, 'readelf')
      success, dynamic = run.call(name + '-elf', [readelf, '-d', directory + '/build/consumer'])
      abort 'Target libintl ABI dependency missing' unless success && dynamic.match?(/NEEDED.*\[libintl\.so\.1\]/)
    end
  end
end
hashes = patches.transform_values { |path| Digest::SHA256.file(path).hexdigest }
hashes['archive'] = Digest::SHA256.file(archive).hexdigest
hashes['target_header'] = Digest::SHA256.file(sysroot + '/usr/include/libintl.h').hexdigest
File.write(out + '/inputs.json', JSON.pretty_generate(hashes) + "\n")
puts 'PASS: native libc gettext and cross-linked AMD64 external libintl; no target program executed'
puts 'PASS: previous recipe native -lintl failure reproduced' if blocks.key?('before')
