// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/calctrl.h>
#include <wx/timer.h>
#include <cstdio>
#include <stdexcept>
#include <type_traits>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static_assert(std::is_same<wxCalendarCtrl, wxGenericCalendarCtrl>::value,
              "GTK4 must use the existing common calendar");

static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }

class CalendarContract : public wxApp
{
    wxFrame* frame = NULL;
    wxCalendarCtrl* calendar = NULL;
    wxTimer timer;
    int result = 1;

    void Key(int code)
    {
        wxKeyEvent event(wxEVT_CHAR);
        event.m_keyCode = code;
        event.SetEventObject(calendar);
        calendar->GetEventHandler()->ProcessEvent(event);
    }

    void Run()
    {
        timer.Stop();
        try
        {
            const wxDateTime leap(29, wxDateTime::Feb, 2028);
            int selected = 0, pages = 0, activated = 0;
            calendar->Bind(wxEVT_CALENDAR_SEL_CHANGED,
                [&](wxCalendarEvent&) { ++selected; });
            calendar->Bind(wxEVT_CALENDAR_PAGE_CHANGED,
                [&](wxCalendarEvent&) { ++pages; });
            calendar->Bind(wxEVT_CALENDAR_DOUBLECLICKED,
                [&](wxCalendarEvent& event)
                {
                    Check(event.GetDate() == calendar->GetDate(),
                          "activation carries the selected date");
                    ++activated;
                });
            Check(calendar->GetDate() == leap, "leap day round trip");
            const wxDateTime lower(1, wxDateTime::Feb, 2028);
            const wxDateTime upper(31, wxDateTime::Mar, 2028);
            Check(calendar->SetDateRange(lower, upper), "set bounded range");
            wxDateTime actualLower, actualUpper;
            Check(calendar->GetDateRange(&actualLower, &actualUpper) &&
                  actualLower == lower && actualUpper == upper,
                  "range round trip");
            Check(!calendar->SetDate(wxDateTime(1, wxDateTime::Apr, 2028)) &&
                  calendar->GetDate() == leap, "out-of-range date rejected");
            Check(calendar->SetDate(leap) && selected == 0 && pages == 0,
                  "programmatic date change is silent");
            Check(calendar->EnableMonthChange(false), "lock month");
            Key(WXK_PAGEDOWN);
            Check(calendar->GetDate() == leap && selected == 0 && pages == 0,
                  "month lock covers keyboard navigation");
            Check(calendar->EnableMonthChange(true), "unlock month");
            Key(WXK_PAGEDOWN);
            Check(calendar->GetDate() == wxDateTime(29, wxDateTime::Mar, 2028) &&
                  selected == 1 && pages == 1, "keyboard changes month once");
            Check(calendar->SetDate(leap), "restore February");
            calendar->Mark(29, true);
            Check(calendar->GetAttr(29) != NULL, "day mark preserved");
            calendar->Mark(29, false);

            wxPoint dayPoint(-1, -1);
            const wxSize size = calendar->GetClientSize();
            // HitTest recalculates text geometry. Locate a date row, the
            // weekday column and then the date with linear scans, rather
            // than measuring every pixel-grid point in the entire control.
            int dateRow = -1, weekdayColumn = -1;
            for (int y = 0; y < size.y; y += 4)
            {
                wxDateTime day;
                if (calendar->HitTest(wxPoint(size.x / 2, y), &day) == wxCAL_HITTEST_DAY)
                { dateRow = y; break; }
            }
            Check(dateRow >= 0, "mapped calendar exposes a date row");
            for (int x = 0; x < size.x; x += 4)
            {
                wxDateTime day;
                if (calendar->HitTest(wxPoint(x, dateRow), &day) == wxCAL_HITTEST_DAY &&
                    day.GetWeekDay() == leap.GetWeekDay())
                { weekdayColumn = x; break; }
            }
            Check(weekdayColumn >= 0, "mapped calendar exposes the weekday column");
            for (int y = 0; y < size.y; y += 4)
            {
                wxDateTime day;
                if (calendar->HitTest(wxPoint(weekdayColumn, y), &day) == wxCAL_HITTEST_DAY &&
                    day == leap)
                { dayPoint = wxPoint(weekdayColumn, y); break; }
            }
            Check(dayPoint.x >= 0, "mapped calendar exposes the leap-day cell");
            wxMouseEvent click(wxEVT_LEFT_DCLICK);
            click.SetPosition(dayPoint);
            click.SetEventObject(calendar);
            calendar->GetEventHandler()->ProcessEvent(click);
            Check(activated == 1, "double click activates one calendar date");
            result = 0;
            std::puts("calendar4 contract PASS");
        }
        catch (const std::exception& error)
        { std::fprintf(stderr, "calendar4: %s\n", error.what()); }
        frame->Destroy();
        ExitMainLoop();
    }

public:
    bool OnInit() wxOVERRIDE
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 calendar contract");
        calendar = new wxCalendarCtrl(frame, wxID_ANY,
            wxDateTime(29, wxDateTime::Feb, 2028), wxDefaultPosition,
            wxDefaultSize, wxCAL_MONDAY_FIRST | wxCAL_SHOW_WEEK_NUMBERS);
        frame->SetClientSize(calendar->GetBestSize());
        calendar->SetSize(frame->GetClientSize());
        frame->Show();
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Run(); });
        timer.StartOnce(200);
        return true;
    }
    int OnRun() wxOVERRIDE { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(CalendarContract);
