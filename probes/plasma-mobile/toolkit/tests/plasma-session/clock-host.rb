#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual harness blocks with modeled clock steps.
require 'digest'
require 'fileutils'
require 'open3'
require 'rbconfig'
require 'tmpdir'

source = File.expand_path(ARGV.fetch(0, __dir__))
inputs = %w[controller.sh run.sh guard.pl clock-host.rb]
pins = inputs.to_h { |name| [name, Digest::SHA256.file("#{source}/#{name}").hexdigest] }
controller = File.read("#{source}/controller.sh")
runner = File.read("#{source}/run.sh")
guard = File.read("#{source}/guard.pl")
baseline = 'fbd7eb6ff5703d1e99dedcf191d322f7c153bc7c'
root, status = Open3.capture2('git', '-C', source, 'rev-parse', '--show-toplevel')
abort 'Cannot find the Ports source' unless status.success?
relative = source.delete_prefix(root.strip + '/')
old = lambda do |name|
  text, status = Open3.capture2('git', '-C', root.strip, 'show', "#{baseline}:#{relative}/#{name}")
  abort "Cannot read baseline #{name}" unless status.success?
  text
end
checks = 0
assert = lambda do |condition, message|
  abort message unless condition
  checks += 1
end
extract = lambda do |text, pattern, message|
  text[pattern] or abort message
end
clock = extract.call(controller, /^monotonic_seconds\(\)\n\{\n.*?^\}\n/m, 'Missing actual monotonic clock function')
perl = ENV.fetch('PERL', 'perl')
out, status = Open3.capture2e('/bin/sh', '-c', clock.gsub('/usr/pkg/bin/perl', perl) + "monotonic_seconds\nmonotonic_seconds\n")
times = out.lines.map(&:strip)
assert.call(status.success? && times.length == 2 && times.all? { |value| value.match?(/^\d+$/) } &&
            times[0].to_i.positive? && times[1].to_i >= times[0].to_i, 'Actual CLOCK_MONOTONIC helper failed')
assert.call(controller.scan('$(date +%s)').length == 2, 'Civil time escaped the two query timestamp sites')
assert.call(controller.scan(/^deadline=/).length == 2, 'Readiness must share its original startup deadline')
assert.call(controller.include?('deadline=$(($(monotonic_seconds) + 100))') &&
            controller.include?('deadline=$(($(monotonic_seconds) + 45))'), 'Deadline budgets changed')
assert.call(runner.scan('./guard.pl "$work" 240 --').length == 1 &&
            runner.index('[ ! -e "$work" ] && [ ! -L "$work" ]') < runner.index('mkdir "$work"') &&
            runner.index('/usr/pkg/bin/perl ./guard.pl') < runner.index('/sbin/sysctl kern.boottime > boot.after'),
            'Same-boot evidence must come from one uninterrupted non-resumable runner/guard chain')
assert.call(guard.include?('waitpid($pid, WNOHANG)') && guard.include?('while (poll_child())'),
            'Guard no longer waits for its original child')
assert.call(controller[/^query\(\)\n\{\n.*?^\}\n/m] == old.call('controller.sh')[/^query\(\)\n\{\n.*?^\}\n/m],
            'UTC query timestamps or query status handling changed')

