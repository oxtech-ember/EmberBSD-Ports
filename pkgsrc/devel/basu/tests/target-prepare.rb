#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package existing local upstream unit tests.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'tmpdir'

if ARGV == ['--self-test']
  checks = 0
  Dir.mktmpdir('basu-target-prepare-') do |temp|
    ['', '.tar.gz', '.tar.gz.sha256'].each_with_index do |suffix, index|
      %w[file directory symlink].each do |kind|
        output = File.join(temp, "case-#{index}-#{kind}")
        protected_path = output + suffix
        case kind
        when 'file' then File.write(protected_path, 'preserve this file')
        when 'directory' then Dir.mkdir(protected_path)
        when 'symlink' then File.symlink('missing-target', protected_path)
        end
        out, status = Open3.capture2e({'READELF'=>'/not-used'}, RbConfig.ruby, __FILE__,
                                     '/missing-source', '/missing-sysroot', output)
        raise "Existing output accepted: #{out}" if status.success? || !out.include?('Output exists:')
        case kind
        when 'file' then raise 'File changed' unless File.read(protected_path) == 'preserve this file'
        when 'directory' then raise 'Directory changed' unless Dir.empty?(protected_path)
        when 'symlink' then raise 'Link changed' unless File.readlink(protected_path) == 'missing-target'
        end
        checks += 1
      end
    end
    result = File.join(temp, 'results')
    Dir.mkdir(result)
    out, status = Open3.capture2e('/bin/sh', File.join(__dir__, 'target-run.sh'), result)
    raise "Existing target results accepted: #{out}" unless status.exitstatus == 2 && Dir.empty?(result)
    checks += 1
  end
  puts "PASS: #{checks} existing-output controls; no target programs executed"
  exit
end

abort 'Usage: target-prepare.rb SOURCE_WITH_OUTPUT SYSROOT NEW_OUTPUT' unless ARGV.size == 3
source, sysroot, output = ARGV.map { |path| File.expand_path(path) }
archive = output + '.tar.gz'
checksum = archive + '.sha256'
[output, archive, checksum].each do |path|
  abort "Output exists: #{path}" if File.exist?(path) || File.symlink?(path)
end
reader = ENV.fetch('READELF')
source = File.realpath(source)
sysroot = File.realpath(sysroot)
build = File.join(source, 'output')
names = %w[test-bus-signature test-bus-error test-bus-introspect]
intro = JSON.parse(File.read(File.join(build, 'meson-info/intro-tests.json')))
project = JSON.parse(File.read(File.join(build, 'meson-info/intro-projectinfo.json')))
raise 'Wrong upstream version' unless project.fetch('version') == '0.2.1'

def inspect_elf(reader, *args)
  out, err, status = Open3.capture3({'LC_ALL'=>'C'}, reader, *args)
  raise "readelf failed: #{err}" unless status.success?
  out
end

metadata = {}
base_paths = {}
names.each do |name|
  input = File.join(build, name)
  entries = intro.select { |entry| entry.fetch('name') == name }
  raise "Missing or duplicate Meson test: #{name}" unless entries.size == 1
  entry = entries.first
  raise "Test contract changed: #{name}" unless entry.fetch('cmd') == [input] && entry.fetch('env').empty? &&
    entry['workdir'].nil? && entry.fetch('protocol') == 'exitcode' && entry.fetch('timeout') == 30 &&
    entry.fetch('extra_paths').empty?
  header = inspect_elf(reader, '-hW', input)
  segments = inspect_elf(reader, '-lW', input)
  dynamic = inspect_elf(reader, '-dW', input)
  raise "Wrong test ABI: #{name}" unless header.match?(/Class:\s+ELF64/) && header.match?(/Machine:\s+AArch64/)
  raise "Wrong interpreter: #{name}" unless segments.include?('[Requesting program interpreter: /libexec/ld.elf_so]')
  needed = dynamic.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.sort
  raise "Unexpected dependency: #{name}: #{needed.inspect}" unless needed == %w[libc.so.12 libpthread.so.1]
  metadata[name] = header + segments + dynamic
  needed.each do |library|
    relative = %w[/lib /usr/lib].map { |dir| dir + '/' + library }.find { |p| File.file?(sysroot + p) }
    raise "Missing base library: #{library}" unless relative
    base_paths[relative] = Digest::SHA256.file(sysroot + relative).hexdigest
  end
