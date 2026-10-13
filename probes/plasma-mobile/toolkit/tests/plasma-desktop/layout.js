// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Read-only Plasma 6.7 layout assertions.
(function () {
    function require(condition, description) {
        if (!condition) {
            throw new Error(description);
        }
    }
    require(screenCount === 1, "Expected one virtual output");
    var geometry = screenGeometry(0);
    require(geometry.width === 1280 && geometry.height === 1024,
            "Unexpected virtual output size");
    var desktop = desktops().filter(function (item) { return item.screen === 0; });
    require(desktop.length === 1 && desktop[0].type === "org.kde.plasma.folder",
            "The default Folder View desktop is missing");
    var panel = panels().filter(function (item) { return item.screen === 0; });
    require(panel.length === 1 && panel[0].type === "org.kde.panel",
            "The default panel is missing");
    var types = panel[0].widgets().map(function (item) { return item.type; });
    var required = ["org.kde.plasma.kickoff", "org.kde.plasma.pager",
                    "org.kde.plasma.icontasks", "org.kde.plasma.systemtray",
                    "org.kde.plasma.digitalclock", "org.kde.plasma.showdesktop"];
    required.forEach(function (type) {
        require(types.indexOf(type) !== -1, "Missing default applet: " + type);
    });
    print("PASS: default desktop, panel and six applet models on 1280x1024");
})();
