#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted fresh libstdc++ build with audited inheritance.
require 'rbconfig'
require_relative '../runtime/recipe/files/runtime'
require_relative '../runtime/recipe/files/inheritance'

module GCC16Runtime
  class LibstdcxxRebuild
    def initialize(args)
      @check = args.first == '--check'
      args.shift if @check
      raise Invalid, 'Usage: rebuild-libstdcxx.rb [--check] TARGET NEW_PKGSRC OLD_PKGSRC GCC_ARCHIVE APP_PREFIX SYSROOT OLD_WORK NEW_WORK' unless args.length == 8
      @target, @pkgsrc, @old_pkgsrc, @archive, @compiler, @sysroot, @old_work, @work = args
      @architecture = TARGETS.fetch(@target) { raise Invalid, 'Unsupported target' }
      @triplet = @architecture.fetch(:triplet)
      args.drop(1).each do |path|
        raise Invalid, 'Absolute simple paths required' unless path.match?(%r{\A/[A-Za-z0-9_./-]+\z}) && !path.split('/').include?('..')
      end
      raise Invalid, 'NEW_WORK already exists' if File.exist?(@work) || File.symlink?(@work)
      @jobs = Integer(ENV.fetch('CROSS_JOBS', '2'), 10)
      raise Invalid, 'CROSS_JOBS must be positive' unless @jobs.positive?
      @here = File.realpath(__dir__)
      @make = ENV.fetch('GNU_MAKE', '/usr/bin/make')
      raise Invalid, 'GNU_MAKE must be an absolute executable' unless @make.start_with?('/') && File.executable?(@make)
      @env = %w[GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH CONFIG_SITE].to_h { |k| [k, nil] }
      @env['PATH'] = @compiler + '/bin:' + ENV.fetch('PATH')
    end

    def capture(*args)
      out, err, status = Open3.capture3(@env, *args)
      raise Invalid, "Command failed: #{args.first}: #{err}" unless status.success?
      out
    end

    def digest(path)
      Inheritance.hash(path)
    end

    def record(path)
      raise Invalid, "Missing regular input: #{path}" unless File.file?(path)
      @inputs[path] = digest(path)
    end

    def check_elf(path, root)
      resolved = File.realpath(path)
      raise Invalid, 'Target ELF escapes its prefix' unless resolved.start_with?(File.realpath(root) + '/')
      data = File.binread(resolved, 20)
      raise Invalid, "Wrong target ELF: #{path}" unless data&.byteslice(0, 7) == "\x7fELF\x02\x01\x01".b && data.byteslice(18, 2).unpack1('v') == @architecture[:elf_machine]
      record(resolved)
    end

    def preflight
      @parent = Stage.new(@old_work, @old_pkgsrc, @archive, allow_rebuild: false).verify
      raise Invalid, 'Parent architecture mismatch' unless @parent[:metadata]['GCC_RUNTIME_TARGET'] == @target
      Inheritance.check_delta(@old_pkgsrc + '/lang/gcc16', @pkgsrc + '/lang/gcc16')
      @inputs = {}
      record(@archive)
      [@pkgsrc, @old_pkgsrc].each do |prefix|
        recipe = prefix + '/lang/gcc16'
        (%w[Makefile Makefile.common distinfo].map { |n| recipe + '/' + n } + Dir.glob(recipe + '/patches/*')).each { |p| record(p) }
      end
      @receipt = @compiler + '/../inputs.txt'
      text = File.read(@receipt)
      raise Invalid, 'Missing application compiler provenance' unless text.lines.count("mode=applications\n") == 1 && text.lines.count("triplet=#{@triplet}\n") == 1
      [digest(@archive), digest(@old_pkgsrc + '/lang/gcc16/distinfo')].each do |sha|
        raise Invalid, 'Application compiler source identity differs' unless text.lines.any? { |l| l.start_with?(sha + '  ') }
      end
      record(@receipt)
      @tools = {}
      %w[gcc g++ ar as ld nm objcopy objdump ranlib readelf strip].each do |name|
        path = @compiler + '/bin/' + @triplet + '-' + name
        raise Invalid, "Missing cross tool: #{name}" unless File.executable?(path)
        @tools[name] = path
        record(File.realpath(path))
      end
      %w[gcc g++].each do |name|
        raise Invalid, 'Compiler target mismatch' unless capture(@tools[name], '-dumpmachine').strip == @triplet
        raise Invalid, 'GCC16.2 required' unless capture(@tools[name], '-dumpfullversion').strip == VERSION
        out, err, status = Open3.capture3(@env, @tools[name], '-v')
        raise Invalid, 'POSIX-thread compiler required' unless status.success? && (out + err).lines.include?("Thread model: posix\n")
      end
      macros, err, status = Open3.capture3(@env, @tools['gcc'], '-dM', '-E', '-x', 'c', '-', stdin_data: "\n")
      arch = @target == 'amd64' ? '__x86_64__' : '__aarch64__'
      raise Invalid, "Cannot inspect target macros: #{err}" unless status.success?
      ["__GNUC__ 16", "__NetBSD__ 1", "__SIZEOF_POINTER__ 8", "#{arch} 1"].each do |definition|
        raise Invalid, 'Compiler target ABI mismatch' unless macros.lines.include?("#define #{definition}\n")
      end
      %w[ar as ld nm objcopy objdump ranlib readelf strip].each do |name|
        version = capture(@tools[name], '--version')
        label = name == 'as' ? 'assembler' : name
        raise Invalid, 'Expected genuine GNU target binutils' unless version.match?(/^GNU #{label}[ (]/)
        raise Invalid, 'Assembler target mismatch' if name == 'as' && !version.include?("target of `#{@triplet}'")
      end
      raise Invalid, 'GNU make required' unless capture(@make, '--version').start_with?('GNU Make ')
      record(File.realpath(@make))
      %w[cc1 cc1plus].each do |name|
        path = File.realpath(capture(@tools['gcc'], '-print-prog-name=' + name).strip)
        raise Invalid, 'Frontend escapes compiler prefix' unless path.start_with?(File.realpath(@compiler) + '/')
        record(path)
      end
      @flags = ["--sysroot=#{@sysroot}", "-B#{@sysroot}/usr/pkg/gcc16/lib/gcc/#{@triplet}/#{VERSION}/", "-B#{@sysroot}/usr/pkg/gcc16/lib/"]
      %w[crtbegin.o crtbeginS.o crtend.o crtendS.o libgcc.a libgcc_s.so].each do |name|
        path = capture(@tools['gcc'], *@flags, '-print-file-name=' + name).strip
        check_elf(path, @sysroot + '/usr/pkg/gcc16') unless name == 'libgcc.a' || name == 'libgcc_s.so'
        expected = @old_work + '/stage/usr/pkg/gcc16/' + (name == 'libgcc_s.so' ? 'lib/' : "lib/gcc/#{@triplet}/#{VERSION}/") + name
        raise Invalid, 'SDK GCC16 support input differs from parent stage' unless File.realpath(path).start_with?(File.realpath(@sysroot) + '/usr/pkg/gcc16/') && digest(path) == digest(expected)
        record(path)
      end
      @parent.fetch(:files).each do |relative|
        path = @sysroot + '/usr/pkg/' + relative
        check_elf(path, @sysroot + '/usr/pkg/gcc16')
        raise Invalid, 'SDK runtime differs from parent stage' unless digest(path) == digest(@old_work + '/stage/usr/pkg/' + relative)
        record(path)
      end
      %w[libc.so.12 libpthread.so.1 libm.so.0 crt0.o].each { |n| check_elf(@sysroot + '/usr/lib/' + n, @sysroot) }
      %w[stddef.h stdio.h pthread.h math.h].each { |n| record(@sysroot + '/usr/include/' + n) }
      old_inputs = File.readlines(@old_work + '/inputs.txt')
      seed = old_inputs.grep(/^sysroot=/)
      raise Invalid, 'Parent seed identity missing' unless seed.size == 1
      old_seed = seed.first.delete_prefix('sysroot=').strip
      %w[usr/lib/libc.so.12 usr/lib/libpthread.so.1 usr/lib/libm.so.0 usr/lib/crt0.o usr/include/stddef.h usr/include/stdio.h usr/include/pthread.h usr/include/math.h].each do |relative|
        raise Invalid, 'EmberBSD seed differs from authenticated parent' unless old_inputs.count("#{digest(@sysroot + '/' + relative)}  #{old_seed}/#{relative}\n") == 1
      end
      Inheritance::PARENT_FILES.each { |n| record(@old_work + '/' + n) }
      [__FILE__, @here + '/prepare-source.sh', @here + '/audit-source.sh', @here + '/../runtime/recipe/files/runtime.rb', @here + '/../runtime/recipe/files/inheritance.rb'].each { |p| record(File.realpath(p)) }
      puts JSON.pretty_generate(scope: 'fresh-libstdcxx-preflight', target: @target, stage: @work + '/stage', compiler: @tools['gcc'], flags: @flags, inherited: Inheritance.inherited_paths(@parent), inputs: @inputs)
    end

    def unchanged_inputs
      @inputs.each { |path, sha| raise Invalid, "Input changed: #{path}" unless digest(path) == sha }
    end

    def run_logged(log, env, *command, chdir: @work)
      status = nil
      File.open(@work + '/' + log, 'w') do |out|
        out.puts('argv=' + JSON.generate(command))
        out.flush
        pid = Process.spawn(@env.merge(env), *command, chdir: chdir, out: out, err: [:child, :out])
        _, status = Process.wait2(pid)
      end
      raise Invalid, "Failed #{log}, status #{status.exitstatus.inspect}" unless status.success?
    end

    def manifests
      entries = Inheritance.inventory(@work + '/stage')
      File.write(@work + '/stage.sha256', entries.sort.filter_map { |p, x| "#{x['sha256']}  ./#{p}\n" if x['sha256'] }.join)
      File.write(@work + '/stage.symlinks', entries.sort.filter_map { |p, x| "./#{p}\t#{x['link']}\n" if x['link'] }.join)
    end

    def compiler_commands
      # Autoconf expands these values as words; it does not unescape shell text.
      # Compiler paths and the paths in @flags passed the simple-path guard.
      {'CC' => [@tools['gcc'], *@flags].join(' '),
       'CXX' => [@tools['gcc'], *@flags, '-shared-libgcc', '-nostdinc++'].join(' ')}
    end

    def prepare_gthreads(source)
      # Standalone libstdc++ still probes the sibling libgcc build header.
      mapping = source + '/config/gthr.m4'
      makefile = source + '/libgcc/Makefile.in'
      header = File.read(mapping)[/^\s+posix\)\s+thread_header=([A-Za-z0-9_.-]+) ;;/, 1]
      raise Invalid, 'Unexpected upstream POSIX thread header' unless header == 'gthr-posix.h'
      rule = File.read(makefile)[/^gthr-default\.h: \$\(srcdir\)\/\$\(thread_header\)\n\t-\$\(LN_S\) \$< \$@\n/]
      raise Invalid, 'Unexpected upstream gthr-default rule' unless rule
      directory = @work + '/build/' + @triplet + '/libgcc'
      FileUtils.mkdir_p(directory)
      rulefile = @work + '/gthreads.mk'
      File.write(rulefile, rule)
      run_logged('gthreads.log', {}, @make, '-f', rulefile, 'srcdir=' + source + '/libgcc',
        'thread_header=' + header, 'LN_S=ln -s', 'gthr-default.h', chdir: directory)
      generated = directory + '/gthr-default.h'
      expected = source + '/libgcc/' + header
      raise Invalid, 'Incorrect generated thread header' unless File.symlink?(generated) && File.realpath(generated) == File.realpath(expected)
      [mapping, makefile, expected, rulefile, generated, @work + '/gthreads.log'].each { |path| record(path) }
    end

    def build
      preflight
      return if @check
      Dir.mkdir(@work)
      FileUtils.mkdir_p(@work + '/parent-recipe/lang')
      FileUtils.cp_r(@old_pkgsrc + '/lang/gcc16', @work + '/parent-recipe/lang', preserve: true)
      Dir.mkdir(@work + '/parent')
      Inheritance::PARENT_FILES.each { |n| FileUtils.cp(@old_work + '/' + n, @work + '/parent/' + n, preserve: true) }
      FileUtils.cp_r(@old_work + '/stage', @work + '/parent', preserve: true)
      parent_paths = {'archive' => File.expand_path(@archive), 'pkgsrc' => File.expand_path(@old_pkgsrc)}
      Stage.new(@work + '/parent', @work + '/parent-recipe', @archive, receipt_paths: parent_paths, allow_rebuild: false).verify
      run_logged('patch.log', {}, 'sh', @here + '/prepare-source.sh', @pkgsrc, @archive, @work + '/src')
      prepare_gthreads(@work + '/src')
      build = @work + '/build/' + @triplet + '/libstdc++-v3'
      FileUtils.mkdir_p(build)
      target_flags = @target == 'amd64' ? '-O2 -march=nocona -mtune=nocona -mfpmath=sse' : '-O2'
      env = compiler_commands.merge(
        'CFLAGS' => target_flags, 'CXXFLAGS' => target_flags, 'CPPFLAGS' => '',
        'LDFLAGS' => "-L#{@sysroot}/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib",
        'ac_cv_func_clock_gettime' => 'yes', 'ac_cv_func_gethostbyname_r' => 'no',
        'ac_cv_func_freelocale' => 'no', 'ac_cv_func_newlocale' => 'no', 'ac_cv_func_uselocale' => 'no')
      %w[ar as ld nm objcopy objdump ranlib readelf strip].each { |name| env[name.upcase] = @tools[name] }
      build_triplet = capture('sh', @work + '/src/config.guess').strip
      args = ["--build=#{build_triplet}", "--host=#{@triplet}", "--target=#{@triplet}", "--with-cross-host=#{build_triplet}", "--with-target-subdir=#{@triplet}",
        '--prefix=/usr/pkg/gcc16', '--libdir=/usr/pkg/gcc16/lib', '--with-toolexeclibdir=/usr/pkg/gcc16/lib',
        '--with-local-prefix=/usr/pkg/gcc16', '--with-gxx-include-dir=/usr/pkg/gcc16/include/c++', "--with-sysroot=#{@sysroot}",
        '--with-native-system-header-dir=/usr/include', '--with-gnu-as', '--with-gnu-ld', "--with-as=#{@tools['as']}", "--with-ld=#{@tools['ld']}",
        '--disable-multilib', '--enable-shared', '--enable-threads=posix', '--enable-long-long', '--disable-libssp', '--disable-libstdcxx-pch', '--disable-nls',
        "--program-transform-name=s&^&#{@triplet}-&", '--disable-year2038']
      File.write(@work + '/commands.json', JSON.pretty_generate(environment: env, configure: args) + "\n")
      run_logged('configure.log', env, @work + '/src/libstdc++-v3/configure', *args, chdir: build)
      config = File.read(build + '/config.status')
      raise Invalid, 'Expected generic locale backend' unless config.include?('config/locale/generic/c_locale.cc')
      header = File.read(build + '/config.h')
      raise Invalid, 'C++ threads unavailable' unless header.match?(/^#define _GLIBCXX_HAS_GTHREADS 1$/)
      run_logged('runtime-build.log', env, @make, '-j' + @jobs.to_s, 'all', chdir: build)
      run_logged('runtime-install.log', env, @make, 'DESTDIR=' + @work + '/stage', 'install', chdir: build)
      raise Invalid, 'Installed locale header differs from prepared source' unless digest(@work + "/stage/usr/pkg/gcc16/include/c++/#{@triplet}/bits/c++locale.h") == digest(@work + '/src/libstdc++-v3/config/locale/generic/c_locale.h')
      fresh = Inheritance.inventory(@work + '/stage')
      old = Inheritance.inventory(@work + '/parent/stage')
      inherited = Inheritance.inherited_paths(@parent).to_h { |p| [p, old.fetch(p)] }
      inherited.each_key do |p|
        target = @work + '/stage/' + p
        raise Invalid, 'Overlapping installation ownership' if File.exist?(target) || File.symlink?(target)
        FileUtils.mkdir_p(File.dirname(target))
        if inherited[p].key?('link')
          File.symlink(inherited[p]['link'], target)
        else
          FileUtils.copy_file(@work + '/parent/stage/' + p, target, true)
        end
      end
      unchanged_inputs
      receipts = Inheritance::PARENT_FILES.to_h { |n| [n, digest(@work + '/parent/' + n)] }
      logs = %w[configure.log runtime-build.log runtime-install.log].to_h { |n| [n, digest(@work + '/' + n)] }
      Dir.mkdir(@work + '/configuration')
      %w[config.status config.h].each { |n| FileUtils.copy_file(build + '/' + n, @work + '/configuration/' + n, true) }
      configuration = Inheritance::CONFIG_FILES.to_h { |n| [n, digest(@work + '/' + n)] }
      File.write(@work + '/inheritance.json', JSON.pretty_generate(format: 1, parent_paths: parent_paths, parent_receipts: receipts, inherited: inherited, rebuilt: fresh, build_logs: logs, configuration: configuration) + "\n")
      [@work + '/inheritance.json', @work + '/src/libstdc++-v3/configure', *Inheritance::CONFIG_FILES.map { |n| @work + '/' + n }].each { |p| record(p) }
      lines = "scope=runtime-libstdcxx-rebuild\ntarget=#{@target}\ntriplet=#{@triplet}\nseed_source=#{@parent[:metadata]['EMBERBSD_SEED_SOURCE']}\nruntime_libraries=#{@parent[:metadata]['GCC_RUNTIME_LIBRARIES']}\n"
      @inputs.each { |p, sha| lines << "#{sha}  #{p}\n" }
      File.write(@work + '/inputs.txt', lines)
      manifests
      File.write(@work + '/build-success', "runtime-libstdcxx-rebuild\n")
      begin
        result = Stage.new(@work, @pkgsrc, @archive).verify
        File.write(@work + '/stage-check.json', JSON.pretty_generate(result) + "\n")
      rescue StandardError
        File.rename(@work + '/build-success', @work + '/failed-stage-marker')
        raise
      end
      puts "Verified fresh runtime stage: #{@work}/stage (target execution pending)"
    end
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    GCC16Runtime::LibstdcxxRebuild.new(ARGV).build
  rescue GCC16Runtime::Invalid, SystemCallError, ArgumentError, KeyError => e
    warn "rebuild-libstdcxx: #{e.message}"
    exit 1
  end
end
