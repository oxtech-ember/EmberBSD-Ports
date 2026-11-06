// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Run with a real GTK4 display and the Ports-patched wxWidgets library.
#include <wx/wx.h>
#include <wx/menu.h>
#include <wx/accel.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }

class MenuContract : public wxApp
{
    wxFrame* frame = NULL;
    wxMenuBar* bar = NULL;
    wxMenu* menu = NULL;
    wxMenuItem* command = NULL;
    int commands = 0, opens = 0, closes = 0, last = wxID_NONE, result = 1;
    bool finished = false;
    wxTimer deadline;
    void Finish(int status, const char* message)
    {
        if (finished) return;
        finished = true;
        deadline.Stop();
        result = status;
        std::fprintf(status ? stderr : stdout, "%s\n", message);
        if (frame) frame->Destroy();
        ExitMainLoop();
    }
    bool Shortcut(guint key)
    {
        GtkWidget* host = GTK_WIDGET(frame->GetHandle());
        GListModel* controllers = gtk_widget_observe_controllers(host);
        bool activated = false;
        for (guint i = 0; !activated && i < g_list_model_get_n_items(controllers); ++i)
        {
            GtkEventController* controller = GTK_EVENT_CONTROLLER(g_list_model_get_item(controllers, i));
            if (GTK_IS_SHORTCUT_CONTROLLER(controller))
            {
                GListModel* list = G_LIST_MODEL(controller);
                for (guint j = 0; !activated && j < g_list_model_get_n_items(list); ++j)
                {
                    GtkShortcut* shortcut = GTK_SHORTCUT(g_list_model_get_item(list, j));
                    GtkShortcutTrigger* trigger = gtk_shortcut_get_trigger(shortcut);
                    if (GTK_IS_KEYVAL_TRIGGER(trigger) && gtk_keyval_trigger_get_keyval(GTK_KEYVAL_TRIGGER(trigger)) == key)
                        activated = gtk_shortcut_action_activate(gtk_shortcut_get_action(shortcut),
                            GTK_SHORTCUT_ACTION_EXCLUSIVE, host, gtk_shortcut_get_arguments(shortcut));
                    g_object_unref(shortcut);
                }
            }
            g_object_unref(controller);
        }
        g_object_unref(controllers);
        return activated;
    }
    void Run()
    {
        try
        {
            // Actual registered shortcut actions, not an emulated key mapper.
            Check(Shortcut(GDK_KEY_F6) && last == 200, "primary native shortcut dispatch");
            const int before = commands;
            bar->EnableTop(0, false);
            Check(!Shortcut(GDK_KEY_F6) && commands == before, "disabled top menu blocks shortcuts");
            bar->EnableTop(0, true);
            command->Enable(false);
            Check(!Shortcut(GDK_KEY_F6), "disabled item blocks shortcut");
            command->Enable(true);
            command->SetItemLabel("&Renamed\tF7");
            Check(!Shortcut(GDK_KEY_F6) && Shortcut(GDK_KEY_F7), "label mutation replaces primary accelerator");
            command->AddExtraAccel(wxAcceleratorEntry(wxACCEL_NORMAL, WXK_F8, 200));
            Check(Shortcut(GDK_KEY_F8), "extra accelerator dispatch");
            command->ClearExtraAccels();
            Check(!Shortcut(GDK_KEY_F8), "extra accelerator removal");
            wxMenuItem* detached = menu->Remove(command);
            Check(!Shortcut(GDK_KEY_F7), "removed item's shortcuts detached");
            menu->Append(detached);
            Check(Shortcut(GDK_KEY_F7), "reinserted item gets one live shortcut");

            wxMenu popup;
            wxMenuItem* toggle = popup.AppendCheckItem(300, "&Toggle");
            wxMenuItem* r1 = popup.AppendRadioItem(301, "Radio &one");
            wxMenuItem* separator = popup.AppendSeparator();
            wxMenuItem* r2 = popup.AppendRadioItem(302, "Radio &two");
            Check(r1->IsChecked() && r2->IsChecked(), "separate radio runs have independent defaults");
            popup.Delete(separator);
            Check(r1->IsChecked() && !r2->IsChecked(), "removing separator merges radio state coherently");
            const int afterCommands = commands;
            r2->Check(); toggle->Check();
            Check(!r1->IsChecked() && r2->IsChecked() && commands == afterCommands,
                  "programmatic check/radio changes do not emit commands");
            auto sub = new wxMenu;
            sub->Append(304, "Nested command");
            popup.AppendSubMenu(sub, "&Nested");
            CallAfter([this, &popup, toggle]()
            {
                try
                {
                    Check(popup.m_popupShown && gtk_widget_get_visible(popup.m_menu), "synchronous popup dispatches while open");
                    popup.Append(305, "Dynamically appended");
                    toggle->SetItemLabel("Changed while &open");
                    Check(gtk_widget_activate(toggle->GetMenuItem()), "native check row activation");
                }
                catch (const std::exception& e) { Finish(1, e.what()); }
            });
            Check(frame->PopupMenu(&popup, 20, 20), "popup returned after activation");
            if (finished) return;
            Check(!popup.m_popupShown && !toggle->IsChecked() && last == 300, "check command and popup closed state");
            Check(opens == closes && opens > 0, "one open and close event per popup lifecycle");

            // The old common wxMenuInvokingWindowSetter dereferenced this
            // deleted menu on returning from PopupMenu. Run under ASan too.
            wxMenu* destroyed = new wxMenu;
            wxMenuItem* destroyItem = destroyed->Append(306, "Destroy this menu");
            frame->Bind(wxEVT_MENU, [&destroyed](wxCommandEvent&) { delete destroyed; destroyed = NULL; }, 306);
            CallAfter([destroyItem]() { gtk_widget_activate(destroyItem->GetMenuItem()); });
            Check(frame->PopupMenu(destroyed, 20, 20) && !destroyed, "menu destruction exits popup safely");
            bar->Detach();
            Check(!Shortcut(GDK_KEY_F7), "menubar detach removes frame shortcut ownership");
            bar->Attach(frame);
            Check(Shortcut(GDK_KEY_F7), "menubar reattach restores accelerator ownership");
            Finish(0, "GTK4 menu mutation, actions, radio regroup, accelerators and popup destruction PASS");
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
    }
public:
    bool OnInit() override
    {
        wxLog::SetActiveTarget(new wxLogStderr);
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 menu contract", wxDefaultPosition, wxSize(500, 300));
        bar = new wxMenuBar;
        menu = new wxMenu;
        command = menu->Append(200, "&Command\tF6");
        bar->Append(menu, "&Test");
        frame->SetMenuBar(bar);
        frame->Bind(wxEVT_MENU, [this](wxCommandEvent& event) { ++commands; last = event.GetId(); });
        frame->Bind(wxEVT_MENU_OPEN, [this](wxMenuEvent&) { ++opens; });
        frame->Bind(wxEVT_MENU_CLOSE, [this](wxMenuEvent&) { ++closes; });
        deadline.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Finish(1, "menu contract timeout"); });
        deadline.StartOnce(15000);
        frame->Show();
        CallAfter(&MenuContract::Run);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(MenuContract);
