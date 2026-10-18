#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted real GCC16/pkgsrc specs-selection regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: cross-openmp-spec.rb PKGSRC CROSS_MAKECONF OLD_PROFILE NEW_PROFILE NEW_WORK' unless ARGV.length == 5
tree, conf, old_profile, new_profile = ARGV.first(4).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'Output must be a new absolute directory' unless ARGV.last == work && !File.exist?(work) && !File.symlink?(work)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
source = File.expand_path('../../development-toolchain/tests/libgomp.c', __dir__)
config = File.read(conf)
pattern = /^\.include "[^"]*\/(?:common-build-tools\/cross\/mk\.conf|EMBERBSD-CROSS-MK\.CONF)"$/
abort 'MAKECONF must include exactly one common cross profile' unless config.scan(pattern).size == 1
abort 'Keep wrapper append policy in the tested profile' if config.match?(/^CWRAPPERS_APPEND\./)
records = []
env = %w[CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH].to_h { |name| [name, nil] }
env['LC_ALL'] = 'C'
run = lambda do |name, argv, extra_env = {}|
  out, err, status = Open3.capture3(env.merge(extra_env), *argv, chdir: work)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  records << { name: name, argv: argv, exitstatus: status.exitstatus, signal: status.termsig }
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  abort "#{name} failed: #{err}" unless status.success?
  out
end
hashes = [source, conf, old_profile, new_profile, tree + '/mk/cwrappers.mk'].uniq.to_h do |path|
  [path, Digest::SHA256.file(path).hexdigest]
