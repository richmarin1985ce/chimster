import unittest
import tkinter as tk
from tkinter import ttk
from chimster.calipi import Calipi, clamp_position, tip_for

class CalipiTests(unittest.TestCase):
    def test_context_and_fallback(self):
        self.assertIn("script", tip_for("Script editor"))
        self.assertEqual(tip_for("unknown", 0), tip_for("unknown", 4))
        self.assertNotEqual(tip_for("Project", 0), tip_for("Project", 1))

    def test_bounds(self):
        self.assertEqual(clamp_position(-1, 900, 800, 600, 100, 150), (0, 450))
        self.assertEqual(clamp_position(50, 50, 20, 20, 100, 100), (0, 0))

    def test_toggle_and_timer_cleanup(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tk display unavailable")
        self.addCleanup(root.destroy)
        root.geometry("800x600")
        tabs = ttk.Notebook(root)
        tabs.pack(fill="both", expand=True)
        tabs.add(ttk.Frame(tabs), text="Project")
        menu = tk.Menu(root, tearoff=False)
        assistant = Calipi(root, tabs, menu)
        root.update()
        self.assertFalse(assistant.enabled.get())
        menu.invoke(0)
        root.update()
        self.assertTrue(assistant.enabled.get())
        self.assertTrue(assistant.frame.winfo_ismapped())
        self.assertIsNotNone(assistant.timer)
        assistant.hide()
        root.update()
        self.assertFalse(assistant.frame.winfo_ismapped())
        self.assertIsNone(assistant.timer)
        self.assertIsNone(assistant.speech_timer)
        self.assertFalse(assistant.enabled.get())
