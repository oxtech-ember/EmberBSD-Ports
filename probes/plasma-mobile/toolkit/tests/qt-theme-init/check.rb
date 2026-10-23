#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No Qt build-tree or target writes.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require 'timeout'
require 'rbconfig'
Process.setrlimit(:CORE, 0, 0)
def capture(argv, seconds = 60)
  Open3.popen3(*argv, pgroup: true) do |input, output, errors, waiter|
    input.close
    readers = [Thread.new { output.read }, Thread.new { errors.read }]
    begin
      Timeout.timeout(seconds) { [readers[0].value, readers[1].value, waiter.value] }
    rescue Timeout::Error
      begin Process.kill('KILL', -waiter.pid); rescue Errno::ESRCH; end
      waiter.value
      raise 'deadline exceeded'
    ensure
      readers.each(&:join)
    end
  end
end
def function(text, signature)
  raise 'nonunique signature: ' + signature unless text.scan(signature).size == 1
  start = text.index(signature)
  brace = text.index('{', start)
  depth = 0
  (brace...text.size).each do |i|
    depth += 1 if text[i] == '{'
    depth -= 1 if text[i] == '}'
    return text[start..i] + "\n" if depth == 0
  end
  raise 'unterminated function'
end
source = File.realpath(ARGV.fetch(0))
work = File.expand_path(ARGV.fetch(1))
raise 'new evidence directory required' if File.exist?(work)
FileUtils.mkdir_p(work)
ports = File.realpath(File.expand_path('../../../../..', __dir__))
recipe = ports + '/pkgsrc/x11/qt6-qtbase'
patch = recipe + '/patches/patch-src_gui_kernel_qguiapplication.cpp-theme-init'
paths = %w[src/gui/kernel/qguiapplication.cpp src/gui/kernel/qstylehints.cpp src/gui/platform/unix/qkdetheme.cpp]
pins = paths.map { |p| [p, Digest::SHA256.file(source + '/' + p).hexdigest] }.to_h
pins['patch'] = Digest::SHA256.file(patch).hexdigest
pins['fixture'] = Digest::SHA256.file(__dir__ + '/contract.cpp').hexdigest
pins['runner'] = Digest::SHA256.file(__FILE__).hexdigest
commands = []
used = {}
run = lambda do |name, argv, expected = 0, condition = nil, seconds = 60|
  raise 'duplicate raw tag' if used[name]
  used[name] = true
  out = ''; err = ''; status = nil; timed = false
  begin
    out, err, status = capture(argv, seconds)
  rescue RuntimeError => e
    raise unless e.message == 'deadline exceeded'
    timed = true
  end
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << { name: name, argv: argv, exit: status && status.exitstatus, signal: status && status.termsig, timeout: timed }
  valid = !timed && status && status.exited? && status.exitstatus == expected &&
    !(out + err).match?(/AddressSanitizer|UndefinedBehaviorSanitizer|LeakSanitizer|MemorySanitizer|ThreadSanitizer|runtime error:/)
  valid &&= err.lines.map(&:strip).include?('FAIL contract: ' + condition) if condition
  valid &&= out.include?('PASS actual-source theme lifecycle') unless condition || name.end_with?('compile') || name == 'apply-patch'
  raise 'rejected command: ' + name unless valid
  [out, err]