Dir.mktmpdir('plasma-clock-', ENV.fetch('TMPDIR', '/tmp')) do |temp|
  clock_service = "#{temp}/clock"
  File.write(clock_service, <<~'SH')
    #!/bin/sh
    [ "$#" = 3 ] && [ "$1" = '-MTime::HiRes=clock_gettime,CLOCK_MONOTONIC' ] &&
        [ "$2" = -e ] && [ "$3" = 'printf "%d\n", clock_gettime(CLOCK_MONOTONIC)' ] || exit 99
    read -r ticks < tick
    echo $((1000 + ticks))
  SH
  File.chmod(0o700, clock_service)
  blocks = lambda do |text|
    initial = extract.call(text, /^deadline=[^\n]*\+ 100\)\)\n/, 'Missing startup deadline')
    display = extract.call(text, /^while :; do\n.*?^done\n/m, 'Missing display loop')
    startup = extract.call(text, /^phase=startup-readiness\nwhile ! ready.*?^done\n/m, 'Missing readiness loop')
    logout = extract.call(text, /^deadline=[^\n]*\+ 45\)\)\nwhile kill -0.*?^done\n/m, 'Missing logout loop')
    {'display'=>[initial + display, 100], 'readiness'=>[initial + startup, 100], 'logout'=>[logout, 45]}
  end
  [[controller, false], [old.call('controller.sh'), true]].each do |text, is_old|
    blocks.call(text).each do |phase, (body, budget)|
      # The model advances monotonic seconds once per sleep. Civil time steps
      # independently after the first sleep. Limit iterations to detect overruns.
      cases = [[579, 3], [-579, 3], [-579, nil], [0, nil], [0, budget]]
      cases.each_with_index do |(step, ready_after), index|
        directory = "#{temp}/#{is_old ? 'old' : 'new'}-#{phase}-#{index}"
        Dir.mkdir(directory)
        File.write("#{directory}/tick", '0')
        File.write("#{directory}/display-env", 'fixture')
        expected = if is_old && step.positive?
          1
        elsif is_old && step.negative? && !ready_after
          97
        else
          ready_after ? 0 : 1
        end
        fixture = <<~SH
          #!/bin/sh
          set -eu
          cd '#{directory}'
          wrapper=$$
          plasma=$$
          iteration=0
          ready() { [ "$iteration" -ge #{ready_after || budget + 2} ]; }
          owner() { ready && printf '%s\\n' "$wrapper"; }
          kill() { #{phase == 'logout' ? '! ready' : 'return 0'}; }
          date() {
              [ "$1" = +%s ] || exit 98
              if [ "$iteration" -eq 0 ]; then echo 1000; else echo $((1000 + iteration + #{step})); fi
          }
          sleep() {
              [ "$1" = 1 ] || exit 98
              iteration=$((iteration + 1))
              printf '%s\\n' "$iteration" > tick
              [ "$iteration" -le #{budget + 1} ] || exit 97
          }
        SH
        fixture += clock.gsub('/usr/pkg/bin/perl', clock_service) unless is_old
        fixture += body + "printf '%s\\n' \"$iteration\" > reached\n"
        File.write("#{directory}/test.sh", fixture)
        out, status = Open3.capture2e('/bin/sh', "#{directory}/test.sh")
        assert.call(status.exitstatus == expected, "#{phase} #{step}/#{ready_after.inspect} old=#{is_old}: expected #{expected}, got #{status.exitstatus}: #{out}")
        iterations = File.read("#{directory}/tick").to_i
        wanted = if is_old && step.positive? then 1
                 elsif is_old && step.negative? && !ready_after then budget + 2
                 else ready_after || budget
                 end
        assert.call(iterations == wanted, "#{phase}: wrong expiry/readiness iteration #{iterations}, expected #{wanted}")
      end
    end
  end

  # Execute the actual post-guard block. A completed guard status remains
  # mandatory; only the civil boot-time comparison becomes diagnostic context.
  [[runner, false], [old.call('run.sh'), true]].each do |text, is_old|
    start = text.index("printf '%s\\n' \"$status\" > status\n") or abort 'Missing post-guard start'
    finish = text.index('[ -f logout.requested ]', start) or abort 'Missing logout proof'
    block = text[start...finish] + "[ -f logout.requested ]\n"
    cases = [
      {changed: false}, {changed: true}, {changed: true, child: 124},
      {child: 124}, {guard: 124}, {controller: 1}, {wrapper: 1}, {plasma: 1}
    ]
    unless is_old
      %i[child guard controller wrapper plasma].each do |name|
        cases << {name=>nil}
        cases << {name=>''}
      end
    end
    cases.each_with_index do |test, index|
      test = {changed: false, child: 0, guard: 0, controller: 0, wrapper: 0, plasma: 0}.merge(test)
      changed, child_status = test.values_at(:changed, :child)
      directory = "#{temp}/boot-#{is_old ? 'old' : 'new'}-#{index}"
      Dir.mkdir(directory)
      File.write("#{directory}/boot.before", "kern.boottime = 1000\n")
      File.write("#{directory}/bus.log", "fixture session completed\n")
      {guard: 'guard.status', controller: 'controller.status', wrapper: 'wrapper.status', plasma: 'startplasma.status'}.each do |key, name|
        File.write("#{directory}/#{name}", "#{test[key]}\n") unless test[key].nil?
      end
      File.write("#{directory}/logout.requested", '')
      sysctl = "#{directory}/sysctl"
      File.write(sysctl, "#!/bin/sh\n[ \"$1\" = kern.boottime ] || exit 99\necho 'kern.boottime = #{changed ? 1579 : 1000}'\n")
      File.chmod(0o700, sysctl)
      script = "#{directory}/test.sh"
      assignment = child_status.nil? ? '' : "status='#{child_status}'\n"
      File.write(script, "#!/bin/sh\nset -eu\ncd '#{directory}'\n" + assignment + block.gsub('/sbin/sysctl', sysctl))
      out, status = Open3.capture2e('/bin/sh', script)
      expected = if is_old
                   changed || test[:controller] != 0 || test[:plasma] != 0 ? 1 : 0
                 else test.except(:changed).values.all? { |value| value == 0 } ? 0 : 1
                 end
      assert.call(expected.zero? ? status.success? : !status.success?, "boot #{test.inspect} old=#{is_old}: expected #{expected}, got #{status.exitstatus}: #{out}")
      if child_status.nil?
        assert.call(!File.exist?("#{directory}/boot.after"), 'Unset guard status did not fail before recording completion')
      else
        assert.call(File.read("#{directory}/boot.after") == "kern.boottime = #{changed ? 1579 : 1000}\n", 'Civil boot context is missing')
      end
      unless is_old || child_status.nil?
        assert.call(File.read("#{directory}/boot-time-change.txt").strip == (changed ? 'changed' : 'unchanged'), 'Civil boot change was not recorded')
      end
    end
  end
  # Civil query timestamps remain diagnostic evidence. A step can put the end
  # before the start; neither ordering changes the actual query return status.
  query = extract.call(controller, /^query\(\)\n\{\n.*?^\}\n/m, 'Missing actual query function')
  [-579, 579].product([0, 124]).each_with_index do |(step, result), index|
    directory = "#{temp}/query-#{index}"
    Dir.mkdir(directory)
    date = "#{directory}/date"
    File.write(date, "#!/bin/sh\n[ \"$1\" = +%s ] || exit 99\nif [ -f queried ]; then echo #{1000 + step}; else echo 1000; fi\n: > queried\n")
    timeout = "#{directory}/timeout"
    File.write(timeout, "#!/bin/sh\n[ \"$1\" = -k ] && [ \"$2\" = 2 ] && [ \"$3\" = 5 ] || exit 99\nexit #{result}\n")
    [date, timeout].each { |path| File.chmod(0o700, path) }
    script = "#{directory}/test.sh"
    File.write(script, "#!/bin/sh\nset -eu\ncd '#{directory}'\nphase=fixture\n" +
      query.gsub('/usr/bin/timeout', timeout) + "query service /object method > /dev/null\n")
    out, status = Open3.capture2e({'PATH'=>"#{directory}:#{ENV.fetch('PATH')}"}, '/bin/sh', script)
    assert.call(status.exitstatus == result, "Clock step changed query status: #{out}")
    rows = File.readlines("#{directory}/queries.tsv", chomp: true).map { |line| line.split("\t", -1) }
    assert.call(rows == [['1000', (1000 + step).to_s, 'fixture', result.to_s, 'service', '/object', 'method']],
                'Clock step or query status disappeared from diagnostic evidence')
  end
end
assert.call(inputs.all? { |name| Digest::SHA256.file("#{source}/#{name}").hexdigest == pins[name] }, 'Harness inputs changed during the regression')
puts "PASS: #{checks} clock and same-boot controls; baseline false failures and overrun reproduced; no target runtime executed"
