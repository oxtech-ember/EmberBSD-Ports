#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise native links in the real cross wrapper PATH.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: cross-native-routing.rb PKGSRC CROSS_MAKECONF LIBX11_WORK FREETYPE_SOURCE NEW_WORK' unless ARGV.length == 5
tree, conf, xwork, freetype = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
ports = File.expand_path('../..', __dir__)
make = ENV.fetch('BMAKE', 'bmake')
# Copy only the recipe under test. All other framework/source inputs stay read-only.
export = work + '/pkgsrc'
Dir.mkdir(export)
Dir.children(tree).each { |name| File.symlink(tree + '/' + name, export + '/' + name) }
{'graphics' => 'freetype2', 'x11' => 'libXt'}.each do |category, recipe|
  File.unlink(export + '/' + category)
  Dir.mkdir(export + '/' + category)
  Dir.children(tree + '/' + category).each do |name|
    next if name == recipe
    File.symlink(tree + '/' + category + '/' + name, export + '/' + category + '/' + name)
  end
  FileUtils.cp_r(ports + '/common-graphics/recipes/' + category + '/' + recipe, export + '/' + category + '/' + recipe)
end
text = File.read(conf)
{'EMBERBSD-CROSS-MK.CONF' => ports + '/common-build-tools/cross/mk.conf',
 'EMBERBSD-COMMON-GRAPHICS-MK.CONF' => ports + '/common-graphics/mk.conf'}.each do |name, path|
  pattern = /^\.include "[^"]*\/#{Regexp.escape(name)}"$/
  abort "expected one #{name} include" unless text.scan(pattern).length == 1
  File.unlink(export + '/' + name)
  FileUtils.cp(path, export + '/' + name)
  text = text.sub(pattern, ".include \"#{export}/#{name}\"")
end
text += "\nWRKOBJDIR=#{work}/objects\nPACKAGES=#{work}/packages\n"
File.write(work + '/mk.conf', text)
run = lambda do |name, env, args, cwd = work, success = true|
  out, err, status = Open3.capture3(env, *args, chdir: cwd)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  File.write(work + '/' + name + '.json', JSON.pretty_generate(argv: args, exit: status.exitstatus, cwd: cwd, env: env))
  abort "FAIL #{name}: exit #{status.exitstatus}: #{err}" if success && !status.success?
  [out, err, status]
end
query = lambda do |name, package, variables, *overrides|
  run.call(name, {}, [make, '-C', export + '/' + package, 'MAKECONF=' + work + '/mk.conf', *overrides,
    *variables.flat_map { |v| ['-V', '${' + v + '}'] }]).first.lines.map(&:chomp)
end
vars = %w[PKG_FAIL_REASON NATIVE_OPSYS EMBERBSD_CROSS_BUILD_CC EMBERBSD_CROSS_BUILD_CXX NATIVE_CC NATIVE_CXX CONFIGURE_ENV CC CXX CROSS_DESTDIR TOOLDIR]
v = vars.zip(query.call('libX11-metadata', 'x11/libX11', vars)).to_h
abort v.fetch('PKG_FAIL_REASON') unless v.fetch('PKG_FAIL_REASON').empty?
abort 'this subprocess-routing regression requires an actual Darwin host' unless v.fetch('NATIVE_OPSYS') == 'Darwin'
# Use actual cwrapper executables and configuration; redirect every write to this fixture.
bin = work + '/bin'
config = work + '/wrapper-config'
FileUtils.mkdir_p([bin, config])
Dir.children(xwork + '/.cwrapper/bin').each do |name|
  File.symlink(File.realpath(xwork + '/.cwrapper/bin/' + name), bin + '/' + name)
end
Dir.children(xwork + '/.cwrapper/config').each do |name|
  value = File.read(xwork + '/.cwrapper/config/' + name)
  value = value.sub(/^worklog=.*$/, 'worklog=' + work + '/wrapper.log')
  value = value.sub(/^wrksrc=.*$/, 'wrksrc=' + work)
  value = value.gsub(xwork + '/.cwrapper/bin', bin)
  File.write(config + '/' + name, value)
end
recorded_path = File.read(xwork + '/.cwrapper/config/ld')[/^path=(.*)$/, 1]
abort 'missing actual wrapper PATH' unless recorded_path
env = {'PATH' => bin + ':' + recorded_path, 'CWRAPPERS_CONFIG_DIR' => config}
File.write(work + '/native.c', "#include <stdio.h>\nint main(void) { puts(\"native C\"); return 0; }\n")
File.write(work + '/native.cc', "#include <iostream>\nint main() { std::cout << \"native C++\\n\"; }\n")
provider_hashes = %w[EMBERBSD_CROSS_BUILD_CC EMBERBSD_CROSS_BUILD_CXX].to_h { |key| [v.fetch(key), Digest::SHA256.file(v.fetch(key)).hexdigest] }
%w[CC CXX].each do |lang|
  cc = Shellwords.split(v.fetch('NATIVE_' + lang))
  source = work + (lang == 'CC' ? '/native.c' : '/native.cc')
  binary = work + '/native-' + lang
  run.call('link-' + lang, env, [*cc, source, '-o', binary])
  out = run.call('execute-' + lang, {}, [binary]).first
  abort 'wrong native execution result' unless out == (lang == 'CC' ? "native C\n" : "native C++\n")
