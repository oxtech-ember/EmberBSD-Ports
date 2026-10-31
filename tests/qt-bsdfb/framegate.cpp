// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).

#include "qbsdfbframegate_p.h"

#include <QRect>
#include <QRegion>
#include <QSize>
#include <QtGlobal>

#include <iostream>

namespace {

using QBsdFb::FrameGate;
using WindowId = QT_PREPEND_NAMESPACE(quintptr);

constexpr WindowId firstWindow = static_cast<WindowId>(1);
constexpr WindowId secondWindow = static_cast<WindowId>(2);

int failures = 0;

void check(bool condition, const char *description)
{
    if (!condition) {
        std::cerr << "FAIL: " << description << '\n';
        ++failures;
    }
}

void testDisabledPreservationIsAlwaysOpen()
{
    FrameGate gate(false);
    const QSize size(4, 3);
    check(gate.allowsRedraw(), "preservation-disabled gate starts open");
    gate.resetForWindow(firstWindow, size);
    check(gate.allowsRedraw(), "reset cannot close preservation-disabled gate");
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 1, 1))),
          "already-open gate does not report another unlock");
}

void testFullCoverageUnlocksOnce()
{
    const QSize size(4, 3);
    FrameGate gate(true);
    check(!gate.allowsRedraw(), "preservation-enabled gate starts closed");
    gate.resetForWindow(firstWindow, size);
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "first half does not unlock the gate");
    check(!gate.allowsRedraw(), "gate remains closed after partial coverage");
    check(gate.addFlush(firstWindow, size, QRegion(QRect(2, 0, 2, 3))),
          "second half completes coverage and unlocks");
    check(gate.allowsRedraw(), "gate opens after full coverage");
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 4, 3))),
          "full flush after unlock does not report another transition");
}

void testGapRequiresItsOwnCoverage()
{
    const QSize size(5, 3);
    FrameGate gate(true);
    gate.resetForWindow(firstWindow, size);
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "left strip leaves a gap");
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(3, 0, 2, 3))),
          "right strip does not cover the center gap");
    check(!gate.allowsRedraw(), "overlapping extent does not count as full coverage");
    check(gate.addFlush(firstWindow, size, QRegion(QRect(2, 0, 1, 3))),
          "center strip completes coverage");
}

void testFlushesAreClippedAndInvalidGeometryDoesNotUnlock()
{
    const QSize size(4, 3);
    FrameGate gate(true);
    gate.resetForWindow(firstWindow, size);
    check(!gate.addFlush(firstWindow, size, QRegion()), "empty flush adds no coverage");
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(5, 0, 2, 3))),
          "outside flush adds no coverage");
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(-2, 1, 1, 1))),
          "negative outside flush adds no coverage");
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(-2, 0, 2, 3))),
          "partially negative flush is clipped to the window");
    check(!gate.allowsRedraw(), "clipped partial coverage does not unlock");
    check(!gate.addFlush(firstWindow, QSize(0, 3), QRegion(QRect(0, 0, 4, 3))),
          "zero-width window does not unlock");
    check(!gate.addFlush(firstWindow, QSize(4, -1), QRegion(QRect(0, 0, 4, 3))),
          "negative-height window does not unlock");
    check(!gate.addFlush(static_cast<WindowId>(0), size, QRegion(QRect(0, 0, 4, 3))),
          "null window identity does not unlock");
    check(!gate.allowsRedraw(), "invalid coverage leaves the gate closed");
}

void testWindowAndSizeChangesDiscardStaleCoverage()
{
    const QSize size(4, 3);
    FrameGate gate(true);
    gate.resetForWindow(firstWindow, size);
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "first window has partial coverage");
    check(!gate.addFlush(secondWindow, size, QRegion(QRect(2, 0, 2, 3))),
          "new window discards old coverage and counts its flush");
    check(!gate.allowsRedraw(), "new window remains partially covered");
    check(gate.addFlush(secondWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "matching flushes for new window complete coverage");

    FrameGate resized(true);
    resized.resetForWindow(firstWindow, size);
    check(!resized.addFlush(firstWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "old size has partial coverage");
    const QSize larger(5, 3);
    check(!resized.addFlush(firstWindow, larger, QRegion(QRect(2, 0, 3, 3))),
          "new size discards old coverage and counts its flush");
    check(!resized.allowsRedraw(), "resized window remains partially covered");
    check(resized.addFlush(firstWindow, larger, QRegion(QRect(0, 0, 2, 3))),
          "matching flushes for new size complete coverage");
}

void testExplicitSameKeyResetDiscardsCoverage()
{
    const QSize size(4, 3);
    FrameGate gate(true);
    gate.resetForWindow(firstWindow, size);
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "first flush leaves half the window uncovered");
    gate.resetForWindow(firstWindow, size);
    check(!gate.allowsRedraw(), "explicit same-key reset keeps gate closed");
    check(!gate.addFlush(firstWindow, size, QRegion(QRect(2, 0, 2, 3))),
          "post-reset matching flush starts a new coverage set");
    check(gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "post-reset matching flushes form a complete union");
}

