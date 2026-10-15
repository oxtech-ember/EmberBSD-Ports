#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check serialized attr install helpers.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: cross-install-scripts.rb ATTR_ARCHIVE NEW_OUTPUT' unless ARGV.length == 2
archive, output = ARGV.map { |path| File.expand_path(path) }
File.umask(0o077)
Dir.mkdir(output)
tar = ENV.fetch('BSDTAR', 'tar')
def run!(*command, **options)
  out, err, status = Open3.capture3(*command, **options)
  raise "Failed #{command.inspect}\n#{out}#{err}" unless status.success?
  [out, err]
end
def target_script!(path)
  source = File.read(path)
  raise "Host path in #{path}" if source.match?(%r{/(?:Volumes|Users|private/tmp|opt/homebrew)/})
  sorts = source.scan(/^SORT="([^"]*)"$/).flatten
  raise "Missing target sort in #{path}" unless !sorts.empty? && sorts.all? { |sort| sort == '/usr/bin/sort' }
  source.scan(/^[A-Z_]+="([^"\n]*)"$/).flatten.each do |value|
    executable = Shellwords.split(value).first
    next unless executable&.start_with?('/')
    unless executable.match?(%r{\A/(?:bin|sbin|usr/bin|usr/sbin|usr/pkg)/})
      raise "Non-target absolute value in #{path}: #{value}"
    end
  end
end
begin
  contents = run!(tar, '-xOf', archive, '+CONTENTS').first
  package = contents[/^@name (attr-\S+)$/, 1] or raise 'Expected an attr package'
  raise 'Unexpected package prefix' unless contents.include?("@cwd /usr/pkg\n")
  metadata = File.join(output, 'pkgdb', package)
  prefix = File.join(output, 'prefix')
  FileUtils.mkdir_p([metadata, prefix])
  %w[+INSTALL +DEINSTALL].each do |name|
    script = run!(tar, '-xOf', archive, name).first
    path = File.join(metadata, name)
    File.write(path, script)
    target_script!(path)
    run!('/bin/sh', '-n', path)
  end
  # Do not rewrite serialized scripts. PKG_PREFIX is their normal interface.
  env = { 'PKG_PREFIX' => prefix, 'PKG_METADATA_DIR' => metadata,
          'PKG_REFCOUNT_DBDIR' => File.join(output, 'refcount'), 'LC_ALL' => 'C' }
  run!(env, '/bin/sh', './+INSTALL', package, 'UNPACK', '+DIRS', chdir: metadata)
  run!(env, '/bin/sh', './+INSTALL', package, 'UNPACK', '+FILES', chdir: metadata)
  %w[+DIRS +FILES].each { |name| target_script!(File.join(metadata, name)) }
  dirs = File.readlines(File.join(metadata, '+DIRS')).grep(/^# DIR: /).map { |line| line.delete_prefix('# DIR: ').split }
  files = File.readlines(File.join(metadata, '+FILES')).grep(/^# FILE: /).map { |line| line.delete_prefix('# FILE: ').split }
  # Restrict this host execution to the known fixture's relative, unprivileged data.
  raise "Unexpected directory records: #{dirs.inspect}" unless dirs == [['etc', 'm']]
  raise "Unexpected configuration records: #{files.inspect}" unless files == [['etc/xattr.conf', 'c', 'share/examples/attr/xattr.conf', '0644']]
  sample = File.join(prefix, files[0][2])
  destination = File.join(prefix, files[0][0])
  FileUtils.mkdir_p(File.dirname(sample))
  File.binwrite(sample, run!(tar, '-xOf', archive, files[0][2]).first)
  invoke = lambda do |name, action|
    out, err = run!(env, '/bin/sh', "./#{name}", action, metadata, chdir: metadata)
    File.open(File.join(output, 'lifecycle.log'), 'a') { |log| log.write("#{name} #{action}\n#{out}#{err}") }
    raise "Helper emitted an error: #{err}" unless err.empty?
  end
  2.times do |cycle|
    %w[+DIRS +FILES].each do |name|
      %w[ADD PERMS CHECK-ADD CHECK-PERMS].each { |action| invoke.call(name, action) }
    end
    raise 'Configuration was not copied' unless File.binread(destination) == File.binread(sample)
    raise 'Configuration mode differs' unless (File.stat(destination).mode & 0o777) == 0o644
    File.open(destination, 'a') { |file| file.write("# locally changed\n") } if cycle == 1
    invoke.call('+FILES', 'REMOVE')
    invoke.call('+DIRS', 'REMOVE')
    if cycle.zero?
      raise 'Unmodified configuration survived removal' if File.exist?(destination)
      raise 'Created directory survived removal' if File.exist?(File.join(prefix, 'etc'))
    else
      raise 'Modified configuration was removed' unless File.read(destination).end_with?("# locally changed\n")
    end
  end
  File.write(File.join(output, 'archive.sha256'), "#{Digest::SHA256.file(archive).hexdigest}  #{File.basename(archive)}\n")
  puts 'PASS: serialized target tools and actual directory/configuration helper lifecycle'
rescue StandardError => error
  warn error.message
  exit 1
end
