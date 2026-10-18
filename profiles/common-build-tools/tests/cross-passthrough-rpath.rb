#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real GCC16/Libtool runtime-path regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'pathname'
require 'shellwords'

abort 'Usage: cross-passthrough-rpath.rb PKGSRC CROSS_MAKECONF NATIVE_MAKECONF NEW_WORK' unless ARGV.length == 4
tree, cross, native = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use absolute portable paths' unless [tree, cross, native, work].all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) }
abort 'Output exists' if File.exist?(work) || File.symlink?(work)
FileUtils.mkdir(work)
patch = File.expand_path('../patches/pkgsrc-cross-passthrough-rpath.patch', __dir__)
make = ENV.fetch('BMAKE', 'bmake')
commands = []
results = {}
hashes = [cross, native, patch, tree + '/mk/buildlink3/bsd.buildlink3.mk'].to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
env = %w[CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH].to_h { |n| [n, nil] }
env['LC_ALL'] = 'C'
run = lambda do |name, argv, cwd = work, extra = {}|
  out, err, status = Open3.capture3(env.merge(extra), *argv, chdir: cwd)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << { name: name, argv: argv, cwd: cwd, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Failed #{name}: #{err}" unless status.success?
  out
end
%w[old new].each do |variant|
  target = work + '/' + variant
  FileUtils.mkdir_p(target + '/devel')
  Dir.children(tree).each do |name|
    File.symlink(tree + '/' + name, target + '/' + name) unless %w[mk devel].include?(name)
  end
  FileUtils.cp_r(tree + '/mk', target)
  Dir.children(tree + '/devel').each do |name|
    if name == 'zlib'
      FileUtils.cp_r(tree + '/devel/zlib', target + '/devel')
    else
      File.symlink(tree + '/devel/' + name, target + '/devel/' + name)
    end
  end
  # Accept the current exported tree as well as its pre-repair counterpart.
  # A reverse/forward application must match the complete patch with no fuzz.
  prepared = File.read(target + '/mk/buildlink3/bsd.buildlink3.mk').include?("_CWRAPPERS_UNWRAP+=\t${_dir_}:")
  if variant == 'old' && prepared
    run.call('reverse-patch', ['patch', '-f', '-R', '-F', '0', '-p1', '-d', target, '-i', patch])
  elsif variant == 'new' && !prepared
    run.call('patch', ['patch', '-f', '-N', '-F', '0', '-p1', '-d', target, '-i', patch])
  end
end
metadata = lambda do |name, variant, config, extra = []|
  dir = work + '/objects-' + name
  base = [make, '-C', work + '/' + variant + '/devel/zlib', 'MAKECONF=' + config,
    'WRKDIR=' + dir, 'WRKOBJDIR=' + dir, 'PACKAGES=' + work + '/packages',
    'USE_LIBTOOL=yes', 'USE_LANGUAGES=c c++', '_PKGSRC_BARRIER=yes', *extra]
  names = %w[PKG_FAIL_REASON USE_CROSS_COMPILE CROSS_DESTDIR TOOLDIR CC CXX CCPATH CXXPATH
    PKG_CC PKG_CXX WRKDIR CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR LDFLAGS
    _CWRAPPERS_TRANSFORM _CWRAPPERS_UNWRAP]
  values = run.call(name + '-metadata', [*base, *names.flat_map { |n| ['-V', '${' + n + '}'] }]).lines.map(&:chomp)
  abort 'Unexpected metadata shape' unless values.size == names.size
  data = names.zip(values).to_h
  abort data['PKG_FAIL_REASON'] unless data['PKG_FAIL_REASON'].empty?
  %w[WRKDIR CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR PKG_CC PKG_CXX].each do |key|
    path = data.fetch(key)
    abort "Output outside private work: #{key}" unless path == dir || path.start_with?(dir + '/')
    abort "Unnormalized output: #{key}" unless Pathname.new(path).cleanpath.to_s == path
    Pathname.new(path).ascend { |part| abort "Symlink output ancestor: #{part}" if File.symlink?(part) }
  end
  results[name] = data
  [data, base]
end
source = work + '/consumer.cpp'
File.write(source, "#include <vector>\nextern \"C\" int ember_runtime_value(int count) { std::vector<int> values(count, 7); return values.at(count - 1); }\n")
%w[old new].each do |variant|
  data, base = metadata.call(variant, variant, cross)
  sysroot = File.realpath(data.fetch('CROSS_DESTDIR'))
  runtime = sysroot + '/usr/pkg/gcc16/lib'
  %w[libstdc++.la libstdc++.so.7 libgomp.la libgomp.so.1].each do |name|
    path = runtime + '/' + name
    hashes[path] = Digest::SHA256.file(path).hexdigest
  end
  %w[CCPATH CXXPATH].each do |name|
    compiler = data.fetch(name)
    hashes[compiler] = Digest::SHA256.file(compiler).hexdigest
    abort 'Expected absolute compiler path' unless compiler.start_with?('/') && Shellwords.split(compiler) == [compiler]
    abort 'GCC16.2.0 required' unless run.call(variant + name + '-version', [compiler, '-dumpfullversion']).strip == '16.2.0'
    abort 'AArch64 target required' unless run.call(variant + name + '-machine', [compiler, '-dumpmachine']).strip == 'aarch64--netbsd'
  end
  run.call(variant + '-wrappers', [*base, data.fetch('PKG_CC'), data.fetch('PKG_CXX'), 'wrapper-dirs', 'generate-cwrappers'])
  dir = work + '/link-' + variant
  FileUtils.mkdir_p(dir + '/stage/usr/pkg/lib')
  wrapper = data.fetch('WRAPPER_BINDIR')
  extra = { 'CWRAPPERS_CONFIG_DIR' => data.fetch('CWRAPPERS_CONFIG_DIR'),
    'PATH' => wrapper + ':' + data.fetch('TOOLDIR') + '/bin:' + ENV.fetch('PATH') }
  libtool = wrapper + '/libtool'
  run.call(variant + '-compile', [libtool, '--tag=CXX', '--mode=compile', wrapper + '/c++', '-O2', '-fPIC', '-c', source, '-o', 'consumer.lo'], dir, extra)
  # ngspice links its mixed C/C++ DSO with the C driver and explicit libstdc++.
  run.call(variant + '-link', [libtool, '--tag=CC', '--mode=link', wrapper + '/cc',
    '-shared', 'consumer.lo', *Shellwords.split(data.fetch('LDFLAGS')), '-lstdc++', '-fopenmp',
    '-o', 'libember-runtime.la', '-rpath', '/usr/pkg/lib', '-version-info', '0:0:0'], dir, extra)
  run.call(variant + '-install', [libtool, '--mode=install', 'install', '-c', 'libember-runtime.la', dir + '/stage/usr/pkg/lib'], dir, extra)
  elf = dir + '/stage/usr/pkg/lib/libember-runtime.so.0.0.0'
  header = File.binread(elf, 20)
  abort 'Not AArch64 ELF64 little endian' unless header.start_with?("\x7fELF\x02\x01".b) && header.byteslice(18, 2).unpack1('v') == 183
  dynamic = run.call(variant + '-elf', [data.fetch('TOOLDIR') + '/bin/aarch64--netbsd-readelf', '-d', elf])
  paths = dynamic.scan(/\((?:RUNPATH|RPATH)\).*?\[([^\]]+)\]/).flatten.flat_map { |v| v.split(':') }
  needed = dynamic.scan(/\(NEEDED\).*?\[([^\]]+)\]/).flatten
  abort 'C++ runtime or OpenMP ABI missing' unless needed.include?('libstdc++.so.7') && needed.include?('libgomp.so.1')
  la = File.read(dir + '/stage/usr/pkg/lib/libember-runtime.la')
  if variant == 'old'
    abort 'Baseline did not reproduce SDK path leak' unless paths.include?(runtime) && la.include?('-L' + runtime)
  else
    abort 'Target runtime path lost' unless paths.include?('/usr/pkg/gcc16/lib')
    abort 'Unexpected runtime path' unless (paths - %w[/usr/pkg/lib /usr/pkg/gcc16/lib]).empty?
    abort 'Private metadata path survived' if la.include?(sysroot) || la.include?(work)
    abort 'Installed runtime dependency path lost' unless la.include?('-L/usr/pkg/gcc16/lib')
  end
  results[variant + '-elf'] = { sha256: Digest::SHA256.file(elf).hexdigest, needed: needed, runtime_paths: paths, la: la }
