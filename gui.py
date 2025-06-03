# gui.py

import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from utils import load_dictionary
from module_loader import load_modules

# Import helper UI classes
from helpers.gui.progress_dialog import ProgressDialog
from helpers.gui.result_frame import ResultFrame

from helpers.codec import decode_message_with_module, multi_step_encode
from tools import caesar_translate, analyze_caesar_candidates, keyshift_translate

AUTO_DETECT = "<Auto-Detect>"

class DecoderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Decoder")

        # Load modules and dictionary
        self.modules = load_modules()
        self.dictionary_set = load_dictionary()

        self.current_panel = "module"
        self.create_widgets()

        self.resizable(width=True, height=True)
        self.minsize(width=640, height=400)

    def create_widgets(self):
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # ================= LEFT PANE ===================
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        # ───────── Module Controls ─────────
        self.module_frame = ttk.LabelFrame(left_frame, text="Modules")
        self.module_frame.pack(fill="x", expand=False, padx=6, pady=6)

        mod_sel_frame = ttk.Frame(self.module_frame)
        mod_sel_frame.pack(fill="x", pady=(4, 0))

        # Module dropdown
        ttk.Label(mod_sel_frame, text="Module:").grid(row=0, column=0, padx=4, pady=2)
        mod_vals = [AUTO_DETECT] + sorted(self.modules.keys())
        self.module_sel = ttk.Combobox(
            mod_sel_frame,
            values=mod_vals,
            state="readonly",
            width=20
        )
        self.module_sel.current(0)
        self.module_sel.grid(row=0, column=1, padx=4, pady=2, sticky="w")

        # Direction: Decode vs Encode
        ttk.Label(mod_sel_frame, text="Direction:").grid(row=1, column=0, padx=4, pady=2)
        self.direction = tk.StringVar(value="decode")
        dir_frame = ttk.Frame(mod_sel_frame)
        dir_frame.grid(row=1, column=1, padx=4, pady=2, sticky="w")
        ttk.Radiobutton(
            dir_frame,
            text="Decode",
            variable=self.direction,
            value="decode"
        ).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(
            dir_frame,
            text="Encode",
            variable=self.direction,
            value="encode"
        ).pack(side="left")

        # Allow flawed decode checkbox
        self.flawed = tk.BooleanVar(value=True)
        flawed_cb = ttk.Checkbutton(
            self.module_frame,
            text="Allow flawed decode",
            variable=self.flawed,
            command=self._toggle_min_acc_visibility
        )
        flawed_cb.pack(side="left", padx=4, anchor="w", pady=(4, 0))

        # Min Accuracy slider (shown only if flawed=True)
        self.minacc_frame = ttk.Frame(self.module_frame)
        self.minacc_frame.pack(fill="x", padx=4, pady=(8, 0))
        ttk.Label(self.minacc_frame, text="Min Accuracy (%)").pack(side="left", padx=(0, 8))
        self.min_accuracy = tk.IntVar(value=0)
        self.min_acc_slider = tk.Scale(
            self.minacc_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.min_accuracy,
            length=180,
        )
        self.min_acc_slider.pack(side="left", fill="x", expand=True)

        if not self.flawed.get():
            self.minacc_frame.pack_forget()

        # ───────── Decoding Algorithms ─────────
        self.other_frame = ttk.LabelFrame(left_frame, text="Algorithms")
        self.other_frame.pack(fill="x", expand=False, padx=6, pady=6)
        self.other_frame.pack_forget()

        tool_sel_frame = ttk.Frame(self.other_frame)
        tool_sel_frame.grid(row=0, column=0, padx=4, pady=2, sticky="w")
        ttk.Label(tool_sel_frame, text="Tool:").grid(row=0, column=0, padx=(0, 4))
        self.tool_sel = ttk.Combobox(
            tool_sel_frame,
            values=["Caesar Cipher", "Keyshift Cipher"],
            state="readonly",
            width=16
        )
        self.tool_sel.current(0)
        self.tool_sel.bind("<<ComboboxSelected>>", lambda e: self._update_tool_options())
        self.tool_sel.grid(row=0, column=1, padx=4, pady=2, sticky="w")

        # Caesar sub-frame
        self.caesar_frame = ttk.Frame(self.other_frame)
        self.caesar_frame.grid(row=1, column=0, columnspan=2, sticky="we", padx=4)

        self.caesar_shift = tk.IntVar(value=0)
        self.shift_slider = tk.Scale(
            self.caesar_frame,
            from_=-26, to=26,
            orient="horizontal",
            variable=self.caesar_shift,
            length=220
        )
        self.shift_slider.pack(fill="x", expand=True)

        slider_frame = ttk.Frame(self.caesar_frame)
        slider_frame.pack(fill="x", expand=True, pady=(4, 0))

        self.shift_entry = tk.Entry(
            slider_frame,
            textvariable=self.caesar_shift,
            width=6,
            justify="center"
        )
        self.shift_entry.pack(side="left", padx=(0, 10))
        self.shift_entry.bind("<Return>", lambda e: self._on_shift_entry())

        self.auto_decrypt_btn = ttk.Button(
            slider_frame,
            text="Auto Decrypt",
            command=self._auto_decrypt_caesar
        )
        self.auto_decrypt_btn.pack(side="right")

        self.caesar_mode_frame = ttk.Frame(self.caesar_frame)
        self.caesar_mode_frame.pack(fill="x", pady=5)

        self.cipher_mode = tk.StringVar(value="manual")
        ttk.Radiobutton(
            self.caesar_mode_frame,
            text="Manual Shift",
            variable=self.cipher_mode,
            value="manual",
            command=self._update_caesar_mode
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            self.caesar_mode_frame,
            text="Auto Analysis",
            variable=self.cipher_mode,
            value="auto",
            command=self._update_caesar_mode
        ).pack(side="left", padx=5)
        # ───────── Keyshift sub-frame ─────────
        self.keyshift_frame = ttk.Frame(self.other_frame)
        self.keyshift_frame.grid(row=2, column=0, columnspan=2, sticky="we", padx=4)
        # Hide it initially:
        self.keyshift_frame.grid_remove()

        # IntVar to hold the Keyshift offset
        self.keyshift_shift = tk.IntVar(value=0)

        # Slider from –10 to 10 (max row length = 10)
        self.keyshift_slider = tk.Scale(
            self.keyshift_frame,
            from_=-10, to=10,
            orient="horizontal",
            variable=self.keyshift_shift,
            length=220
        )
        self.keyshift_slider.pack(fill="x", expand=True)

        # Entry below the slider for direct numeric input
        keyshift_entry_frame = ttk.Frame(self.keyshift_frame)
        keyshift_entry_frame.pack(fill="x", expand=True, pady=(4, 0))

        self.keyshift_entry = tk.Entry(keyshift_entry_frame, width=4, textvariable=self.keyshift_shift)
        self.keyshift_entry.pack(side="left")
        self.keyshift_entry.bind("<Return>", lambda e: self._on_keyshift_entry())


        # ───────── Panel Switch (Modules, Algorithms) ─────────
        switch_frame = ttk.Frame(left_frame)
        switch_frame.pack(fill="x", expand=False, padx=6, pady=6)

        self.tool_type = tk.StringVar(value="module")
        ttk.Radiobutton(
            switch_frame,
            text="Modules",
            variable=self.tool_type,
            value="module",
            command=lambda: self._switch_panel("module")
        ).pack(side="left", padx=4)
        ttk.Radiobutton(
            switch_frame,
            text="Algorithms",
            variable=self.tool_type,
            value="other",
            command=lambda: self._switch_panel("other")
        ).pack(side="left", padx=4)

        # ───────── Message Input ─────────
        msg_frame = ttk.LabelFrame(left_frame, text="Message")
        msg_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.msg_text = tk.Text(msg_frame, wrap="char")
        self.msg_text.pack(fill="both", expand=True, padx=4, pady=4)

        self.go_button = ttk.Button(msg_frame, text="Process", command=self._process_message)
        self.go_button.pack(fill="x", padx=4, pady=(0, 4))

        # ================= RIGHT PANE ===================
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        # Create and pack ResultFrame
        self.result_frame = ResultFrame(right_frame, self.dictionary_set)
        self.result_frame.pack(fill="both", expand=True, padx=6, pady=6)

        #  ─── Set initial sashpos so panes start roughly equal ───
        self.after(100, lambda: paned.sashpos(0, int(self.winfo_width() * 0.5)))

        self._switch_panel("module")

    def _switch_panel(self, panel: str):
        """
        Show module_frame or other_frame depending on radio-button.
        """
        if panel == "module":
            if self.current_panel != "module":
                self.other_frame.pack_forget()
                self.module_frame.pack(fill="x", expand=False, padx=6, pady=6)
                self.current_panel = "module"
        else:
            if self.current_panel != "other":
                self.module_frame.pack_forget()
                self.other_frame.pack(fill="x", expand=False, padx=6, pady=6)
                self.current_panel = "other"
                self._update_tool_options()

    def _update_caesar_mode(self):
        """
        Enable/disable Caesar slider vs auto-analysis.
        """
        mode = self.cipher_mode.get()
        if mode == "manual":
            self.shift_slider.config(state="normal")
            self.shift_entry.config(state="normal")
            self.auto_decrypt_btn.config(state="disabled")
        else:
            self.shift_slider.config(state="disabled")
            self.shift_entry.config(state="disabled")
            self.auto_decrypt_btn.config(state="normal")

    def _on_shift_entry(self):
        """
        Clamp Caesar shift slider after manual entry.
        """
        try:
            shift = int(self.shift_entry.get())
        except ValueError:
            return
        shift = max(-26, min(26, shift))
        self.caesar_shift.set(shift)

    def _on_keyshift_entry(self):
        """
        Keep slider and entry in sync for Keyshift.
        If user types a number and presses Enter, update the slider.
        """
        try:
            val = int(self.keyshift_entry.get())
        except ValueError:
            val = 0
        # Clamp within allowed range
        if val < -10:
            val = -10
        elif val > 10:
            val = 10
        self.keyshift_shift.set(val)

    def _update_tool_options(self):
        """
        Show/hide the Caesar vs Keyshift sub-frames
        depending on which tool was selected in the Combobox.
        """
        selected = self.tool_sel.get()
        if selected == "Caesar Cipher":
            # Show Caesar UI, hide Keyshift UI
            self.caesar_frame.grid()
            self.keyshift_frame.grid_remove()
        elif selected == "Keyshift Cipher":
            # Show Keyshift UI, hide Caesar UI
            self.caesar_frame.grid_remove()
            self.keyshift_frame.grid()
        else:
            # Fallback: hide both if something unexpected appears
            self.caesar_frame.grid_remove()
            self.keyshift_frame.grid_remove()


    def _auto_decrypt_caesar(self):
        """
        Run Caesar auto-analysis & display in result_frame.
        """
        msg = self.msg_text.get("1.0", "end").strip()
        if not msg:
            self.result_frame.display_plain_text("No message to decrypt.")
            return

        lines = ["Running Caesar cipher auto-analysis…"]
        candidates = analyze_caesar_candidates(msg, 5)
        for i, (shift, plaintext, score) in enumerate(candidates, start=1):
            lines.append(f"--- Candidate #{i} (Shift: {shift}, Score: {score:.2f}) ---")
            lines.append(plaintext)
            lines.append("")  # blank

        self.result_frame.display_plain_text("\n".join(lines))

        if candidates:
            best_shift = candidates[0][0]
            self.caesar_shift.set(best_shift)

    def _toggle_min_acc_visibility(self):
        """
        Hide/show the Min Accuracy slider when “Allow flawed decode” toggles.
        """
        if self.flawed.get():
            self.minacc_frame.pack(fill="x", padx=4, pady=(8, 0))
        else:
            self.minacc_frame.pack_forget()

    def _process_message(self):
        """
        Called when “Process” is clicked. Handles Module decode/encode
        or Caesar. For Auto-Detect, pops up ProgressDialog with Cancel/Skip.
        Finally groups results into result_frame.
        """
        raw_msg = self.msg_text.get("1.0", "end").strip()
        if not raw_msg:
            self.result_frame.display_plain_text("No message to process.")
            return

        outputs = []

        if self.current_panel == "other":
            tool_choice = self.tool_sel.get()
            if tool_choice == "Caesar Cipher":
                # Mirror existing Caesar logic
                if self.cipher_mode.get() == "auto":
                    self._auto_decrypt_caesar()
                    return
                else:
                    shift = self.caesar_shift.get()
                    outputs = [caesar_translate(raw_msg, shift)]
                    self.result_frame.display_plain_text("\n\n".join(outputs))
                    return

            elif tool_choice == "Keyshift Cipher":
                # Always a manual Keyshift
                shift = self.keyshift_shift.get()
                outputs = [keyshift_translate(raw_msg, shift)]
                self.result_frame.display_plain_text("\n\n".join(outputs))
                return

            else:
                # Fallback if no valid choice
                self.result_frame.display_plain_text("No tool selected.")
                return
        # ==== MODULE PATH ====
        mod_name     = self.module_sel.get()
        flawed_allowed = self.flawed.get()
        min_acc_pct    = self.min_accuracy.get() / 100.0

        if self.direction.get() == "encode":
            # ENCODING
            if mod_name == AUTO_DETECT:
                for name, data in self.modules.items():
                    encs = multi_step_encode(data, raw_msg)
                    outputs += [f"[{name}] {enc}" for enc in encs]
            else:
                data = self.modules.get(mod_name)
                if data:
                    encs = multi_step_encode(data, raw_msg)
                    outputs = [f"[{mod_name}] {enc}" for enc in encs]

            self.result_frame.display_plain_text("\n\n".join(outputs) if outputs else "No results.")
            return

        # ===== DECODING =====
        if mod_name == AUTO_DETECT:
            total_mods = len(self.modules)
            prog_dialog = ProgressDialog(self, total_mods)

            perfect_outputs = []
            # 1) Perfect-decode pass (collect all)
            for idx, (name, data) in enumerate(self.modules.items(), start=1):
                if prog_dialog.cancel_flag.cancel:
                    break
                if prog_dialog.skip_flag.skip:
                    prog_dialog.skip_flag.skip = False
                    continue

                prog_dialog.update_module_phase(idx, name)

                candidate_list = decode_message_with_module(
                    data,
                    raw_msg,
                    flawed=False,
                    min_accuracy=min_acc_pct,
                    progress_callback=lambda stage, m_i, t_m, pct, m_name, _idx=idx, _tm=total_mods, _name=name:
                        prog_dialog.update_permutation_phase(
                            pct if stage == "PermutationsPhase"
                            else ((_idx / _tm) * 100.0),
                            _name
                        ),
                    skip_flag=prog_dialog.skip_flag
                )

                if prog_dialog.skip_flag.skip:
                    prog_dialog.skip_flag.skip = False
                    continue

                if candidate_list:
                    perfect_outputs += [f"[{name}] {txt}" for txt in candidate_list]

            # If any perfect found, use them
            if perfect_outputs:
                outputs = perfect_outputs
            elif flawed_allowed and not prog_dialog.cancel_flag.cancel:
                # 2) Flawed-decode pass (collect all)
                for idx, (name, data) in enumerate(self.modules.items(), start=1):
                    if prog_dialog.cancel_flag.cancel:
                        break
                    if prog_dialog.skip_flag.skip:
                        prog_dialog.skip_flag.skip = False
                        continue

                    prog_dialog.update_module_phase(idx, name)

                    candidate_list = decode_message_with_module(
                        data,
                        raw_msg,
                        flawed=True,
                        min_accuracy=min_acc_pct,
                        progress_callback=lambda stage, m_i, t_m, pct, m_name, _idx=idx, _tm=total_mods, _name=name:
                            prog_dialog.update_permutation_phase(
                                pct if stage == "PermutationsPhase"
                                else ((_idx / _tm) * 100.0),
                                _name
                            ),
                        skip_flag=prog_dialog.skip_flag
                    )

                    if prog_dialog.skip_flag.skip:
                        prog_dialog.skip_flag.skip = False
                        continue

                    if candidate_list:
                        outputs += [f"[{name}] {txt}" for txt in candidate_list]

            prog_dialog.close()

        else:
            # Single module chosen
            data = self.modules.get(mod_name)
            if data:
                perfect_list = decode_message_with_module(
                    data,
                    raw_msg,
                    flawed=False,
                    min_accuracy=min_acc_pct,
                    progress_callback=None,
                    skip_flag=None
                )
                if perfect_list:
                    outputs += [f"[{mod_name}] {txt}" for txt in perfect_list]
                elif flawed_allowed:
                    flawed_list = decode_message_with_module(
                        data,
                        raw_msg,
                        flawed=True,
                        min_accuracy=min_acc_pct,
                        progress_callback=None,
                        skip_flag=None
                    )
                    outputs += [f"[{mod_name}] {txt}" for txt in flawed_list]

        if not outputs:
            self.result_frame.display_plain_text("No results.")
            return

        # Pass raw_msg so pass-through is demoted
        self.result_frame.display_grouped_results(outputs, min_acc_pct, raw_msg)