end
begin
  # The runner must reject crashes, unrelated assertions and sanitizer reports.
  gates = {
    'signal' => ['puts "PASS actual-source theme lifecycle"; Process.kill("KILL", Process.pid)', false, nil, 2],
    'wrong-check' => ['warn "FAIL contract: unrelated"; exit 1', false, 'named', 2],
    'ubsan-zero' => ['puts "PASS actual-source theme lifecycle"; warn "x.cpp:1: runtime error: invalid access"', false, nil, 2],
    'asan-check' => ['warn "AddressSanitizer: invalid access"; warn "FAIL contract: named"; exit 1', false, 'named', 2],
    'held-pipe' => ['fork { sleep 20 }; exit 0', false, nil, 0.5],
    'named-check' => ['warn "FAIL contract: named"; exit 1', true, 'named', 2]
  }
  gates.each do |name, (code, expected, condition, seconds)|
    accepted = true
    begin
      run.call('gate-' + name, [RbConfig.ruby, '-e', code], condition ? 1 : 0, condition, seconds)
    rescue RuntimeError => e
      raise unless e.message == 'rejected command: gate-' + name
      accepted = false
    end
    raise 'process gate classified incorrectly' unless accepted == expected
  end
  gui = File.read(source + '/' + paths[0])
  style = File.read(source + '/' + paths[1])
  kde = File.read(source + '/' + paths[2])
  FileUtils.mkdir_p(work + '/patched/src/gui/kernel')
  changed = work + '/patched/' + paths[0]
  File.write(changed, gui)
  Dir.chdir(work + '/patched') { run.call('apply-patch', ['patch', '-s', '-p0', '-F0', '-i', patch]) }
  patched = File.read(changed)
  process_sig = 'void QGuiApplicationPrivate::processThemeChanged('
  handler = function(gui, 'void QGuiApplicationPrivate::handleThemeChanged()')
  update = function(style, 'void QStyleHintsPrivate::update(const QPlatformTheme *theme)')
  constructor = function(kde, 'QKdeTheme::QKdeTheme(')
  refresh = function(kde, 'void QKdeThemePrivate::refresh()')
  create = function(kde, 'QPlatformTheme *QKdeTheme::createKdeTheme()')
  version_gate = create.split('    // Determine KDE prefixes', 2).first
  raise 'KDE modern version gate' unless version_gate.include?('if (kdeVersion < 4)') && version_gate.include?('if (kdeVersion > 4)') && version_gate.include?('return new QKdeTheme(QStandardPaths::standardLocations(QStandardPaths::GenericConfigLocation), kdeVersion);')
  version_gate += "    return nullptr; // Legacy KDE 4 path is outside this contract.\n}\n"
  notification = 'QWindowSystemInterface::handleThemeChange();'
  raise 'KDE refresh notification' unless refresh.scan(notification).size == 1
  install = 'QGuiApplicationPrivate::platform_theme = QGuiApplicationPrivate::platform_integration->createPlatformTheme(themeName);'
  raise 'actual install assignment' unless gui.scan(install).size == 1
  post = 'QStyleHintsPrivate::get(QGuiApplication::styleHints())->update(platformTheme());'
  raise 'post-assignment style update' unless gui.include?("init_platform(QLatin1StringView(platformName), platformPluginPath, platformThemeName, argc, argv);\n    " + post)
  init = "updatePalette();\n    QFont::initialize();\n    initThemeHints();"
  raise 'post-assignment state initialization' unless gui.include?("createPlatformIntegration();\n\n    " + init)
  make = lambda do |processor|
    [gui, style, kde].map { |t| t.lines.take_while { |line| line.start_with?('//') || line.strip.empty? }.join }.uniq.join("\n") +
      processor + handler + update + constructor + version_gate +
      "void QKdeThemePrivate::refresh() { ++refreshed; #{notification} if (repeatConstructor && !QGuiApplicationPrivate::platform_theme) #{notification} }\n" +
      "static void install_theme() { QString themeName; #{install} }\n" +
      "static void initialize_state() {\n    const auto platformTheme = QGuiApplicationPrivate::platformTheme;\n    const auto updatePalette = QGuiApplicationPrivate::updatePalette;\n    #{post}\n    #{init}\n}\n"
  end
  body = work + '/actual-theme.h'
  compile = Shellwords.split(ENV.fetch('CXX', 'c++')) + %w[-std=c++17 -Wall -Wextra -Werror] + Shellwords.split(ENV.fetch('CXXFLAGS', '')) + ['-I' + work, __dir__ + '/contract.cpp', '-o', work + '/contract']
  baseline = make.call(function(gui, process_sig))
  File.write(body, baseline)
  run.call('baseline-compile', compile)
  run.call('baseline-constructor', [work + '/contract', 'constructor'], 1, 'theme')
  positive = make.call(function(patched, process_sig))
  File.write(body, positive)
  run.call('positive-compile', compile)
  %w[constructor constructor-repeat version-refused generic late explicit-font no-app].each { |s| run.call(s, [work + '/contract', s]) }
  mutations = {
    'version-gate' => ['const int kdeVersion = kdeVersionBA.toInt();', 'const int kdeVersion = (void(kdeVersionBA), 6);', 'version-refused', 'refreshed == 0 && requested == 0 && QGuiApplicationPrivate::platform_theme == nullptr'],
    'constructor-guard' => ['if (!qGuiApp || !platformTheme())', 'if (!qGuiApp)', 'constructor', 'theme'],
    'runtime-delivery' => ['if (!qGuiApp || !platformTheme())', 'if (true)', 'late', 'styleUpdates == 2'],
    'no-application' => ['if (!qGuiApp || !platformTheme())', 'if (!platformTheme())', 'no-app', 'app'],
    'initial-style' => ["    #{post}\n    #{init}", "    (void)platformTheme;\n    #{init}", 'constructor', 'styleUpdates == 1'],
    'initial-palette' => ["    #{init}", "    (void)updatePalette;\n    QFont::initialize();\n    initThemeHints();", 'constructor', 'paletteValue == expected && fontValue == expectedFont && hintValue == expected'],
    'explicit-font' => ['if (!(applicationResourceFlags & ApplicationFontExplicitlySet))', 'if (true)', 'explicit-font', 'paletteValue == expected && fontValue == expectedFont && hintValue == expected']
  }
  mutations.each do |name, (before, after, scenario, condition)|
    raise 'nonunique mutation: ' + name unless positive.scan(before).size == 1
    File.write(body, positive.sub(before, after))
    run.call('control-' + name + '-compile', compile)
    run.call('control-' + name, [work + '/contract', scenario], 1, condition)
  end
  File.write(body, positive)
  run.call('final-compile', compile)
  paths.each { |p| raise 'shared source changed' unless pins[p] == Digest::SHA256.file(source + '/' + p).hexdigest }
  puts 'PASS actual-source Qt theme lifecycle and named causal controls'
ensure
  File.write(work + '/receipt.json', JSON.pretty_generate({ inputs_sha256: pins, commands: commands, scope: 'Actual extracted Qt bodies with controlled synchronous QPA/configuration services. No full Qt runtime, KWin, target execution or shared build mutation.' }) + "\n")
end