void testCursorOrExposureWithoutFlushCannotUnlock()
{
    FrameGate gate(true);
    gate.resetForWindow(firstWindow, QSize(4, 3));
    // Cursor and exposure redraws do not add backing-store flush coverage.
    check(!gate.allowsRedraw(), "redraw without a flush leaves the gate closed");
}

void testGateStaysOpenAfterFirstCompleteFrame()
{
    FrameGate gate(true);
    const QSize size(4, 3);
    gate.resetForWindow(firstWindow, size);
    check(gate.addFlush(firstWindow, size, QRegion(QRect(0, 0, 4, 3))),
          "complete first flush makes the frame ready");
    gate.framePresented();
    gate.resetForWindow(secondWindow, QSize(8, 6));
    check(gate.allowsRedraw(), "presented frame permanently opens the gate");
}

void testPrematurePresentationDoesNotSealTheGate()
{
    const QSize size(4, 3);
    const QRegion full(QRect(0, 0, 4, 3));
    FrameGate gate(true);
    gate.resetForWindow(firstWindow, size);
    gate.framePresented();
    check(!gate.allowsRedraw(), "presentation before a full flush leaves gate closed");
    check(!gate.hasPresentedFrame(), "presentation before readiness does not seal the gate");
    check(gate.addFlush(firstWindow, size, full), "full coverage makes frame ready");
    check(gate.allowsRedraw(), "ready frame can be redrawn");
    check(!gate.hasPresentedFrame(), "ready state is distinct from presented state");
    gate.framePresented();
    check(gate.hasPresentedFrame(), "actual presentation seals a ready frame");
    gate.resetForWindow(secondWindow, QSize(8, 6));
    check(gate.allowsRedraw(), "sealed presentation survives later key changes");
}

void testReadyGateCanBeReopenedBeforePresentation()
{
    const QSize size(4, 3);
    const QRegion full(QRect(0, 0, 4, 3));
    FrameGate gate(true);
    gate.resetForWindow(firstWindow, size);
    check(gate.addFlush(firstWindow, size, full), "first complete flush readies the gate");
    check(!gate.addFlush(firstWindow, size, full),
          "additional flush does not repeat the ready transition");
    gate.resetForWindow(firstWindow, size);
    check(!gate.allowsRedraw(), "same-key resize/reset invalidates unpresented readiness");
    check(gate.addFlush(firstWindow, size, full),
          "complete coverage after reset reports a new ready transition");
}

void testPendingFrameResetClosesUntilAFrameIsPresented()
{
    const QSize size(4, 3);
    const QRegion full(QRect(0, 0, 4, 3));
    FrameGate sameWindow(true);
    sameWindow.resetForWindow(firstWindow, size);
    check(sameWindow.addFlush(firstWindow, size, full),
          "complete flush makes same-window frame ready");
    check(sameWindow.allowsRedraw(), "complete flush allows its pending redraw");
    sameWindow.resetForWindow(firstWindow, size);
    check(!sameWindow.allowsRedraw(),
          "same-key reset before presentation closes the gate again");
    check(!sameWindow.addFlush(firstWindow, size, QRegion(QRect(0, 0, 2, 3))),
          "partial coverage after same-key reset stays closed");
    check(!sameWindow.allowsRedraw(),
          "pending full coverage was discarded by same-key reset");
    check(sameWindow.addFlush(firstWindow, size, full),
          "new full flush reopens after same-key reset");

    FrameGate replacedWindow(true);
    replacedWindow.resetForWindow(firstWindow, size);
    check(replacedWindow.addFlush(firstWindow, size, full),
          "complete flush makes replaced-window frame ready");
    const QSize larger(8, 6);
    replacedWindow.resetForWindow(secondWindow, larger);
    check(!replacedWindow.allowsRedraw(),
          "window replacement before presentation closes the gate");
    check(!replacedWindow.addFlush(secondWindow, larger,
                                   QRegion(QRect(0, 0, 4, 6))),
          "partial replacement-window coverage stays closed");
    check(!replacedWindow.allowsRedraw(),
          "old window readiness cannot expose replacement window");
    check(replacedWindow.addFlush(secondWindow, larger,
                                  QRegion(QRect(0, 0, 8, 6))),
          "replacement-window full coverage becomes ready");
}

} // namespace

int main()
{
    testDisabledPreservationIsAlwaysOpen();
    testFullCoverageUnlocksOnce();
    testGapRequiresItsOwnCoverage();
    testFlushesAreClippedAndInvalidGeometryDoesNotUnlock();
    testWindowAndSizeChangesDiscardStaleCoverage();
    testExplicitSameKeyResetDiscardsCoverage();
    testCursorOrExposureWithoutFlushCannotUnlock();
    testGateStaysOpenAfterFirstCompleteFrame();
    testPrematurePresentationDoesNotSealTheGate();
    testReadyGateCanBeReopenedBeforePresentation();
    testPendingFrameResetClosesUntilAFrameIsPresented();
    return failures == 0 ? 0 : 1;
}
