#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted replay of the upstream native-compiler check.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: cross-ncurses-native.rb PKGSRC MAKECONF NCURSES_WORK OLD_PROFILE NEW_PROFILE NEW_WORK' unless ARGV.size == 6
tree, conf, original, old_profile, new_profile = ARGV.first(5).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute output directory' unless work == ARGV.last && !File.exist?(work) && !File.symlink?(work)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
configure = original + '/ncurses-6.6/configure'
log = File.read(original + '/ncurses-6.6/config.log')
text = File.read(configure)
start = text.index("\tcf_save_crossed=$cross_compiling\n\tcf_save_ac_link=$ac_link\n")
finish = start && text.index("\nelse\n\t: ${BUILD_CC:='${CC}'}", start)
abort 'Upstream native-compiler check changed' unless start && finish
probe = text[start...finish]
abort 'Missing upstream compile/run check' unless probe.include?("ac_link='$BUILD_CC -o") && probe.include?('Cross-build requires two compilers.') && probe.include?('"./conftest$ac_exeext"')
defines = log[/\n(#define PACKAGE "ncurses"\n.*)\n\nconfigure: exit [0-9]+\n?\z/m, 1]
abort 'Missing actual configure header' unless defines && defines.include?('#define NCURSES_VERSION "6.6"')
File.write(work + '/upstream-config.log', log)
config = File.read(conf)
include_pattern = /^\.include "[^"]*\/(?:common-build-tools\/cross\/mk\.conf|EMBERBSD-CROSS-MK\.CONF)"$/
abort 'Expected one common cross profile' unless config.scan(include_pattern).size == 1
hashes = [configure, conf, old_profile, new_profile].uniq.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] }
commands = []
clean_env = %w[CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH].to_h { |key| [key, nil] }
clean_env['LC_ALL'] = 'C'
run = lambda do |label, args, env = {}, cwd = work, expected = 0|
  out, err, status = Open3.capture3(clean_env.merge(env), *args, chdir: cwd)
  File.write(work + '/' + label + '.stdout', out)
  File.write(work + '/' + label + '.stderr', err)
  commands << { name: label, argv: args, cwd: cwd, exitstatus: status.exitstatus, expected: expected }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Unexpected #{label} result: #{status.inspect}: #{err}" unless status.exitstatus == expected
  out
