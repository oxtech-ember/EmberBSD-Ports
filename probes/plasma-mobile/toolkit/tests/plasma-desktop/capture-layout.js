// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Add visible content only in the private test HOME.
(function () {
    var desktop = desktops().filter(function (item) { return item.screen === 0; })[0];
    if (!desktop || desktop.widgets("org.kde.plasma.digitalclock").length !== 0) {
        throw new Error("Expected an empty test desktop");
    }
    var widget = desktop.addWidget("org.kde.plasma.digitalclock", 128, 128, 384, 256);
    if (!widget || widget.type !== "org.kde.plasma.digitalclock") {
        throw new Error("The capture widget did not load");
    }
    print("PASS: capture widget created");
})();