end
results = {}
{ 'old' => old_profile, 'new' => new_profile }.each do |label, profile|
  dir = work + '/' + label
  Dir.mkdir(dir)
  selected = dir + '/profile.mk'
  FileUtils.cp(profile, selected)
  makeconf = dir + '/mk.conf'
  File.write(makeconf, config.sub(pattern, ".include \"#{selected}\""))
  # pkgsrc enables its buildlink transformations in this normal wrapper-phase
  # mode. Generate only compiler dispatch and wrappers, not a package phase.
  base = [make, '-C', tree + '/devel/zlib', 'MAKECONF=' + makeconf,
    'WRKOBJDIR=' + dir + '/objects', 'PACKAGES=' + dir + '/packages', 'USE_LANGUAGES=c c++',
    '_PKGSRC_BARRIER=yes']
  names = %w[PKG_FAIL_REASON OPSYS MACHINE_ARCH CC CXX CCPATH CXXPATH PKG_CC PKG_CXX CROSS_DESTDIR TOOLDIR WRKDIR
    CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR CWRAPPERS_SRC_DIR CWRAPPERS_APPEND.cc CWRAPPERS_APPEND.cxx LDFLAGS]
  output = run.call(label + '-metadata', [*base, *names.flat_map { |name| ['-V', '${' + name + '}'] }])
  values = output.lines.map(&:chomp)
  abort 'Unexpected metadata output' unless values.size == names.size
  metadata = names.zip(values).to_h
  File.write(dir + '/metadata.json', JSON.pretty_generate(metadata) + "\n")
  abort metadata.fetch('PKG_FAIL_REASON') unless metadata.fetch('PKG_FAIL_REASON').empty?
  abort 'The target must be NetBSD' unless metadata.fetch('OPSYS') == 'NetBSD'
  # WRKOBJDIR is only a default. Refuse explicit MAKECONF overrides before
  # invoking upstream rules that create compiler links and wrapper files.
  %w[WRKDIR CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR PKG_CC PKG_CXX].each do |key|
    path = metadata.fetch(key)
    abort "Generated #{key} escapes private objects" unless File.expand_path(path) == path && path.start_with?(dir + '/objects/')
    ancestor = path
    loop do
      abort "Generated #{key} crosses a symlink" if File.symlink?(ancestor)
      break if ancestor == dir
      ancestor = File.dirname(ancestor)
    end
  end
  machine, triplet = { 'aarch64' => [183, 'aarch64--netbsd'], 'x86_64' => [62, 'x86_64--netbsd'] }.fetch(metadata.fetch('MACHINE_ARCH'))
  sysroot = File.realpath(metadata.fetch('CROSS_DESTDIR'))
  runtime = sysroot + '/usr/pkg/gcc16/lib'
  crt = runtime + '/gcc/' + triplet + '/16.2.0/'
  expected = runtime + '/libgomp.spec'
  base_spec = sysroot + '/usr/lib/libgomp.spec'
  [expected, base_spec, crt + 'include/omp.h'].each do |path|
    abort "Required target input missing: #{path}" unless File.file?(path)
    hashes[path] = Digest::SHA256.file(path).hexdigest
  end
  readelf = metadata.fetch('TOOLDIR') + '/bin/' + triplet + '-readelf'
  %w[CC CXX].each do |language|
    compiler = metadata.fetch(language + 'PATH')
    abort 'Expected one absolute compiler pathname' unless Shellwords.split(compiler) == [compiler] && compiler.start_with?('/')
    hashes[compiler] = Digest::SHA256.file(compiler).hexdigest
    abort 'Wrong target compiler' unless run.call(label + '-' + language + '-machine', [compiler, '-dumpmachine']).strip == triplet
    abort 'GCC16.2.0 is required' unless run.call(label + '-' + language + '-version', [compiler, '-dumpfullversion']).strip == '16.2.0'
    flags = Shellwords.split(metadata.fetch('CWRAPPERS_APPEND.' + (language == 'CC' ? 'cc' : 'cxx')))
    path = run.call(label + '-' + language + '-direct-spec', [compiler, '--sysroot=' + sysroot, *flags, '-print-file-name=libgomp.spec']).strip
    wanted = label == 'old' ? base_spec : expected
    abort "Wrong #{label} direct specs selection: #{path}" unless path == wanted
  end
  # Generate actual pkgsrc wrappers. No source extraction, build or installation runs.
  run.call(label + '-generate-wrappers', [*base, metadata.fetch('PKG_CC'), metadata.fetch('PKG_CXX'),
    'wrapper-dirs', 'generate-cwrappers'])
  wrapper_env = { 'CWRAPPERS_CONFIG_DIR' => metadata.fetch('CWRAPPERS_CONFIG_DIR') }
  wrapper_dir = metadata.fetch('WRAPPER_BINDIR')
  %w[cc c++].each do |language|
    wrapper = wrapper_dir + '/' + language
    hashes[File.realpath(wrapper)] = Digest::SHA256.file(wrapper).hexdigest
    tag = label + (language == 'cc' ? '-C' : '-CXX')
    path = run.call(tag + '-wrapper-spec', [wrapper, '--sysroot=' + sysroot, '-print-file-name=libgomp.spec'], wrapper_env).strip
    wanted = label == 'old' ? base_spec : expected
    abort "Wrong #{label} wrapper specs selection: #{path}" unless path == wanted
    object = dir + '/contract.o'
    if language == 'cc'
      run.call(tag + '-compile', [wrapper, '--sysroot=' + sysroot, '-std=c11', '-O2',
        '-Wall', '-Wextra', '-Werror', '-fopenmp', '-c', source, '-o', object], wrapper_env)
    end
    binary = dir + '/' + language.tr('+', 'x') + '-contract'
    run.call(tag + '-link', [wrapper, '--sysroot=' + sysroot, '-fopenmp', '-v', object,
      *Shellwords.split(metadata.fetch('LDFLAGS')), '-o', binary], wrapper_env)
    log = File.read(work + '/' + tag + '-link.stderr')
    abort 'Link did not read the selected specs file' unless log.lines.map(&:chomp).include?('Reading specs from ' + wanted)
    elf = File.binread(binary, 20)
    abort 'Wrong target ELF' unless elf.start_with?("\x7fELF\x02\x01".b) && elf.byteslice(18, 2).unpack1('v') == machine
    dynamic = run.call(tag + '-dynamic', [readelf, '-d', binary])
    needed = dynamic.scan(/\(NEEDED\).*?\[([^\]]+)\]/).flatten
    abort 'Wrong OpenMP ABI' unless needed.include?('libgomp.so.1') && needed.grep(/^libgomp\./) == ['libgomp.so.1']
    paths = dynamic.scan(/\((?:RUNPATH|RPATH)\).*?\[([^\]]+)\]/).flatten.flat_map { |value| value.split(':') }
    abort 'Missing GCC16 runtime path' unless paths.include?('/usr/pkg/gcc16/lib')
    abort 'Build-host runtime path leaked' unless (paths - %w[/usr/pkg/gcc16/lib /usr/pkg/lib /usr/lib /lib]).empty?
    results[tag] = { specs: path, elf_machine: machine, needed: needed, runtime_paths: paths,
      binary_sha256: Digest::SHA256.file(binary).hexdigest }
  end
end
hashes.each { |path, sha| abort "Input changed: #{path}" unless Digest::SHA256.file(path).hexdigest == sha }
File.write(work + '/result.json', JSON.pretty_generate(inputs: hashes, results: results,
  scope: 'Real metadata, generated pkgsrc C/C++ wrappers, GCC16 spec selection and target ELF linking; no target execution.') + "\n")
puts 'PASS: real GCC16 and pkgsrc C/C++ wrappers select staged OpenMP specs; target ELF links retain the selected ABI and runtime path'
