#!/usr/bin/env python3

import pyautogui
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import pytesseract
import threading
from pynput import keyboard
from PIL import Image
import random
import time
import sys

class BaristaTracker(Tk):
    def __init__(self):
        super().__init__()
        self.title("Barista Tracker")
        self.geometry("400x200")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.status_label = Label(self, text="Status: OFF")
        self.status_label.pack(pady=5)

        self.button_container = Frame(self)
        self.button_container.pack()
        self.help_btn = ttk.Button(self.button_container, text="Help", command=self.show_help)
        self.help_btn.grid(row=0, column=0)
        self.settings_btn = ttk.Button(self.button_container, text="Settings", command=self.show_settings)
        self.settings_btn.grid(row=0, column=1)

        self.help_window_instance = None
        self.tracker_enabled = False
        self.keyboard = keyboard.Controller()
        self.spam_thread = None
        self.spamming = False
        self.randomlow = 0.1
        self.randomhigh = 0.5
        self.start_hotkey_listener()

    def start_hotkey_listener(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f6:
                    self.toggle_tracker()
                elif key == keyboard.Key.f7:
                    self.destroy()
                    sys.exit()
            except Exception as e:
                print(f"Hotkey error: {e}")

        threading.Thread(target=lambda: keyboard.Listener(on_press=on_press).run(), daemon=True).start()

    def toggle_tracker(self):
        self.tracker_enabled = not self.tracker_enabled
        status_text = "ON" if self.tracker_enabled else "OFF"
        self.status_label.config(text=f"Status: {status_text}")

        if self.tracker_enabled:
            self.spamming = True
            self.spam_thread = threading.Thread(target=self.spam_key_e, daemon=True)
            self.spam_thread.start()
        else:
            self.spamming = False

    def spam_key_e(self):
        while self.spamming:
            self.keyboard.press('e')
            self.keyboard.release('e')
            time.sleep(random.uniform(self.randomlow, self.randomhigh))  # Sleep between 100ms and 500ms

    def show_help(self):
        if self.help_window_instance is not None and self.help_window_instance.winfo_exists():
            self.help_window_instance.focus()
            return
        self.freeze_gui()
        self.help_window_instance = Toplevel(self)
        self.help_window_instance.title("Help")
        self.help_window_instance.geometry("400x150")
        self.help_window_instance.resizable(False, False)

        help_text = (
            "F6 = Toggle ON/OFF\n"
            "F7 = Emergency Stop"
        )
        Label(self.help_window_instance, text=help_text, justify=LEFT).pack(padx=15, pady=15, fill=BOTH, expand=True)

        def on_close():
            if self.help_window_instance is not None and self.help_window_instance.winfo_exists():
                self.help_window_instance.destroy()
            self.help_window_instance = None
            self.help_btn.state(['!disabled'])
            self.unfreeze_gui()

        self.help_window_instance.protocol("WM_DELETE_WINDOW", on_close)

    def show_settings(self):
        self.freeze_gui()
        settings_window = Toplevel(self)
        settings_window.title("Settings")
        settings_window.geometry("400x200")
        settings_window.resizable(False, False)

        Label(settings_window, text="Lower bound (sec)").grid(row=0, column=0, padx=10, pady=10)
        self.lower_bound_entry = ttk.Entry(settings_window, width=5)
        self.lower_bound_entry.grid(row=0, column=1, padx=10, pady=10)
        self.lower_bound_entry.insert(0, str(self.randomlow))
        Label(settings_window, text="Upper bound (sec)").grid(row=1, column=0, padx=10, pady=10)
        self.upper_bound_entry = ttk.Entry(settings_window, width=5)
        self.upper_bound_entry.grid(row=1, column=1, padx=10, pady=10)
        self.upper_bound_entry.insert(0, str(self.randomhigh))

        self.save_settings_btn = ttk.Button(settings_window, text="Save", command=self.save_settings)
        self.save_settings_btn.grid(row=2, column=0, columnspan=2, pady=10)

        def on_close():
            settings_window.destroy()
            self.unfreeze_gui()

        settings_window.protocol("WM_DELETE_WINDOW", on_close)

    def save_settings(self):
        try:
            lower_bound = float(self.lower_bound_entry.get())
            upper_bound = float(self.upper_bound_entry.get())
            if lower_bound < 0 or upper_bound < 0 or lower_bound >= upper_bound:
                raise ValueError("Invalid bounds")
            self.randomlow = lower_bound
            self.randomhigh = upper_bound
            messagebox.showinfo("Settings", "Settings saved successfully!")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def freeze_gui(self):
        def _disable_all(widget):
            try:
                widget.configure(state='disabled')
            except:
                pass
            for child in widget.winfo_children():
                _disable_all(child)
        _disable_all(self)

    def unfreeze_gui(self):
        def _enable_all(widget):
            try:
                widget.configure(state='normal')
            except:
                pass
            for child in widget.winfo_children():
                _enable_all(child)
        _enable_all(self)

if __name__ == "__main__":
    app = BaristaTracker()
    app.mainloop()