end
abort 'native compiler invoked target wrappers' if File.exist?(work + '/wrapper.log') && !File.empty?(work + '/wrapper.log')
%w[CC CXX].each do |lang|
  expected = [v.fetch('EMBERBSD_CROSS_BUILD_' + lang), '-B/usr/bin/']
  abort "wrong NATIVE_#{lang} command" unless Shellwords.split(v.fetch('NATIVE_' + lang)) == expected
  assignments = Shellwords.split(v.fetch('CONFIGURE_ENV')).grep(/^#{lang}_FOR_BUILD=/)
  abort 'missing or inconsistent configure compiler command' if assignments.empty? || assignments.any? { |s| Shellwords.split(s.split('=', 2).last) != expected }
end
# Compile the unchanged upstream generator and consume its actual keysym headers.
makekeys = xwork + '/libX11-1.8.13/src/util/makekeys.c'
run.call('makekeys-link', env, [*Shellwords.split(v.fetch('NATIVE_CC')), makekeys, '-o', work + '/makekeys'])
headers = Dir[v.fetch('CROSS_DESTDIR') + '/usr/pkg/include/X11/*keysym*.h'].sort
abort 'missing installed keysym inputs' if headers.empty?
out = run.call('makekeys-execute', {}, [work + '/makekeys', *headers]).first
abort 'makekeys produced no hash table' unless out.include?('hashString') && out.include?('hashKeysym')
# Extract the exact native compiler/suffix probe from the pinned upstream configure.
ft = query.call('freetype-metadata', 'graphics/freetype2', %w[PKG_FAIL_REASON CONFIGURE_ENV])
abort ft.first unless ft.first.empty?
build_cc = Shellwords.split(ft.last).grep(/^CC_BUILD=/)
abort 'wrong FreeType native compiler command' unless build_cc == ['CC_BUILD=' + v.fetch('NATIVE_CC')]
source = File.read(freetype + '/builds/unix/configure')
start = source.index('  rm -f a.* b.* a_out.exe conftest.*')
finish = source.index('  CFLAGS_BUILD=', start)
abort 'upstream native probe changed' unless start && finish && source[start...finish].include?('${CC_BUILD} conftest.c')
probe = "#!/bin/sh\nset -eu\nas_me=configure as_lineno=0 LINENO=0\nas_fn_error() { echo \"$2\" >&2; exit 1; }\nexec 5>config.log 6>configure.log\n" + source[start...finish] + "\n[ -z \"$EXEEXT_BUILD\" ]\n"
FileUtils.mkdir_p(work + '/freetype-probe')
File.write(work + '/freetype-probe/probe.sh', probe)
run.call('freetype-native-probe', env.merge('CC_BUILD' => build_cc.first.split('=', 2).last), ['/bin/sh', 'probe.sh'], work + '/freetype-probe')
# libXt appends another command after the common profile too. Exercise the last value.
xt = query.call('libXt-metadata', 'x11/libXt', %w[PKG_FAIL_REASON CONFIGURE_ENV])
abort xt.first unless xt.first.empty?
xt_cc = Shellwords.split(xt.last).grep(/^CC_FOR_BUILD=/).last&.split('=', 2)&.last
abort 'missing libXt build compiler' unless xt_cc
run.call('libXt-native-link', env, [*Shellwords.split(xt_cc), work + '/native.c', '-o', work + '/libXt-native'])
abort 'libXt reset the selected native compiler command' unless xt_cc == v.fetch('NATIVE_CC')
abort 'libXt native program failed' unless run.call('libXt-native-execute', {}, [work + '/libXt-native']).first == "native C\n"
abort 'native compiler invoked target wrappers' if File.exist?(work + '/wrapper.log') && !File.empty?(work + '/wrapper.log')
# The unchanged target driver still links ELF64/x86-64 through target binutils.
sysroot = v.fetch('CROSS_DESTDIR')
triplet = 'x86_64--netbsd'
cc = v.fetch('CC')
run.call('target-link', env, [cc, '--sysroot=' + sysroot, '-B' + sysroot + '/usr/pkg/gcc16/lib/gcc/' + triplet + '/16.2.0/', '-L' + sysroot + '/usr/pkg/gcc16/lib', work + '/native.c', '-o', work + '/target'])
elf = File.binread(work + '/target', 20)
abort 'target route changed' unless elf.start_with?("\x7fELF\x02\x01".b) && elf.byteslice(18, 2).unpack1('v') == 62
provider_hashes.each { |path, sha| abort 'native provider changed' unless Digest::SHA256.file(path).hexdigest == sha }
File.write(work + '/provider-sha256.json', JSON.pretty_generate(provider_hashes))
puts 'PASS: real polluted-PATH C/C++ native links/runs, libX11 makekeys, FreeType/libXt native commands and target ELF route'
