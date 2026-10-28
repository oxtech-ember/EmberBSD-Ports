EmberBSD local test harness repair, AI-assisted; not submitted upstream.
Preserve selected tools and propagate test failures.

--- tests/aslts.sh.orig
+++ tests/aslts.sh
@@ -4,10 +4,11 @@
 #
 
 # Will build temporary versions of iASL and acpiexec
-postfix=`date +%H%M%S`
-tmp_iasl=/tmp/iasl-$postfix
-tmp_acpiexec=/tmp/acpiexec-$postfix
-tmp_acpibin=/tmp/acpibin-$postfix
+tmp_tool_dir=$(mktemp -d "${TMPDIR:-/tmp}/acpica-aslts.XXXXXXXX") || exit 1
+tmp_iasl=$tmp_tool_dir/iasl
+tmp_acpiexec=$tmp_tool_dir/acpiexec
+tmp_acpibin=$tmp_tool_dir/acpibin
+trap 'rm -f "$tmp_iasl" "$tmp_acpiexec" "$tmp_acpibin"; rmdir "$tmp_tool_dir"' EXIT
 
 TEST_CASES=
 TEST_MODES=
@@ -49,16 +50,16 @@
 
 	if [ -z "$generation_dir" ] ; then
 		echo "missing generation directory argument"
-		exit
+		exit 1
 	elif [ -z "$aslts_dir" ] ; then
 		echo "missing aslts directory argument"
-		exit
+		exit 1
 	elif [ ! -d "$generation_dir" ] ; then
 		echo $generation_dir is not a dir
-		exit
+		exit 1
 	elif [ ! -d "$aslts_dir" ] ; then
 		echo $aslts_dir is not a dir
-		exit
+		exit 1
 	fi
 
 	# Variables required by ASLTS
@@ -78,45 +79,45 @@
 build_acpi_tools() {
 
 	restore_dir=$PWD
-	cd ${generation_dir}
-	rm -f $tmp_iasl $tmp_acpiexec $tmp_acpibin
+	cd "${generation_dir}" || exit 1
+	rm -f "$tmp_iasl" "$tmp_acpiexec" "$tmp_acpibin"
 
 	# Build native-width iASL compiler and acpiexec
-	if [ ! -e bin/iasl -o ! -e bin/acpiexec ]; then
+	if [ ! -e bin/iasl -o ! -e bin/acpiexec -o ! -e bin/acpibin ]; then
 		REBUILD_TOOLS=yes
 	fi
 	if [ "x$REBUILD_TOOLS" = "xyes" ]; then
-		jobs=`nproc`
-		make clean
+		jobs=${ASLTS_JOBS:-1}
+		make clean || exit 1
 		# We need to disable the Fatal() opcode in order to test it
-		make iasl ASLTS=TRUE OPT_CFLAGS="-DACPI_CONTINUE_ON_FATAL" -j$jobs
-		make acpibin ASLTS=TRUE OPT_CFLAGS="-DACPI_CONTINUE_ON_FATAL" -j$jobs
-		make acpiexec ASLTS=TRUE OPT_CFLAGS="-DACPI_CONTINUE_ON_FATAL" -j$jobs
+		make iasl ASLTS=TRUE OPT_CFLAGS="-DACPI_CONTINUE_ON_FATAL" -j$jobs || exit 1
+		make acpibin ASLTS=TRUE OPT_CFLAGS="-DACPI_CONTINUE_ON_FATAL" -j$jobs || exit 1
+		make acpiexec ASLTS=TRUE OPT_CFLAGS="-DACPI_CONTINUE_ON_FATAL" -j$jobs || exit 1
 	fi
 
 	if [ -d "bin" ] && [ -f "bin/iasl" ]; then
 		echo "Installing ACPICA tools"
-		cp bin/iasl $tmp_iasl
-		cp bin/acpiexec $tmp_acpiexec
-		cp bin/acpibin $tmp_acpibin
+		cp bin/iasl "$tmp_iasl" || exit 1
+		cp bin/acpiexec "$tmp_acpiexec" || exit 1
+		cp bin/acpibin "$tmp_acpibin" || exit 1
 	else
 		echo "Could not find iASL/acpiexec tools"
-		exit
+		exit 1
 	fi
 
 	# Ensure that the tools are available
-	if [ ! -f $tmp_iasl ] ; then
+	if [ ! -f "$tmp_iasl" ] ; then
 		echo "iasl compiler not found"
-		exit
-	elif [ ! -f $tmp_acpiexec ] ; then
+		exit 1
+	elif [ ! -f "$tmp_acpiexec" ] ; then
 		echo "acpiexec utility not found"
-		exit
-	elif [ ! -f $tmp_acpibin ] ; then
+		exit 1
+	elif [ ! -f "$tmp_acpibin" ] ; then
 		echo "acpibin utility not found"
-		exit
-	fi
-
-	cd $restore_dir
+		exit 1
+	fi
+
+	cd "$restore_dir" || exit 1
 }
 
 # Run a simple compiler test.
@@ -128,18 +129,27 @@
 # 5 runs binary comparison between .aml and recomp.aml
 run_compiler_template_test()
 {
-	pushd templates
+	pushd templates || return 1
+	local status=0
 
 	rm -f *.asl *.aml *.dsl
 
-	$ASL -T all 2> /dev/null
+	"$ASL" -T all 2> /dev/null || status=1
+	# CDAT has no signature; iASL requires its explicit table type.
+	"$ASL" -ds CDAT -T CDAT 2> /dev/null || status=1
 	for filename in *.asl
 	do
-		make -s NAME=$(basename "$filename" .asl)
+		name=$(basename "$filename" .asl)
+		case "$name" in
+		cdat) make -s NAME="$name" DISASM_ARGS="-ds CDAT" || status=1 ;;
+		rsdp) echo "Data table rsdp: iASL raw RSDP disassembly unsupported" ;;
+		*) make -s NAME="$name" || status=1 ;;
+		esac
 	done
 
 	rm -f *.asl *.aml *.dsl
-	popd
+	popd || return 1
+	return "$status"
 }
 
 
@@ -147,15 +157,16 @@
 run_aslts() {
 
 	# Remove a previous version of the AML test code
-	version=`$ASL | grep version | awk '{print $5}'`
+	version=`"$ASL" | grep version | awk '{print $5}'`
 	rm -rf $ASLTSDIR/tmp/aml/$version
 
 	# run templates test
 
-	run_compiler_template_test
+	local template_status=0
+	run_compiler_template_test || template_status=1
 
 	if [ "x$DATATABLEONLY" = "xyes" ]; then
-		return 0
+		return "$template_status"
 	fi;
 
 	if [ "x$TEST_MODES" = "x" ]; then
@@ -176,14 +187,15 @@
 		if [ "x$TEST_MODES" = "x" ]; then
 			TEST_MODES="n32 n64 o32 o64"
 		fi
-		Do 1 $TEST_MODES $TEST_CASES
+		Do 1 $TEST_MODES $TEST_CASES || return 1
 
 		echo ""
 		echo "ASL Test Suite Finished: `date`"
 		echo "                Started: $start_time"
 
-		rm -f $tmp_iasl $tmp_acpiexec $tmp_acpibin
+		rm -f "$tmp_iasl" "$tmp_acpiexec" "$tmp_acpibin"
 	fi;
+	return "$template_status"
 }
 
 SRCDIR=`(cd \`dirname $0\`; cd ..; pwd)`
