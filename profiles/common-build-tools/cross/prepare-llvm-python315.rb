#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), a bounded package metadata migration.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'optparse'

options = {}
OptionParser.new do |parser|
  parser.banner = 'Usage: prepare-llvm-python315.rb --clang ARCHIVE --lld ARCHIVE --lit ARCHIVE --clang-source DIRECTORY --python HOST_PYTHON --cmake HOST_CMAKE --readelf TARGET_READELF --pkg-create HOST_PKG_CREATE NEW_OUTPUT'
  %w[clang lld lit clang-source python cmake readelf pkg-create].each do |name|
    parser.on("--#{name} PATH") { |value| options[name] = File.expand_path(value) }
  end
end.parse!
abort 'All options and one new output directory are required' unless options.size == 8 && ARGV.size == 1
out = File.expand_path(ARGV.fetch(0))
abort "Output exists: #{out}" if File.exist?(out)
options.each { |key, path| abort "Missing #{key}: #{path}" unless File.exist?(path) }

def run!(*args)
  output, status = Open3.capture2e(*args)
  abort "Command failed: #{args.inspect}\n#{output}" unless status.success?
  output
end

def digest(path)
  Digest::SHA256.file(path).hexdigest
end

scripts = {
  'bin/analyze-build' => 'tools/scan-build-py/bin/analyze-build',
  'bin/git-clang-format' => 'tools/clang-format/git-clang-format',
  'bin/hmaptool' => 'utils/hmaptool/hmaptool',
  'bin/intercept-build' => 'tools/scan-build-py/bin/intercept-build',
  'bin/scan-build-py' => 'tools/scan-build-py/bin/scan-build',
  'bin/scan-view' => 'tools/scan-view/bin/scan-view',
  'libexec/analyze-c++' => 'tools/scan-build-py/libexec/analyze-c++',
  'libexec/analyze-cc' => 'tools/scan-build-py/libexec/analyze-cc',
  'libexec/intercept-c++' => 'tools/scan-build-py/libexec/intercept-c++',
  'libexec/intercept-cc' => 'tools/scan-build-py/libexec/intercept-cc',
  'share/clang/clang-format-diff.py' => 'tools/clang-format/clang-format-diff.py',
  'share/scan-view/Reporter.py' => 'tools/scan-view/share/Reporter.py',
  'share/scan-view/startfile.py' => 'tools/scan-view/share/startfile.py'
}.freeze
version = run!(options.fetch('python'), '--version').strip
abort "Expected host Python 3.15: #{version}" unless version.match?(/\APython 3\.15\./)
FileUtils.mkdir_p(out)
source_root = File.expand_path('../../..', __dir__)
source_commit = run!('git', '-C', source_root, 'rev-parse', 'HEAD').strip
receipt = { 'source_commit' => source_commit, 'helper_sha256' => digest(__FILE__), 'operation' => 'repackage; no C/C++ compilation or target installation',
            'python' => version, 'cmake' => run!(options.fetch('cmake'), '--version').lines.first.strip,
            'packages' => {} }