end
metadata = {}
%w[old new].zip([old_profile, new_profile]).each do |label, profile|
  dir = work + '/' + label
  Dir.mkdir(dir)
  FileUtils.cp(profile, dir + '/profile.mk')
  File.write(dir + '/mk.conf', config.sub(include_pattern, ".include \"#{dir}/profile.mk\""))
  names = %w[PKG_FAIL_REASON NATIVE_OPSYS NATIVE_CC NATIVE_CXX CCPATH CROSS_DESTDIR
    CWRAPPERS_APPEND.cc LDFLAGS]
  queries = names.flat_map { |name| ['-V', '${' + name + '}'] } + ['-V', '${CONFIGURE_ENV:MBUILD_CC=*}']
  output = run.call(label + '-metadata', [make, '-C', tree + '/devel/ncurses',
    'MAKECONF=' + dir + '/mk.conf', 'WRKOBJDIR=' + dir + '/objects', *queries])
  values = output.lines.map(&:chomp)
  abort 'Unexpected configure metadata' unless values.size == names.size + 1
  data = names.zip(values).to_h
  abort data.fetch('PKG_FAIL_REASON') unless data.fetch('PKG_FAIL_REASON').empty?
  abort 'This causal regression requires Linux' unless data.fetch('NATIVE_OPSYS') == 'Linux'
  assignments = Shellwords.split(values.last)
  abort 'ncurses lost the complete native command' unless assignments == ['BUILD_CC=' + data.fetch('NATIVE_CC')]
  %w[NATIVE_CC NATIVE_CXX].each do |name|
    compiler = Shellwords.split(data.fetch(name))
    abort 'Native GCC16.2.0 is required' unless run.call(label + '-' + name + '-version', [*compiler, '-dumpfullversion']).strip == '16.2.0'
    hashes[compiler.first] = Digest::SHA256.file(compiler.first).hexdigest
  end
  metadata[label] = data
  File.write(dir + '/metadata.json', JSON.pretty_generate(data) + "\n")

  # Reuse the real wrapper executables. Redirect all wrapper writes to this
  # case, as in cross-native-routing.rb; original package work stays read-only.
  bin = dir + '/bin'
  wrappers = dir + '/wrapper-config'
  FileUtils.mkdir_p([bin, wrappers])
  Dir.children(original + '/.cwrapper/bin').each do |name|
    real = File.realpath(original + '/.cwrapper/bin/' + name)
    hashes[real] = Digest::SHA256.file(real).hexdigest
    File.symlink(real, bin + '/' + name)
  end
  Dir.children(original + '/.cwrapper/config').each do |name|
    path = original + '/.cwrapper/config/' + name
    hashes[path] = Digest::SHA256.file(path).hexdigest
    value = File.read(path).sub(/^worklog=.*$/, 'worklog=' + dir + '/wrapper.log')
    value = value.sub(/^wrksrc=.*$/, 'wrksrc=' + dir)
    value = value.gsub(original + '/.cwrapper/bin', bin)
    File.write(wrappers + '/' + name, value)
  end
  recorded_path = File.read(wrappers + '/ld')[/^path=(.*)$/, 1]
  abort 'Missing real linker-wrapper PATH' unless recorded_path
  env = { 'PATH' => bin + ':' + recorded_path, 'CWRAPPERS_CONFIG_DIR' => wrappers,
    'BUILD_CC' => data.fetch('NATIVE_CC') }
  header = "#!/bin/sh\nset -eu\nas_me=configure\ncross_compiling=yes\nac_link=unused\nac_ext=c\nac_objext=o\nac_exeext=\nECHO_N= ECHO_T= ECHO_C=\nBUILD_CFLAGS= BUILD_CPPFLAGS= BUILD_LDFLAGS= BUILD_LIBS=\nexec 5>config.log 6>configure.log\n"
  File.write(dir + '/probe.sh', header + probe + "\n")
  File.write(dir + '/confdefs.h', defines)
  run.call(label + '-upstream-probe', ['/bin/sh', './probe.sh'], env, dir, label == 'old' ? 1 : 0)
  result = File.read(dir + '/config.log')
  if label == 'old'
    abort 'Baseline did not fail through the target linker' unless result.include?('aarch64--netbsd-ld: unrecognised emulation mode: elf_x86_64')
  else
    abort 'Upstream native compile/run did not pass' unless result.include?('result: yes') && result.scan(/\$\? = 0/).size == 2
    abort 'Native compiler still invoked target wrappers' if File.exist?(dir + '/wrapper.log') && !File.empty?(dir + '/wrapper.log')
  end
end
%w[NATIVE_CC NATIVE_CXX].each do |name|
  old = Shellwords.split(metadata.fetch('old').fetch(name))
  current = Shellwords.split(metadata.fetch('new').fetch(name))
  abort 'Native compiler command was replaced or truncated' unless current == old + ['-B/usr/bin/']
end
# The same target driver must still produce AArch64 ELF after the host fix.
current = metadata.fetch('new')
abort 'Target compiler changed' unless current.fetch('CCPATH') == metadata.fetch('old').fetch('CCPATH')
program = probe[/cat >"conftest\.\$ac_ext" <<_ACEOF\n(.*?)\n_ACEOF/m, 1]
abort 'Upstream conftest changed' unless program && program.scan('${cf_cv_main_return:-return}').size == 1
File.write(work + '/target.c', program.sub('${cf_cv_main_return:-return}', 'return'))
File.write(work + '/confdefs.h', defines)
run.call('target-link', [current.fetch('CCPATH'), '--sysroot=' + current.fetch('CROSS_DESTDIR'),
  *Shellwords.split(current.fetch('CWRAPPERS_APPEND.cc')), work + '/target.c',
  *Shellwords.split(current.fetch('LDFLAGS')), '-o', work + '/target'])
elf = File.binread(work + '/target', 20)
abort 'Wrong target ELF' unless elf.start_with?("\x7fELF\x02\x01".b) && elf.byteslice(18, 2).unpack1('v') == 183
hashes.each { |path, sha| abort "Input changed: #{path}" unless Digest::SHA256.file(path).hexdigest == sha }
File.write(work + '/result.json', JSON.pretty_generate(inputs: hashes, metadata: metadata,
  scope: 'Actual ncurses native compile/run probe and target AArch64 link; no full ncurses build or VM execution.') + "\n")
puts 'PASS: ncurses native probe rejects polluted linker PATH before the fix and compiles/runs after it; target AArch64 selection is unchanged'
