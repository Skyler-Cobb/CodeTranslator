# helpers/gui/progress_dialog.py

import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

class ProgressDialog(tk.Toplevel):
    """
    Modal dialog showing progress during Auto‐Detect over multiple modules.
    Has two buttons:
      - Cancel: abort entire auto‐detect
      - Skip Step: abort current module’s decoding and move on
    """

    def __init__(self, parent, total_modules: int):
        super().__init__(parent)
        self.title("Decoding Progress")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.total_modules = total_modules
        self.module_index = 0

        # Track flags
        self.cancel_flag = SimpleNamespace(cancel=False)
        self.skip_flag   = SimpleNamespace(skip=False)

        # Status label
        self.status_label = ttk.Label(self, text="Starting...")
        self.status_label.pack(padx=12, pady=(12, 6))

        # Progress bar
        self.progress_bar = ttk.Progressbar(self, length=400, mode="determinate")
        self.progress_bar.pack(padx=12, pady=(0, 12))

        # Button frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=(0, 12))

        # Skip Step button
        skip_btn = ttk.Button(btn_frame, text="Skip Step", command=self._on_skip)
        skip_btn.pack(side="left", padx=8)

        # Cancel button
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self._on_cancel)
        cancel_btn.pack(side="left", padx=8)

        # Position near parent
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")

    def _on_cancel(self):
        self.cancel_flag.cancel = True

    def _on_skip(self):
        self.skip_flag.skip = True

    def update_module_phase(self, module_idx: int, module_name: str):
        """
        Called when starting a new module’s perfect‐search.
        """
        self.module_index = module_idx
        self.status_label.config(
            text=f"[{module_idx}/{self.total_modules}] Testing For Perfect Match: {module_name}"
        )
        bar_value = (module_idx / self.total_modules) * 100.0
        self.progress_bar["value"] = bar_value
        self.update_idletasks()

    def update_permutation_phase(self, percent: float, module_name: str):
        """
        Called repeatedly as we iterate token‐configs inside a single module.
        """
        self.status_label.config(
            text=f"[{self.module_index}/{self.total_modules}] Testing Permutations: {module_name}"
        )
        self.progress_bar["value"] = percent
        self.update_idletasks()

    def close(self):
        self.grab_release()
        self.destroy()