old_rpath = '/usr/pkg/gcc16/lib:/usr/pkg/lib:/usr/pkg/lib/python3.14/config-3.14'
new_rpath = '/usr/pkg/gcc16/lib:/usr/pkg/lib'
%w[clang lld lit].each do |kind|
  archive = options.fetch(kind)
  members = run!('/usr/bin/tar', '-tf', archive).lines.map(&:chomp)
  abort "Invalid archive paths: #{archive}" unless members.all? do |member|
    !member.start_with?('/') && !member.split('/').include?('..') && !member.include?("\n")
  end
  stage = File.join(out, kind)
  Dir.mkdir(stage)
  run!({ 'COPYFILE_DISABLE' => '1' }, '/usr/bin/tar', '-xf', archive, '-C', stage)
  contents = File.read(File.join(stage, '+CONTENTS'))
  name = kind == 'lit' ? 'py315-llvm-lit-23.1.3' : "#{kind}-23.1.3"
  abort "Wrong package: #{archive}" unless contents.include?("@name #{name}\n")
  abort 'Unexpected prefix' unless contents.include?("@cwd /usr/pkg\n")
  build = File.read(File.join(stage, '+BUILD_INFO'))
  abort 'Expected target NetBSD/aarch64 package' unless build.match?(/^OPSYS=NetBSD$/) && build.match?(/^MACHINE_ARCH=aarch64$/)
  payload = []
  skip = false
  contents.each_line(chomp: true) do |line|
    if skip
      skip = false
    elsif line == '@ignore'
      skip = true
    elsif !line.empty? && !line.start_with?('@')
      payload << line
    end
  end
  last_payload = nil
  contents.each_line(chomp: true) do |line|
    if line.start_with?('@comment MD5:')
      abort "Wrong input MD5: #{last_payload}" unless last_payload && Digest::MD5.file(File.join(stage, last_payload)).hexdigest == line.delete_prefix('@comment MD5:')
    elsif line.start_with?('@comment Symlink:')
      abort "Wrong input link: #{last_payload}" unless last_payload && File.readlink(File.join(stage, last_payload)) == line.delete_prefix('@comment Symlink:')
    elsif payload.include?(line)
      last_payload = line
    end
  end
  before = {}
  expected = {}
  elf_inodes = {}
  payload.each do |rel|
    path = File.join(stage, rel)
    if File.symlink?(path)
      before[rel] = { 'symlink' => File.readlink(path) }
      expected[rel] = before.fetch(rel)
    else
      bytes = File.binread(path)
      before[rel] = { 'sha256' => Digest::SHA256.hexdigest(bytes) }
      expected[rel] = before.fetch(rel)
      elf_inodes[File.stat(path).ino] = true if bytes.start_with?("\x7fELF".b)
    end
  end
  changes = {}
  if kind == 'clang'
    scripts.each do |rel, source_rel|
      path = File.join(stage, rel)
      source = File.join(options.fetch('clang-source'), source_rel)
      bytes = File.binread(path)
      abort "Unexpected interpreter: #{rel}" unless bytes.start_with?("#!/usr/pkg/bin/python3.14\n")
      abort "Not the pinned upstream script: #{source_rel}" unless bytes.lines.drop(1) == File.binread(source).lines.drop(1)
      mode = File.stat(path).mode & 0777
      File.chmod(mode | 0200, path)
      File.binwrite(path, bytes.sub("#!/usr/pkg/bin/python3.14\n", "#!/usr/pkg/bin/python3.15\n"))
      File.chmod(mode, path)
      expected[rel] = { 'sha256' => digest(path) }
      changes[rel] = { 'kind' => 'interpreter only', 'upstream' => source_rel, 'upstream_sha256' => digest(source) }
    end
    File.write(File.join(out, 'py-compile.log'), run!({ 'PYTHONPYCACHEPREFIX' => File.join(out, 'pycache') }, options.fetch('python'), '-m', 'py_compile', *scripts.keys.map { |rel| File.join(stage, rel) }))
  end
  changed_inodes = {}
  payload.each do |rel|
    path = File.join(stage, rel)
    next if File.symlink?(path)
    inode = File.stat(path).ino
    next unless elf_inodes[inode]
    if changed_inodes[inode]
      expected[rel], changes[rel] = changed_inodes.fetch(inode)
      next
    end
    bytes = File.binread(path)
    abort "Not AArch64 ELF64: #{rel}" unless bytes.byteslice(4, 2) == "\x02\x01".b && bytes.byteslice(18, 2).unpack1('v') == 183
    dynamic = run!(options.fetch('readelf'), '-d', path)
    abort "Unexpected libpython dependency: #{rel}" if dynamic.match?(/NEEDED.*libpython/)
    old = bytes.index(old_rpath)
    if old
      abort "Unexpected old RPATH in #{kind}: #{rel}" unless kind == 'clang'
      abort "Ambiguous RPATH string: #{rel}" if bytes.index(old_rpath, old + 1)
      unless changed_inodes[inode]
        cmake = File.join(out, 'change-rpath.cmake')
        File.write(cmake, "file(RPATH_CHANGE FILE [==[#{path}]==] OLD_RPATH [==[#{old_rpath}]==] NEW_RPATH [==[#{new_rpath}]==])\n")
        run!(options.fetch('cmake'), '-P', cmake)

      end
      wanted = bytes.dup
      wanted[old, old_rpath.bytesize] = new_rpath.ljust(old_rpath.bytesize, "\0")
      abort "Unexpected ELF byte change: #{rel}" unless File.binread(path) == wanted
      expected[rel] = { 'sha256' => Digest::SHA256.hexdigest(wanted) }
      changes[rel] = { 'kind' => 'RPATH string only', 'offset' => old, 'length' => old_rpath.bytesize }
      changed_inodes[inode] = [expected.fetch(rel), changes.fetch(rel)]
    end
    final_dynamic = run!(options.fetch('readelf'), '-d', path)
    paths = final_dynamic.scan(/\((?:RPATH|RUNPATH)\).*?\[([^\]]+)\]/).flatten.flat_map { |entry| entry.split(':') }
    abort "Unexpected RPATH: #{rel}: #{paths}" unless (paths - %w[/usr/pkg/lib /usr/pkg/gcc16/lib]).empty?
  end
  payload.each do |rel|
    path = File.join(stage, rel)
    actual = File.symlink?(path) ? { 'symlink' => File.readlink(path) } : { 'sha256' => digest(path) }
    abort "Unexpected payload change: #{rel}" unless actual == expected.fetch(rel)
  end
  if kind == 'lit'
    %w[bin/lit bin/llvm-lit].each do |rel|
      abort "Wrong lit interpreter: #{rel}" unless File.open(File.join(stage, rel), &:readline) == "#!/usr/pkg/bin/python3.15\n"
    end
  end
  # Keep the original compile provenance. These fields describe a separate
  # package operation; they do not claim a new compiler build.
  build += "EMBERBSD_REPACKAGE_KIND=python315-runtime-metadata\nEMBERBSD_REPACKAGE_INPUT_SHA256=#{digest(archive)}\nEMBERBSD_REPACKAGE_SOURCE=#{source_commit}\n"
  File.write(File.join(stage, '+BUILD_INFO'), build)
  plist = contents.lines.reject { |line| line.start_with?('@comment MD5:', '@comment Symlink:') }.join
  plist = plist.sub("@name #{name}\n", "@name #{name}nb1\n")
  plist = plist.gsub(/^@pkgdep py314-llvm-lit[^\n]*$/, '@pkgdep py315-llvm-lit>=23.1.3nb1')
  plist = plist.sub("@name #{name}nb1\n", "@name #{name}nb1\n@pkgdep python315>=3.15.0\n") if kind == 'clang'
  plist = plist.sub("@name #{name}nb1\n", "@name #{name}nb1\n@pkgcfl py[0-9]*-llvm-lit-[0-9]*\n") if kind == 'lit'
  abort 'Old runtime dependency retained' if plist.match?(/^@pkgdep (?:python314|py314-)/)
  plist_path = File.join(out, "#{kind}.plist")
  File.write(plist_path, plist)
  result = File.join(out, "#{name}nb1.tgz")
  command = [options.fetch('pkg-create'), '-p', stage, '-I', '/usr/pkg', '-f', plist_path,
             '-c', File.join(stage, '+COMMENT'), '-d', File.join(stage, '+DESC'),
             '-B', File.join(stage, '+BUILD_INFO')]
  { '+BUILD_VERSION' => '-b', '+INSTALL' => '-i', '+DEINSTALL' => '-k', '+DISPLAY' => '-D',
    '+SIZE_PKG' => '-s', '+SIZE_ALL' => '-S' }.each do |entry, flag|
    command += [flag, File.join(stage, entry)] if File.file?(File.join(stage, entry))
  end
  abort 'Unexpected +REQUIRE script' if File.exist?(File.join(stage, '+REQUIRE'))
  File.write(File.join(out, "#{kind}-pkg-create.log"), run!(*command, result))
  File.write(File.join(stage, '+CONTENTS'), run!('/usr/bin/tar', '-xOf', result, '+CONTENTS'))
  receipt.fetch('packages')[name] = { 'input_sha256' => digest(archive), 'output' => result,
    'output_sha256' => digest(result), 'payload_before' => before, 'payload_after' => expected, 'changes' => changes }
end
File.write(File.join(out, 'receipt.json'), JSON.pretty_generate(receipt) + "\n")
puts 'PASS: package metadata, upstream script bodies, Python 3.15 compilation, exact ELF byte changes and unchanged remaining payload.'
