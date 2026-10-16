#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute actual serialized pkgsrc helpers.
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: package-lifecycle.rb XWAYLAND_ARCHIVE NEW_OUTPUT' unless ARGV.length == 2
archive, output = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(output)
def run!(*command, **options)
  out, err, status = Open3.capture3(*command, **options)
  raise "Command failed: #{command.inspect}\n#{out}#{err}" unless status.success?
  [out, err]
end
begin
  metadata = "#{output}/pkgdb/xwayland-test"
  prefix = "#{output}/prefix"
  FileUtils.mkdir_p([metadata, prefix])
  %w[+INSTALL +DEINSTALL].each do |name|
    script = run!('tar', '-xOf', archive, name).first
    raise 'Host path in target script' if script.match?(%r{/(?:Volumes|Users|private/tmp|opt/homebrew)/})
    raise 'Non-target script shell' unless script.start_with?("#!/bin/sh\n")
    raise 'Non-target sort' unless script.scan(/^SORT="([^"]+)"$/).flatten.uniq == ['/usr/bin/sort']
    File.write("#{metadata}/#{name}", script)
    run!('/bin/sh', '-n', "#{metadata}/#{name}")
  end
  env = {'PKG_PREFIX'=>prefix, 'PKG_METADATA_DIR'=>metadata, 'PKG_REFCOUNT_DBDIR'=>"#{output}/refcount", 'LC_ALL'=>'C', 'PKG_RCD_SCRIPTS'=>nil}
  run!(env, '/bin/sh', './+INSTALL', 'xwayland-test', 'UNPACK', '+FILES', chdir: metadata)
  path = "#{metadata}/+FILES"
  source = File.read(path)
  records = source.lines.grep(/^# FILE: /)
  expected = "# FILE: /etc/rc.d/x11_runtime cr share/examples/rc.d/x11_runtime 0755\n"
  raise "Unexpected managed file records: #{records.inspect}" unless records == [expected]
  # Keep the generated helper unchanged. Scope only its one data record to
  # the private prefix so no host /etc path can be changed by this test.
  File.write(path, source.sub(expected, expected.sub('/etc/', 'etc/')))
  sample = "#{prefix}/share/examples/rc.d/x11_runtime"
  dest = "#{prefix}/etc/rc.d/x11_runtime"
  FileUtils.mkdir_p([File.dirname(sample), File.dirname(dest)])
  File.write(sample, run!('tar', '-xOf', archive, 'share/examples/rc.d/x11_runtime').first)
  invoke = lambda do |action, enabled|
    out, err = run!(env.merge('PKG_RCD_SCRIPTS'=>enabled), '/bin/sh', './+FILES', action, metadata, chdir: metadata)
    File.open("#{output}/lifecycle.log", 'a') { |f| f.write("#{action} PKG_RCD_SCRIPTS=#{enabled.inspect}\n#{out}#{err}") }
    raise "Helper diagnostic: #{err}" unless err.empty?
  end
  invoke.call('ADD', nil)
  raise 'Default unexpectedly installed service' if File.exist?(dest)
  2.times do |cycle|
    %w[ADD PERMS CHECK-ADD CHECK-PERMS].each { |action| invoke.call(action, 'yes') }
    raise 'Service copy differs' unless File.binread(dest) == File.binread(sample)
    raise 'Wrong service mode' unless File.stat(dest).mode & 0o7777 == 0o755
    invoke.call('ADD', 'yes')
    raise 'Repeated ADD changed service' unless File.binread(dest) == File.binread(sample)
    File.open(dest, 'a') { |f| f.puts '# local change' } if cycle == 1
    invoke.call('REMOVE', 'yes')
    if cycle.zero?
      raise 'Unmodified service survived deinstall' if File.exist?(dest)
    else
      raise 'Modified service was removed' unless File.read(dest).end_with?("# local change\n")
    end
  end
  File.write("#{output}/archive.sha256", "#{Digest::SHA256.file(archive).hexdigest}  #{File.basename(archive)}\n")
  puts 'PASS: actual generated script tools, default disabled, explicit activation, repeat install and deinstall preservation'
rescue StandardError => error
  warn error.message
  exit 1
end
