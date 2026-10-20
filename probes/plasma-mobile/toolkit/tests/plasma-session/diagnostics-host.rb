#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual runner blocks with explicit bus fixtures.
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'tmpdir'

source = File.expand_path(__dir__)
root, status = Open3.capture2('git', '-C', source, 'rev-parse', '--show-toplevel')
abort 'Cannot find the Ports source' unless status.success?
root = root.strip
relative = source.delete_prefix(root + '/')
baseline = 'a087d5ad763b736aa12aca98cdd3adde17fc2c4a'
old = lambda do |name|
  text, status = Open3.capture2('git', '-C', root, 'show', "#{baseline}:#{relative}/#{name}")
  abort "Cannot read baseline #{name}" unless status.success?
  text
end
runner = File.read("#{source}/run.sh")
controller = File.read("#{source}/controller.sh")
perl = ENV.fetch('PERL', 'perl')
checks = 0
assert = lambda do |condition, message|
  abort message unless condition
  checks += 1
end
executable = lambda do |path, text|
  File.write(path, text)
  File.chmod(0o700, path)
end
Dir.mktmpdir('plasma-session-diagnostics-') do |temp|
  timeout = "#{temp}/timeout"
  executable.call(timeout, <<~SH)
    #!/bin/sh
    [ "$1" = -k ] && [ "$2" = 2 ] && [ "$3" = 5 ] || exit 99
    shift 3
    exec "$@"
  SH
  # Execute the unchanged prerequisite boundary, before simulated output/launch.
  [[runner, false], [old.call('run.sh'), true]].each do |text, is_old|
    a = text.index('[ -x /usr/pkg/qt6/bin/qdbus ]') or abort 'Missing prerequisite start'
    b = text.index('[ -x /usr/pkg/libexec/kactivitymanagerd ]') or abort 'Missing prerequisite end'
    assert.call(a < b && b < text.index('mkdir "$work"'), 'System bus check must precede output creation')
    cases = is_old ? [['absent', 1, '', 0]] : [
      ['ready', 0, '0123456789abcdef0123456789abcdef', 0],
      ['absent', 1, '', 2], ['timeout', 124, '', 2],
      ['empty', 0, '', 2], ['invalid', 0, 'not-a-bus-id', 2],
      ['long', 0, '0' * 33, 2], ['two-lines', 0, ('0' * 32) + "\n" + ('1' * 32), 2]
    ]
    cases.each do |name, query_status, reply, expected|
      directory = "#{temp}/#{is_old ? 'old' : 'new'}-#{name}"
      Dir.mkdir(directory)
      qdbus = "#{directory}/qdbus"
      executable.call(qdbus, <<~SCRIPT)
        #!#{RbConfig.ruby}
        require 'json'
        expected = ['--system', 'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus.GetId']
        abort 'Unexpected bus call' unless ARGV == expected
        abort 'Inherited bus override' if ENV.key?('DBUS_SYSTEM_BUS_ADDRESS') || ENV.key?('LD_LIBRARY_PATH')
        File.write(#{"#{directory}/call.json".inspect}, JSON.generate(ARGV))
        puts #{reply.inspect}
        warn 'fixture: system bus unavailable' if #{query_status} != 0
        exit #{query_status}
      SCRIPT
      block = text[a...b].gsub('/usr/pkg/bin/perl', perl).gsub('/usr/bin/timeout', timeout).gsub('/usr/pkg/qt6/bin/qdbus', qdbus)
      script = "#{directory}/run.sh"
      File.write(script, "#!/bin/sh\nset -eu\n" + block + "mkdir '#{directory}/output'\n: > '#{directory}/launched'\n")
      out, status = Open3.capture2e({'DBUS_SYSTEM_BUS_ADDRESS'=>'invalid:', 'LD_LIBRARY_PATH'=>'/invalid'}, '/bin/sh', script)
      assert.call(status.exitstatus == expected, "#{name}: expected #{expected}, got #{status.exitstatus}: #{out}")
      assert.call(File.directory?("#{directory}/output") == (expected == 0), "#{name}: incorrect output creation")
      assert.call(File.file?("#{directory}/launched") == (expected == 0), "#{name}: incorrect launch boundary")
      assert.call(File.file?("#{directory}/call.json") != is_old, "#{name}: incorrect bus call count")
      if query_status != 0 && !is_old
        assert.call(out.include?("system-bus preflight status=#{query_status}"), "#{name}: original bus status is missing")
      end
    end
  end
  # Preserve the real query + ready functions, including redirections and returns.
  [[controller, false], [old.call('controller.sh'), true]].each do |text, is_old|
    prefix = text.split("owner()\n", 2).first
    ready = text[/^ready\(\)\n\{\n.*?^\}\n/m] or abort 'Missing actual ready function'
    cases = is_old ? [[124, '', 1]] : [[0, 'org.kde.plasma.desktop', 0], [124, '', 124], [2, '', 2], [137, '', 137], [0, '', 1]]
    cases.each_with_index do |(query_status, reply, expected), index|
      directory = "#{temp}/query-#{is_old ? 'old' : 'new'}-#{index}"
      Dir.mkdir(directory)
      File.write("#{directory}/layout.js", 'fixture layout')
      %w[bus.log compositor.log plasma-session.log].each { |name| File.write("#{directory}/#{name}", '') }
      qdbus = "#{directory}/qdbus"
      executable.call(qdbus, <<~SCRIPT)
        #!#{RbConfig.ruby}
        case ARGV[2]
        when 'org.kde.KSMServerInterface.isShuttingDown' then puts 'false'
        when 'org.kde.KSMServerInterface.currentSession' then puts 'default'
        when 'org.kde.ActivityManager.Activities.CurrentActivity', 'org.kde.ActivityManager.Activities.ListActivities'
          puts '12345678-1234-1234-1234-123456789abc'
        when 'org.freedesktop.DBus.Properties.Get'
          abort 'Invalid property call' unless ARGV == ['org.kde.plasmashell', '/PlasmaShell', 'org.freedesktop.DBus.Properties.Get', 'org.kde.PlasmaShell', 'shell']
          puts #{reply.inspect} unless #{reply.empty?}
          warn 'fixture: property failure' if #{query_status} != 0
          exit #{query_status}
        when 'org.kde.PlasmaShell.evaluateScript'
          puts 'PASS: default desktop, panel and six applet models on 1280x1024'
        else abort 'Unexpected query'
        end
      SCRIPT
      script = "#{directory}/controller.sh"
      body = (prefix + ready + "phase=liveness-1\nready\n").gsub('/usr/pkg/bin/perl', perl).gsub('/usr/bin/timeout', timeout).gsub('/usr/pkg/qt6/bin/qdbus', qdbus)
      File.write(script, body)
      out, status = Open3.capture2e({'EMBER_PLASMA_OUTPUT'=>directory, 'EMBER_PLASMA_SESSION_MARKER'=>'fixture'}, '/bin/sh', script)
      assert.call(status.exitstatus == expected, "query #{index}: expected #{expected}, got #{status.exitstatus}: #{out}")
      assert.call(File.read("#{directory}/controller.status").strip == expected.to_s, 'Controller status differs from process status')
      if is_old
        assert.call(!File.exist?("#{directory}/queries.tsv"), 'Baseline unexpectedly has query evidence')
      else
        rows = File.readlines("#{directory}/queries.tsv", chomp: true).map { |line| line.split("\t", -1) }
        assert.call(rows.all? { |row| row.length == 7 && row[0].match?(/^\d+$/) && row[1].to_i >= row[0].to_i && row[2] == 'liveness-1' }, 'Invalid query evidence')
        row = rows.find { |entry| entry[6] == 'org.freedesktop.DBus.Properties.Get' }
        assert.call(row && row[3] == query_status.to_s && row[4..5] == ['org.kde.plasmashell', '/PlasmaShell'], 'Original property status is missing')
        assert.call(rows.none? { |row| row.join.include?('fixture layout') }, 'Query evidence copied its payload')
        assert.call(out.include?("controller phase=liveness-1 status=#{expected}"), 'Controller phase is missing') unless expected == 0
        assert.call(out.include?("query phase=liveness-1 status=#{query_status}"), 'Query failure status is missing') unless query_status == 0
      end
    end
  end
end
puts "PASS: #{checks} system-bus and query diagnostics controls; baseline failures reproduced"
