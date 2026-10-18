# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Run in a fresh installed Tcl 9.1 process with an X11 display.
namespace eval contract {
    variable checks 0
    variable mounted 0
    variable images {}
    variable timer {}
    variable backgroundErrors {}
}

proc contract::check {condition description} {
    if {![uplevel 1 [list expr $condition]]} {
        error $description
    }
    variable checks
    incr checks
}

proc contract::await {condition description} {
    set deadline [expr {[clock milliseconds] + 5000}]
    while {![uplevel 1 [list expr $condition]]} {
        if {[clock milliseconds] >= $deadline} {
            error "Timed out: $description"
        }
        after 10 {set ::contract::tick 1}
        vwait ::contract::tick
    }
}

proc contract::run {} {
    variable mounted
    variable images
    variable timer
    if {[package vcompare [info patchlevel] 9.1] < 0} {
        error "Tcl 9.1 or newer is required"
    }
    if {[llength $::argv] != 2} {
        error "Usage: tclsh tk-installed.tcl NEW_OUTPUT_DIRECTORY TK_SHARED_LIBRARY"
    }
    lassign $::argv output library
    if {[file exists $output] || ![file isfile $library]} {
        error "The output directory must be new; the installed Tk library must exist"
    }
    if {![info exists ::env(DISPLAY)] || $::env(DISPLAY) eq ""} {
        error "An X11 DISPLAY is required"
    }
    if {[llength [info commands ::winfo]]} {
        error "Use a fresh tclsh process without a loaded Tk library"
    }
    set output [file normalize $output]
    set library [file normalize $library]
    set ::argv {}
    set ::argc 0
    file mkdir $output

    # Load actual package scripts from the ZipFS appended to its installed DSO.
    # This leaves the installed external script tree intact.
    zipfs mount $library /tk-installed-contract
    set mounted 1
    set ::tk_library //zipfs:/tk-installed-contract/tk_library
    set ::env(TK_LIBRARY) $::tk_library
    check {[file isfile [file join $::tk_library tk.tcl]]} \
        "The installed Tk library has no embedded tk.tcl"
    set timer [after 15000 {
        puts stderr "FAIL: Tk installed contract exceeded its event-loop deadline"
        exit 1
    }]
    package require -exact tk 9.1.0
    check {[tk windowingsystem] eq "x11"} "Tk did not select X11"
    check {$::tk_library eq "//zipfs:/tk-installed-contract/tk_library"} \
        "Tk did not initialize from the selected embedded script tree"
    check {[lindex [file system [file join $::tk_library tk.tcl]] 0] eq "zipfs"} \
        "Tk scripts did not use ZipFS"
    set loaded {}
    foreach item [info loaded] {
        if {[string equal -nocase [lindex $item 1] tk]} {
            lappend loaded [file normalize [lindex $item 0]]
        }
    }
    check {$loaded eq [list $library]} "Tk loaded a different shared library"

    # Background callback failures must fail this process, not open a dialog.
    proc ::bgerror {message} {lappend ::contract::backgroundErrors $message}
    wm title . "Installed Tk contract"
    wm geometry . 420x260+0+0
    set unicode "Tcl/Tk: Ελληνικά 日本語 שלום \U0001f642"
    text .text -width 36 -height 3 -font TkDefaultFont
    .text insert 1.0 $unicode
    .text tag add sample 1.0 end-1c
    pack .text -fill x
    check {[.text get 1.0 end-1c] eq $unicode} "Text Unicode content differs"
    check {[.text count -chars 1.0 end-1c] == [string length $unicode]} \
        "Text character count differs"
    check {[.text tag ranges sample] eq [list 1.0 "1.[string length $unicode]"]} \
        "Text tag indices differ"
    check {[font metrics TkDefaultFont -linespace] > 0} "Font metrics are empty"
    check {[font measure TkDefaultFont $unicode] > 0} "Text has no measured width"

    ttk::button .button -text $unicode -command {incr ::contract::invoked}
    pack .button
    set ::contract::invoked 0
    .button invoke
    check {$::contract::invoked == 1} "The themed button command did not run"
    check {[.button cget -text] eq $unicode} "Themed widget Unicode content differs"

    set image [image create photo -width 3 -height 2]
    lappend images $image
    $image put {{#ff0000 #00ff00 #0000ff} {#ffffff #123456 #000000}}
    $image transparency set 1 0 128 -alpha
    set png [file join $output pixels.png]
    $image write $png -format png
    set channel [open $png rb]
    try {
        set signature [read $channel 8]
    } finally {
        close $channel
    }
    check {[binary encode hex $signature] eq "89504e470d0a1a0a"} \
        "The PNG file signature differs"
    set disk [image create photo -file $png -format png]
    lappend images $disk
    set memory [image create photo -data [$image data -format png] -format png]
    lappend images $memory
    foreach copy [list $disk $memory] {
        check {[image width $copy] == 3 && [image height $copy] == 2} \
            "PNG dimensions differ"
        for {set y 0} {$y < 2} {incr y} {
            for {set x 0} {$x < 3} {incr x} {
                check {[$copy get $x $y] eq [$image get $x $y]} \
                    "PNG RGB differs at $x,$y"
                check {[$copy transparency get $x $y -alpha] == \
                    [$image transparency get $x $y -alpha]} \
                    "PNG alpha differs at $x,$y"
            }
        }
    }
    label .image -image $disk
    pack .image
    canvas .canvas -width 80 -height 30
    set rectangle [.canvas create rectangle 2 3 20 25 -fill red]
    pack .canvas
    check {[.canvas coords $rectangle] eq {2.0 3.0 20.0 25.0}} \
        "Canvas coordinates differ"

    wm deiconify .
    await {[winfo ismapped .] && [winfo ismapped .button]} "X11 window mapping"
    check {[winfo id .] != 0 && [winfo id .button] != 0} "X11 window IDs are empty"
    check {[winfo width .] > 1 && [winfo height .] > 1} "X11 geometry is empty"
    check {[winfo server .] ne ""} "The X11 server identity is empty"

    set ::contract::delivered {}
    bind .button <<InstalledContract>> {set ::contract::delivered %d}
    event generate .button <<InstalledContract>> -when tail -data $unicode
    await {$::contract::delivered eq $unicode} "queued virtual event delivery"
    check {$::contract::delivered eq $unicode} "Virtual event Unicode data differs"
    set ::contract::idle 0
    after idle {set ::contract::idle 1}
    await {$::contract::idle == 1} "idle callback delivery"
    check {$::contract::idle == 1} "The idle callback did not run"
    set ::contract::destroyed 0
    bind .button <Destroy> {incr ::contract::destroyed}
    destroy .button
    check {![winfo exists .button] && $::contract::destroyed == 1} \
        "Window destruction did not deliver its event"
    update
    check {$::contract::backgroundErrors eq {}} \
        "Background callback errors: $::contract::backgroundErrors"
    puts "PASS: Tcl [info patchlevel], Tk [package provide tk]; $::contract::checks checks"
    puts "X11: [winfo server .]"
    puts "Tk library: $library"
    puts "Tk scripts: $::tk_library"
    puts "PNG: $png"
}

set status [catch {contract::run} message options]
if {$::contract::timer ne ""} {
    after cancel $::contract::timer
}
set cleanupErrors {}
foreach image $::contract::images {
    if {[catch {image delete $image} cleanupError]} {
        lappend cleanupErrors $cleanupError
    }
}
if {[llength [info commands ::winfo]] &&
        ![catch {winfo exists .} exists] && $exists} {
    if {[catch {destroy .} cleanupError]} {
        lappend cleanupErrors $cleanupError
    }
}
if {$::contract::mounted} {
    if {[catch {zipfs unmount /tk-installed-contract} cleanupError]} {
        lappend cleanupErrors $cleanupError
    }
}
if {$status} {
    puts stderr "FAIL: $message"
    puts stderr [dict get $options -errorinfo]
    exit 1
}
if {$cleanupErrors ne {}} {
    puts stderr "FAIL: Cleanup errors: $cleanupErrors"
    exit 1
}
exit 0
