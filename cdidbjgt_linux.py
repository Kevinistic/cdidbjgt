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
        self.geometry("550x200")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.status_label = Label(self, text="Status: OFF")
        self.status_label.pack(pady=5)
        self.money_label = Label(self, text="Money: ")
        self.money_label.pack(pady=5)
        self.mph_label = Label(self, text="Money Per Hour: ")
        self.mph_label.pack(pady=5)

        self.button_container = Frame(self)
        self.button_container.pack()
        self.help_btn = ttk.Button(self.button_container, text="Help", command=self.show_help)
        self.help_btn.grid(row=0, column=0)
        self.recalibrate_btn = ttk.Button(self.button_container, text="Recalibrate", command=self.recalibrate)
        self.recalibrate_btn.grid(row=0, column=1)

        self.region = None
        self.help_window_instance = None
        self.f8_listener = None
        self._recalibrate_step = None
        self._recalibrate_coords = []
        self.previous_money = 0
        self.money_timestamp = None
        self.money_update_interval = 10_000  # 10,000 ms = 10 seconds
        self.tracker_enabled = False
        self.keyboard = keyboard.Controller()
        self.spam_thread = None
        self.spamming = False
        self.start_hotkey_listener()
        self.start_money_tracker()

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
            time.sleep(random.uniform(0.1, 0.5))  # Sleep between 100ms and 500ms

    def get_numbers_from_app(self, region):
        """
        Capture a region of the screen and extract numbers using OCR.
        :param region: (left, top, width, height)
        :return: Extracted numbers as string
        """
        screenshot = pyautogui.screenshot(region=region)
        text = pytesseract.image_to_string(screenshot, config='--psm 7 -c tessedit_char_whitelist=0123456789')
        print(f"OCR raw text: '{text}'")
        return text.strip()

    def get_current_money_value(self):
        money_text = self.money_label.cget("text").replace(",", "")
        digits = ''.join(c for c in money_text if c.isdigit())
        return int(digits) if digits else 0
    
    def start_money_tracker(self):
        if self.region:
            numbers = self.get_numbers_from_app(self.region)
            digits_only = ''.join(c for c in numbers if c.isdigit())
            if digits_only:
                formatted = "{:,}".format(int(digits_only))
                self.money_label.config(text=f"Money: {formatted}")

        current_money = self.get_current_money_value()
        if self.previous_money != 0:
            earned = current_money - self.previous_money
            earned_per_hour = earned * (3600 / (self.money_update_interval / 1000))
            if earned_per_hour >= 0:
                self.mph_label.config(text=f"Money Per Hour: {int(earned_per_hour):,}")
        self.previous_money = current_money
        self.after(self.money_update_interval, self.start_money_tracker)

    def show_help(self):
        if self.help_window_instance is not None and self.help_window_instance.winfo_exists():
            self.help_window_instance.focus()
            return
        self.freeze_gui()
        self.help_window_instance = Toplevel(self)
        self.help_window_instance.title("Help")
        self.help_window_instance.geometry("500x150")
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

    def recalibrate(self):
        # Start recalibration process with custom window
        self.freeze_gui()
        self._recalibrate_step = 0
        self._recalibrate_coords = []
        self._recalibrate_window = Toplevel(self)
        self._recalibrate_window.title("Recalibrate")
        self._recalibrate_window.geometry("500x150")
        self._recalibrate_window.resizable(False, False)
        self._recalibrate_label = Label(self._recalibrate_window, text="Move your cursor to the TOP LEFT of the region and press F8.", wraplength=320)
        self._recalibrate_label.pack(padx=15, pady=25, fill=BOTH, expand=True)
        self._recalibrate_window.protocol("WM_DELETE_WINDOW", self._close_recalibrate_window)
        self.start_f8_listener()

    def _close_recalibrate_window(self):
        # Called when recalibrate window is closed (manual or auto)
        if hasattr(self, "_recalibrate_window") and self._recalibrate_window.winfo_exists():
            self._recalibrate_window.destroy()
        self._recalibrate_window = None
        # If recalibration not finished, treat as cancelled
        if self._recalibrate_step is not None and self._recalibrate_step < 2:
            self._recalibrate_step = None
            self._recalibrate_coords = []
            self.region = None
            # Stop F8 listener if running
            if self.f8_listener is not None:
                try:
                    self.f8_listener.stop()
                except Exception:
                    pass
                self.f8_listener = None
        self.unfreeze_gui()

    def start_f8_listener(self):
        # Listen for F8 key press
        def on_press(key):
            try:
                if key == keyboard.Key.f8:
                    x, y = pyautogui.position()
                    self._recalibrate_coords.append((x, y))
                    self._recalibrate_step += 1
                    if self._recalibrate_step == 1:
                        # Update window text for next step
                        if hasattr(self, "_recalibrate_label"):
                            self._recalibrate_label.config(text="Now move your cursor to the BOTTOM RIGHT of the region and press F8.")
                    elif self._recalibrate_step == 2:
                        # Calculate region
                        x1, y1 = self._recalibrate_coords[0]
                        x2, y2 = self._recalibrate_coords[1]
                        left = min(x1, x2)
                        top = min(y1, y2)
                        width = abs(x2 - x1)
                        height = abs(y2 - y1)
                        self.region = (left, top, width, height)
                        # Show region set message
                        if hasattr(self, "_recalibrate_label"):
                            self._recalibrate_label.config(text=f"Region set to: {self.region}")
                        # Extract number and update label
                        numbers = self.get_numbers_from_app(self.region)
                        # Keep only digits (filter out all non-digit characters)
                        digits_only = ''.join(c for c in numbers if c.isdigit())
                        if digits_only:
                            formatted = "{:,}".format(int(digits_only))
                            self.money_label.config(text=f"Money: {formatted}")
                        else:
                            self.money_label.config(text="Money: (No valid number found)")
                        # Close window after short delay
                        self.after(1200, self._close_recalibrate_window)
                        # Stop listener
                        self.f8_listener.stop()
                        self.f8_listener = None
            except Exception:
                pass

        def listen():
            with keyboard.Listener(on_press=on_press) as listener:
                self.f8_listener = listener
                listener.join()

        threading.Thread(target=listen, daemon=True).start()

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