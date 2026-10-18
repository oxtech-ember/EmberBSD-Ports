# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run with the current native Tcl provider.
if {[package vcompare [info patchlevel] 9.1] < 0} {
    error "Tcl 9.1 or newer is required"
}
if {[llength $argv] != 1 || [file exists [lindex $argv 0]]} {
    error "Usage: tclsh tcl9-host.tcl NEW_OUTPUT_DIRECTORY"
}
set output [file normalize [lindex $argv 0]]
file mkdir $output
set input [file join $output scripts]
file mkdir $input
set channel [open [file join $input unicode.txt] w]
fconfigure $channel -encoding utf-8
puts -nonewline $channel "Tcl 9.1: Ελληνικά 日本語"
close $channel
set archive [file join $output scripts.zip]
zipfs mkzip $archive $input $input
set mount [zipfs mount $archive /host-contract]
set channel [open //zipfs:/host-contract/unicode.txt r]
fconfigure $channel -encoding utf-8
set actual [read $channel]
close $channel
if {$actual ne "Tcl 9.1: Ελληνικά 日本語"} {
    error "ZipFS Unicode round trip differs"
}
zipfs unmount /host-contract

package require Itcl 4.3.8
itcl::class HostCounter {
    private variable value 40
    method next {} { incr value }
}
HostCounter counter
if {[counter next] != 41 || [counter next] != 42} {
    error "Itcl state differs"
}
itcl::delete object counter
itcl::delete class HostCounter

package require sqlite3 3.53.4
sqlite3 database :memory:
database eval {CREATE TABLE inputs (value INTEGER); INSERT INTO inputs VALUES (41)}
if {[database onecolumn {SELECT value + 1 FROM inputs}] != 42} {
    error "SQLite result differs"
}
database close

package require tdbc::sqlite3 1.1.15
tdbc::sqlite3::connection create connection :memory:
set statement [connection prepare {SELECT 6 * 7 AS answer}]
set rows [$statement allrows -as dicts]
if {[dict get [lindex $rows 0] answer] != 42} {
    error "TDBC result differs"
}
$statement close
connection close

package require Thread 3.0.7
set worker [thread::create {thread::wait}]
if {[thread::send $worker {expr {6 * 7}}] != 42} {
    error "Thread result differs"
}
thread::release $worker
puts "PASS: Tcl [info patchlevel]; ZipFS, Unicode, Itcl, system SQLite, TDBC and Thread"