end
sysroot = results.fetch('old').fetch('CROSS_DESTDIR')
candidate = sysroot + '/usr/pkg/gcc16'
outside = sysroot + '-other/usr/pkg/gcc16'
%w[old new].each do |variant|
  metadata.call(variant + '-native', variant, native, ['BUILDLINK_PASSTHRU_DIRS=' + candidate + ' ' + outside])
  metadata.call(variant + '-boundary', variant, cross, ['BUILDLINK_PASSTHRU_DIRS=' + candidate + ' ' + outside])
end
%w[_CWRAPPERS_TRANSFORM _CWRAPPERS_UNWRAP].each do |key|
  normalized = %w[old new].map do |variant|
    results.fetch(variant + '-native').fetch(key).gsub(work + '/objects-' + variant + '-native', '%WORK%')
  end
  abort 'Native mapping changed' unless normalized.uniq.size == 1
end
new_rules = results.fetch('new-boundary').fetch('_CWRAPPERS_TRANSFORM').split
abort 'Prefix sibling was changed' unless new_rules.include?("R:#{outside}:#{outside}")
abort 'SDK compile/link mappings were changed' unless %w[I L P].all? { |kind| new_rules.include?("#{kind}:#{candidate}:#{candidate}") }
abort 'SDK runtime mapping missing' unless new_rules.include?("R:#{candidate}:/usr/pkg/gcc16")
hashes.each { |p, sha| abort "Input changed: #{p}" unless Digest::SHA256.file(p).hexdigest == sha }
File.write(work + '/result.json', JSON.pretty_generate(inputs: hashes, results: results,
  scope: 'Real pkgsrc C/C++ wrappers, GCC16 Libtool DSO link/install and target ELF/metadata; no package installation or target execution.') + "\n")
puts 'PASS: genuine C++ Libtool SDK RPATH leak repaired; installed metadata, native and boundary mappings checked'
