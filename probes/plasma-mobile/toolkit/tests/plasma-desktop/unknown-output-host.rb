#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). This runs the actual shell control, not Plasma.
require 'fileutils'
require 'open3'
require 'rbconfig'
require 'tmpdir'

source = File.read(File.join(__dir__, 'session.sh'))
start_marker = '# This internal API must reject an unknown connector; it must not save a file.'
end_marker = '# Layout models can precede a visible Quick item.'
section = lambda do |text|
  start = text.index(start_marker) or abort 'Missing unknown-output control'
  finish = text.index(end_marker, start) or abort 'Missing capture boundary'
  text[start...finish]
end
body = section.call(source)
function = source[/^check_missing_images\(\)\n\{.*?^\}/m] or abort 'Missing image check'
abort 'Late image checks are missing' unless source.scan(/^\s*check_missing_images(?: \|\| result=1)?$/).size >= 6
baseline, status = Open3.capture2e('git', '-C', __dir__, 'show',
  '201a136c5ab3b09def8de0d31453337e6f9bb31c:probes/plasma-mobile/toolkit/tests/plasma-desktop/session.sh')
abort 'Missing causal baseline' unless status.success?
checks = 0
Dir.mktmpdir('ember-unknown-output-', '/tmp') do |root|
  execute = lambda do |name, mode, candidate, baseline_case = false|
    work = File.join(root, name)
    FileUtils.mkdir(work)
    File.write(File.join(work, 'date'), <<~RUBY)
      #!#{RbConfig.ruby}
      count = File.file?('clock-count') ? File.read('clock-count').to_i : 0
      File.write('clock-count', (count + 1).to_s)
      puts [80, 88, 90][[count, 2].min]
    RUBY
    File.write(File.join(work, 'sleep'), "#!/bin/sh\nexit 0\n")
    File.write(File.join(work, 'timeout'), <<~'SH')
      #!/bin/sh
      printf '%s\n' "$3" >> durations
      shift 3
      exec "$@"
    SH
    File.write(File.join(work, 'qdbus'), <<~RUBY)
      #!#{RbConfig.ruby}
      expected = ['org.kde.plasmashell', '/PlasmaShell',
        'org.kde.PlasmaShell.grabContainmentImage', 'Ember-Missing-Output', '320', '256']
      abort 'Wrong probe arguments' unless ARGV[0, 6] == expected
      count = File.file?('calls') ? File.read('calls').to_i + 1 : 1
      File.write('calls', count.to_s)
      File.open('paths', 'a') { |f| f.puts(ARGV.fetch(6)) }
      mode = #{mode.inspect}
      exit 124 if mode == 'timeout' || (%w[delayed late-image].include?(mode) && count == 1)
      exit 0 if mode == 'success'
      exit 139 if mode == 'crash'
      if mode == 'image'
        File.write(ARGV.fetch(6), 'invalid image')
      elsif mode == 'symlink'
        File.symlink('absent', ARGV.fetch(6))
      elsif mode == 'late-image'
        File.write(File.readlines('paths').first.strip, 'late image')
      end
      puts "Error: org.freedesktop.DBus.Error.InvalidArgs\n" +
        (mode == 'wrong-error' ? 'Other error' : 'Unknown screen name')
      exit(mode == 'wrong-status' ? 1 : 2)
    RUBY
    %w[date sleep timeout qdbus].each { |name| File.chmod(0o700, File.join(work, name)) }
    block = candidate.gsub('/usr/bin/timeout', "#{work}/timeout")
                     .gsub('/usr/pkg/qt6/bin/qdbus', "#{work}/qdbus")
    fixture = "#!/bin/sh\nset -eu\ncd #{work}\ndeadline=90\nplasma_pid=$$\n#{function}\n"
    fixture += "query() { #{work}/timeout -k 2 5 #{work}/qdbus \"$@\"; }\n"
    fixture += block
    fixture += "touch missing-output-1.png\n" if mode == 'final-image'
    fixture += "check_missing_images\n" unless baseline_case
    fixture += "echo 'PASS: strict unknown-output rejection'\n"
    File.write(File.join(work, 'fixture.sh'), fixture)
    output, result = Open3.capture2e({'PATH' => "#{work}:#{ENV.fetch('PATH')}"}, '/bin/sh', File.join(work, 'fixture.sh'))
    {work: work, output: output, status: result.exitstatus}
  end
  controls = %w[ready delayed timeout success wrong-status wrong-error crash image symlink late-image final-image]
  controls.each do |mode|
    result = execute.call(mode, mode, body)
    accepted = %w[ready delayed].include?(mode)
    abort "Incorrect #{mode} result: #{result.inspect}" unless (result[:status] == 0) == accepted
    abort "Wrong success evidence for #{mode}" if accepted && !result[:output].include?('PASS: strict unknown-output rejection')
    if %w[delayed timeout].include?(mode)
      durations = File.readlines(File.join(result[:work], 'durations')).map(&:to_i)
      abort 'The original deadline was extended' unless durations == [5, 2]
      paths = File.readlines(File.join(result[:work], 'paths')).map(&:strip)
      abort 'Retry paths were reused' unless paths.uniq.size == 2 && paths.size == 2
      statuses = [1, 2].map { |n| File.read(File.join(result[:work], "missing-output-#{n}.status")).to_i }
      abort 'Statuses were not retained' unless statuses == [124, mode == 'timeout' ? 124 : 2]
      abort 'Per-attempt logs are missing' unless [1, 2].all? { |n| File.file?(File.join(result[:work], "missing-output-#{n}.log")) }
    end
    abort 'Persistent timeout lacked the deadline diagnostic' if mode == 'timeout' && !result[:output].include?('before the startup deadline')
    checks += 1
  end
  old = execute.call('baseline-delayed', 'delayed', section.call(baseline), true)
  abort 'The old one-shot control did not reproduce the startup failure' unless old[:status] == 1 && File.read(File.join(old[:work], 'calls')).to_i == 1
  checks += 1
  # The same cases must reject weakened retry, deadline, status and image gates.
  mutants = {
    'no-retry' => ['delayed', body.sub("    124)\n        sleep 1 ;;", "    124)\n        exit 1 ;;")],
    'reset-deadline' => ['delayed', body.sub('    remaining=$((deadline - $(date +%s)))', "    deadline=100\n    remaining=$((deadline - $(date +%s)))")],
    'accept-wrong-status' => ['wrong-status', body.sub("    2)\n", "    2|1)\n")],
    'ignore-image' => ['image', body.gsub(/^    check_missing_images\n/, '')]
  }
  mutants.each do |name, (mode, changed)|
    abort "Mutant #{name} did not change the source" if changed == body
    result = execute.call("mutant-#{name}", mode, changed)
    killed = case name
             when 'no-retry' then result[:status] != 0
             when 'reset-deadline' then File.readlines(File.join(result[:work], 'durations')).map(&:to_i) != [5, 2]
             when 'accept-wrong-status' then result[:status] == 0
             when 'ignore-image' then !result[:output].include?('unknown output created an image') || File.file?(File.join(result[:work], 'missing-output.log'))
             end
    abort "Mutant #{name} survived" unless killed
    checks += 1
  end
end
puts "PASS: #{checks} unknown-output host controls; causal baseline rejected; no target execution"