end
base_paths['/libexec/ld.elf_so'] = Digest::SHA256.file(sysroot + '/libexec/ld.elf_so').hexdigest
base_paths.each_key do |relative|
  header = inspect_elf(reader, '-hW', sysroot + relative)
  raise "Wrong base ABI: #{relative}" unless header.match?(/Class:\s+ELF64/) && header.match?(/Machine:\s+AArch64/)
end

# Reserve each result with exclusive creation. A second writer cannot overwrite it.
owned = []
begin
  Dir.mkdir(output, 0o700)
  owned << output
  %w[bin metadata source].each { |name| Dir.mkdir(File.join(output, name), 0o700) }
  names.each do |name|
    FileUtils.copy_file(File.join(build, name), File.join(output, 'bin', name), true)
    FileUtils.copy_file(File.join(source, 'src/libsystemd/sd-bus', name + '.c'), File.join(output, 'source', name + '.c'))
    File.write(File.join(output, 'metadata', name + '.elf'), metadata.fetch(name))
  end
  FileUtils.copy_file(File.join(__dir__, 'target-run.sh'), File.join(output, 'run.sh'))
  FileUtils.copy_file(File.join(__dir__, 'target-README.md'), File.join(output, 'README.md'))
  FileUtils.copy_file(File.join(source, 'LICENSE.LGPL2.1'), File.join(output, 'LICENSE.LGPL2.1'))
  FileUtils.copy_file(File.join(source, 'src/test/meson.build'), File.join(output, 'source/test-meson.build'))
  %w[intro-tests.json intro-projectinfo.json intro-compilers.json].each do |file|
    FileUtils.copy_file(File.join(build, 'meson-info', file), File.join(output, 'metadata', file))
  end
  FileUtils.copy_file(File.join(build, 'compile_commands.json'), File.join(output, 'metadata/compile_commands.json'))
  commands = JSON.parse(File.read(File.join(build, 'compile_commands.json')))
  files = commands.map { |entry| File.expand_path(entry.fetch('file'), entry.fetch('directory')) }.uniq.sort
  File.write(File.join(output, 'metadata/compiled-source.sha256'), files.map { |file|
    "#{Digest::SHA256.file(file).hexdigest}  #{file.delete_prefix(source + '/')}\n"
  }.join)
  File.write(File.join(output, 'metadata/base.sha256'), base_paths.sort.map { |path, hash| "#{hash}  #{path}\n" }.join)
  File.write(File.join(output, 'metadata/selection.txt'), "basu 0.2.1; EmberBSD Ports package revision 2\n#{names.join("\n")}\nPrepared only. Target execution and Valgrind are pending.\n")
  payload = Dir.glob(File.join(output, '**/*')).select { |file| File.file?(file) }.sort
  File.write(File.join(output, 'SHA256SUMS'), payload.map { |file|
    "#{Digest::SHA256.file(file).hexdigest}  #{file.delete_prefix(output + '/')}\n"
  }.join)
  File.open(archive, File::WRONLY | File::CREAT | File::EXCL, 0o600) do |archive_file|
    owned << archive
    raise 'Archive creation failed' unless system('/usr/bin/tar', '-czf', '-', '-C', output, '.', out: archive_file)
  end
  File.open(checksum, File::WRONLY | File::CREAT | File::EXCL, 0o600) do |file|
    owned << checksum
    file.puts Digest::SHA256.file(archive).hexdigest
  end
  owned.clear
  puts "PREPARED: #{names.size} unchanged upstream local unit tests; target execution pending"
ensure
  owned.reverse_each { |path| File.directory?(path) ? FileUtils.remove_entry(path) : File.unlink(path) }
end
