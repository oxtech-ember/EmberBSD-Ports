#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); genuine archived GCC16 runtime link commands.
require 'shellwords'
require_relative 'rebuild-libstdcxx'
require_relative '../runtime/recipe/files/relro'

module GCC16Runtime
  class RelroRelink
    def initialize(args)
      raise Invalid, 'Usage: relink-relro.rb TARGET NEW_PKGSRC OLD_PKGSRC GCC_ARCHIVE APP_PREFIX SYSROOT OLD_WORK LOCALE_WORK BACKUP BACKUP_SHA256 NEW_WORK' unless args.size == 11
      @target, @pkgsrc, old_pkgsrc, @archive, compiler, sysroot, @old, @parent, @backup, @backup_sha, @work = args
      raise Invalid, 'Expected archive SHA256' unless @backup_sha.match?(/\A[0-9a-f]{64}\z/)
      [@parent, @backup].each { |p| raise Invalid, 'Absolute simple paths required' unless p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) && !p.split('/').include?('..') }
      @preflight = LibstdcxxRebuild.new(['--check', @target, @pkgsrc, old_pkgsrc, @archive, compiler, sysroot, @old, @work])
      @readelf = compiler + '/bin/' + TARGETS.fetch(@target).fetch(:triplet) + '-readelf'
      @stock = old_pkgsrc + '/mk/check/check-relro-elf.awk'
      @env = %w[GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH CONFIG_SITE].to_h { |key| [key, nil] }.merge('LC_ALL' => 'C')
      @inputs = {}; @commands = []
    end

    def hash(path)
      Inheritance.hash(path)
    end

    def record(path)
      @inputs[path] = hash(path)
    end

    def capture(*argv, chdir: @work, stdin_data: '')
      out, err, status = Open3.capture3(@env, *argv, chdir: chdir, stdin_data: stdin_data)
      raise Invalid, "Failed #{argv.first}: #{err}" unless status.success?
      out
    end

    def abi(path)
      text = capture(@readelf, '--dyn-syms', '--wide', path)
      rows = text.lines.filter_map do |line|
        fields = line.split
        next unless fields.size >= 8 && fields[0].match?(/\A\d+:\z/) && fields[6] != 'UND'
        [fields[2], fields[3], fields[4], fields[5], fields[7]]
      end.sort
      raise Invalid, 'No dynamic symbols' if rows.empty?
      rows
    end

    def run
      @preflight.preflight
      raise Invalid, 'Archived bootstrap hash mismatch' unless hash(@backup) == @backup_sha
      raise Invalid, 'Expected completed locale rebuild' unless File.read(@parent + '/build-success') == "runtime-libstdcxx-rebuild\n"
      parent = Stage.new(@parent, @pkgsrc, @archive, historical: true).verify
      raise Invalid, 'All four runtime libraries are required' unless parent[:metadata]['GCC_RUNTIME_LIBRARIES'] == SELECTIONS.last
      raise Invalid, 'Locale target differs' unless parent[:metadata]['GCC_RUNTIME_TARGET'] == @target
      Dir.mkdir(@work); Dir.mkdir(@work + '/proof')
      root = File.basename(@old)
      triplet = TARGETS.fetch(@target).fetch(:triplet)
      listing = capture('tar', '-tzf', @backup).lines.map(&:chomp)
      driver = %w[xgcc collect2 collect-ld specs libgcc_s.so libgcc_s.so.1 libgcc_s_asneeded.so crtbeginS.o crtendS.o libgcc.a liblto_plugin.so]
      rules = %w[libatomic/libatomic.map libgcc/config/t-slibgcc libgcc/config/t-slibgcc-gld libgcc/Makefile.in libgomp/Makefile.in libatomic/Makefile.in]
      members = listing.select { |p| p.match?(%r{\A#{Regexp.escape(root)}/build/#{Regexp.escape(triplet)}/(?:libgcc|libgomp|libatomic)/}) && !p.end_with?('/') }
      members += driver.map { |n| root + '/build/gcc/' + n }
      members += (Relro::PARENT - ['inheritance.json'] + ['runtime-build.log']).map { |n| root + '/' + n }
      members += rules.map { |n| root + '/src/' + n }
      raise Invalid, 'Unsafe or missing archive members' unless members.all? { |n| n.match?(%r{\A[A-Za-z0-9_+./-]+\z}) && !n.split('/').include?('..') && listing.count(n) == 1 }
      File.write(@work + '/members.txt', members.join("\n") + "\n")
      capture('tar', '-xzf', @backup, '-C', @work, '--no-recursion', '--verbatim-files-from', '-T', @work + '/members.txt')
      restored = @work + '/' + root
      (Relro::PARENT - ['inheritance.json'] + ['runtime-build.log']).each do |n|
        raise Invalid, 'Archived original receipt mismatch' unless hash(restored + '/' + n) == hash(@old + '/' + n)
      end
      # Keep every selected regular file immutable; link outputs use proof/.
      Find.find(restored) { |p| record(p) if File.file?(p) && !File.symlink?(p) }
      record(@readelf); record(__FILE__); record(@work + '/members.txt')
      linker_wrapper = File.read(restored + '/build/gcc/collect-ld')
      linker = linker_wrapper[/^ORIGINAL_LD_FOR_TARGET=['"]?([^'"\n]+)['"]?$/, 1]
      raise Invalid, 'Missing absolute original linker' unless linker && linker.start_with?('/') && File.executable?(linker)
      lines = File.readlines(restored + '/inputs.txt')
      raise Invalid, 'Original linker differs from authenticated bootstrap' unless lines.include?("#{hash(linker)}  #{linker}\n")
      record(linker)
      original_seed = lines.grep(/^sysroot=/).map { |l| l.strip.delete_prefix('sysroot=') }
      raise Invalid, 'Expected one original seed' unless original_seed.size == 1
      %w[usr/lib/libc.so.12 usr/lib/libpthread.so.1 usr/lib/libm.so.0 usr/lib/crt0.o].each do |n|
        path = original_seed.first + '/' + n
        raise Invalid, 'Original seed differs from bootstrap' unless lines.include?("#{hash(path)}  #{path}\n")
        record(path)
      end
      raise Invalid, 'Wrong archived compiler version' unless capture(restored + '/build/gcc/xgcc', '-dumpfullversion').strip == VERSION
      raise Invalid, 'Wrong archived target' unless capture(restored + '/build/gcc/xgcc', '-dumpmachine').strip == triplet
      log = File.readlines(restored + '/runtime-build.log')
      components = {}
      Relro::COMPONENTS.each do |library, basename|
        selected = log.select do |line|
          library == 'libgcc' ? line.start_with?(@old + '/build/./gcc/xgcc') && line.include?('-o ./libgcc_s.so.1.tmp') : line.start_with?('libtool: link: ') && line.include?('-o .libs/' + basename)
        end
        raise Invalid, 'Expected one original link command' unless selected.size == 1
        original = Shellwords.split(selected.first.sub(/^libtool: link: /, '').split(' && ', 2).first)
        argv = original.map { |word| word.gsub(@old, restored) }
        raise Invalid, 'Unexpected original link driver' unless argv.first == restored + '/build/./gcc/xgcc'
        raise Invalid, 'Expected one link output' unless argv.count('-o') == 1 && argv.include?('-shared') && !argv.include?('-c')
        index = argv.index('-o')
        outputs = [false, true].map do |relro|
          output = @work + '/proof/' + basename + (relro ? '.relro' : '.baseline')
          command = argv.dup; command[index + 1] = output
          command << '-Wl,-z,relro' if relro
          out, err, status = Open3.capture3(@env, *command, chdir: restored + '/build/' + triplet + '/' + library)
          name = library + (relro ? '-relro' : '-baseline')
          File.write(@work + '/' + name + '.stdout', out); File.write(@work + '/' + name + '.stderr', err)
          @commands << {component: library, argv: command, status: status.exitstatus}
          File.write(@work + '/commands.json', JSON.pretty_generate(@commands) + "\n")
          raise Invalid, 'Actual link failed' unless status.success?
          output
        end
        relative = 'usr/pkg/gcc16/lib/' + basename
        raise Invalid, 'Baseline does not reproduce original bytes' unless hash(outputs.first) == hash(@parent + '/stage/' + relative)
        old_abi = abi(outputs.first)
        raise Invalid, 'Runtime symbol identity or size changed' unless old_abi == abi(outputs.last)
        File.write(@work + '/' + library + '-abi.json', JSON.pretty_generate(old_abi) + "\n")
        soname = LIBRARIES.fetch(library)
        target = TARGETS.fetch(@target)
        allowed = LIBRARIES.values
        before = ELF.new(outputs.first).verify(soname, target, allowed, require_relro: false)
        after = ELF.new(outputs.last).verify(soname, target, allowed)
        raise Invalid, 'Runtime dependency changed' unless before == after
        components[library] = {path: relative, before: hash(outputs.first), after: hash(outputs.last)}
      end
      stock = @stock
      %w[baseline relro].each do |mode|
        paths = Relro::COMPONENTS.values.map { |n| @work + '/proof/' + n + '.' + mode }
        out, err, status = Open3.capture3(@env.merge('READELF' => @readelf), 'awk', '-f', stock, stdin_data: paths.join("\n") + "\n")
        File.write(@work + '/stock-' + mode + '.stdout', out); File.write(@work + '/stock-' + mode + '.stderr', err)
        expected = mode == 'baseline' ? paths.map { |p| p + ": missing RELRO\n" }.join : ''
        raise Invalid, 'Stock pkgsrc RELRO check differs' unless status.success? && err.empty? && out == expected
      end
      record(stock); record(@work + '/commands.json')
      Dir.glob(@work + '/*.{stdout,stderr,json}').each { |p| record(p) }
      @inputs.each { |p, sha| raise Invalid, 'Relink input changed' unless hash(p) == sha }
      FileUtils.cp_r(@parent + '/stage', @work + '/stage', preserve: true)
      components.each_value { |r| FileUtils.copy_file(@work + '/proof/' + File.basename(r[:path]) + '.relro', @work + '/stage/' + r[:path]) }
      receipt = {format: 1, parent_work: File.realpath(@parent), parent_receipts: Relro::PARENT.to_h { |n| [n, hash(@parent + '/' + n)] },
                 backup: {path: File.realpath(@backup), sha256: @backup_sha}, inputs: @inputs, components: components}
      File.write(@work + '/relink.json', JSON.pretty_generate(receipt) + "\n")
      inputs = File.read(@parent + '/inputs.txt').sub(/^scope=runtime-libstdcxx-rebuild$/, 'scope=runtime-relro-relink')
      File.write(@work + '/inputs.txt', inputs + "#{hash(@work + '/relink.json')}  #{@work}/relink.json\n")
      entries = Inheritance.inventory(@work + '/stage')
      File.write(@work + '/stage.sha256', entries.sort.filter_map { |p, x| "#{x['sha256']}  ./#{p}\n" if x['sha256'] }.join)
      File.write(@work + '/stage.symlinks', entries.sort.filter_map { |p, x| "./#{p}\t#{x['link']}\n" if x['link'] }.join)
      File.write(@work + '/build-success', "runtime-relro-relink\n")
      begin
        result = Stage.new(@work, @pkgsrc, @archive).verify
        File.write(@work + '/stage-check.json', JSON.pretty_generate(result) + "\n")
      rescue StandardError
        File.rename(@work + '/build-success', @work + '/failed-stage-marker')
        raise
      end
      puts 'PASS: exact original baseline DSOs, three real RELRO relinks, unchanged ABI and ordinary stage gates; target runtime pending.'
    end
  end
end
if $PROGRAM_NAME == __FILE__
  begin
    GCC16Runtime::RelroRelink.new(ARGV).run
  rescue GCC16Runtime::Invalid, SystemCallError, ArgumentError, KeyError => error
    warn "relink-relro: #{error.message}"; exit 1
  end
end
