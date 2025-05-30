# This is a modified version of the GUI file with enhanced Caesar cipher functionality
# Only the relevant parts have been changed

import tkinter as tk
from tkinter import ttk

from utils          import load_dictionary, compute_accuracy
from module_loader  import load_modules
from codec          import (
    multi_step_decode, multi_step_encode, multi_step_tokenize,
    decode_message_with_module, encode_message_with_module, tokenize_message_with_module,
)
from tools          import caesar_translate, analyze_caesar_candidates


class DecoderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Decoder")

        # persistent data
        self.modules    = load_modules()
        self.dictionary = load_dictionary()

        # selection tracking
        self.current_module_type = None   # "module", "other"
        self.current_module_name = None
        self.current_module_data = None

        # GUI elements
        self.create_widgets()
        self.resizable(width=True, height=True)
        self.minsize(width=640, height=400)

    def create_widgets(self):
        # ================= LEFT PANE ===================
        left_frame = ttk.Frame(self)
        left_frame.pack(side="left", fill="both", expand=True)

        # ───────── module controls ─────────
        self.module_frame = ttk.LabelFrame(left_frame, text="Modules")
        self.module_frame.pack(fill="x", expand=False, padx=6, pady=6)

        # module selection: one dropdown for each module in the modules.keys() list
        mod_sel_frame = ttk.Frame(self.module_frame)
        mod_sel_frame.pack(fill="x")

        ttk.Label(mod_sel_frame, text="Module:").grid(row=0, column=0, padx=4, pady=2)
        self.module_sel = ttk.Combobox(mod_sel_frame, values=list(self.modules.keys()), state="readonly", width=16)
        self.module_sel.current(0)
        self.module_sel.bind("<<ComboboxSelected>>", lambda e: self._switch_module_type("module"))
        self.module_sel.grid(row=0, column=1, padx=4, pady=2, sticky="w")

        # module paths, if avaiable
        ttk.Label(mod_sel_frame, text="Path:").grid(row=1, column=0, padx=4, pady=2)
        self.path_sel = ttk.Combobox(mod_sel_frame, values=[], state="readonly", width=16)
        self.path_sel.grid(row=1, column=1, padx=4, pady=2, sticky="w")

        # direction radio
        ttk.Label(mod_sel_frame, text="Direction:").grid(row=2, column=0, padx=4, pady=2)
        self.direction = tk.StringVar(value="decode")
        ttk.Radiobutton(mod_sel_frame, text="Decode", variable=self.direction, value="decode").grid(row=2, column=1, padx=4, pady=2, sticky="w")
        ttk.Radiobutton(mod_sel_frame, text="Encode", variable=self.direction, value="encode").grid(row=3, column=1, padx=4, pady=2, sticky="w")

        # options
        opts_frame = ttk.Frame(self.module_frame)
        opts_frame.pack(fill="x", pady=(4, 0))

        # flawed checkbox
        self.flawed = tk.BooleanVar(value=True)
        flawed_cb = ttk.Checkbutton(opts_frame, text="Allow flawed decode", variable=self.flawed)
        flawed_cb.pack(side="left", padx=4, anchor="w")

        # all modules checkbox
        self.all_modules = tk.BooleanVar(value=False)
        all_mod_cb = ttk.Checkbutton(opts_frame, text="Try all modules", variable=self.all_modules)
        all_mod_cb.pack(side="left", padx=4, anchor="w")

        # ───────── other tools controls ─────────
        self.other_frame = ttk.LabelFrame(left_frame, text="Other Tools")
        self.other_frame.pack(fill="x", expand=False, padx=6, pady=6)

        # tool selection
        ttk.Label(self.other_frame, text="Tool:").grid(row=0, column=0, padx=4, pady=2)
        self.tool_sel = ttk.Combobox(self.other_frame, values=["Caesar Cipher"], state="readonly", width=16)
        self.tool_sel.current(0)
        self.tool_sel.bind("<<ComboboxSelected>>", lambda e: self._update_tool_options())
        self.tool_sel.grid(row=0, column=1, padx=4, pady=2, sticky="w")

        # Caesar Cipher options
        self.caesar_frame = ttk.Frame(self.other_frame)
        self.caesar_frame.grid(row=1, column=0, columnspan=2, sticky="we", padx=4)
        
        # offset widgets (single IntVar keeps them in sync)
        self.caesar_shift = tk.IntVar(value=0)
        self.shift_slider = tk.Scale(self.caesar_frame, from_=-26, to=26, orient="horizontal",
                                     variable=self.caesar_shift, length=220)
        self.shift_slider.pack(fill="x", expand=True)
        
        slider_frame = ttk.Frame(self.caesar_frame)
        slider_frame.pack(fill="x", expand=True)
        
        self.shift_entry = tk.Entry(slider_frame, textvariable=self.caesar_shift, width=6, justify="center")
        self.shift_entry.pack(side="left", padx=(0, 10))
        
        # Auto-decrypt button
        self.auto_decrypt_btn = ttk.Button(slider_frame, text="Auto Decrypt", 
                                          command=self._auto_decrypt_caesar)
        self.auto_decrypt_btn.pack(side="right")

        # Create a frame for radio buttons
        self.caesar_mode_frame = ttk.Frame(self.caesar_frame)
        self.caesar_mode_frame.pack(fill="x", pady=5)
        
        # Add radio buttons for mode (manual vs auto)
        self.cipher_mode = tk.StringVar(value="manual")
        ttk.Radiobutton(self.caesar_mode_frame, text="Manual Shift", 
                       variable=self.cipher_mode, value="manual",
                       command=self._update_caesar_mode).pack(side="left", padx=5)
        ttk.Radiobutton(self.caesar_mode_frame, text="Auto Analysis", 
                       variable=self.cipher_mode, value="auto",
                       command=self._update_caesar_mode).pack(side="left", padx=5)

        self.other_frame.pack_forget()

        # ───────── radio buttons to switch between modules & others ─────────
        switch_frame = ttk.Frame(left_frame)
        switch_frame.pack(fill="x", expand=False, padx=6, pady=6)

        self.tool_type = tk.StringVar(value="module")
        ttk.Radiobutton(switch_frame, text="Modules", variable=self.tool_type, value="module",
                       command=lambda: self._switch_module_type("module")).pack(side="left", padx=4)
        ttk.Radiobutton(switch_frame, text="Other Tools", variable=self.tool_type, value="other",
                       command=lambda: self._switch_module_type("other")).pack(side="left", padx=4)

        # ───────── message input ─────────
        msg_frame = ttk.LabelFrame(left_frame, text="Message")
        msg_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.msg_text = tk.Text(msg_frame, wrap="char", width=30, height=10)
        self.msg_text.pack(fill="both", expand=True, padx=4, pady=4)

        self.go_button = ttk.Button(msg_frame, text="Process", command=self._process_message)
        self.go_button.pack(fill="x", padx=4, pady=(0, 4))

        # ================= RIGHT PANE ===================
        right_frame = ttk.Frame(self)
        right_frame.pack(side="right", fill="both", expand=True)

        # ───────── results pane ─────────
        results_frame = ttk.LabelFrame(right_frame, text="Results")
        results_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.results_text = tk.Text(results_frame, wrap="char", width=40, height=20)
        self.results_text.pack(fill="both", expand=True, padx=4, pady=4)

        # ───────── init module path selection ─────────
        self._init_module_path()
        
    def _update_tool_options(self):
        """Update tool options based on selected tool"""
        tool = self.tool_sel.get()
        
        # Hide all tool-specific frames first
        self.caesar_frame.grid_forget()
        
        # Show the appropriate frame for the selected tool
        if tool == "Caesar Cipher":
            self.caesar_frame.grid(row=1, column=0, columnspan=2, sticky="we", padx=4)
            self._update_caesar_mode()

    def _update_caesar_mode(self):
        """Update Caesar cipher UI based on selected mode"""
        mode = self.cipher_mode.get()
        
        if mode == "manual":
            self.shift_slider.config(state="normal")
            self.shift_entry.config(state="normal")
            self.auto_decrypt_btn.config(state="disabled")
        else:  # auto mode
            self.shift_slider.config(state="disabled")
            self.shift_entry.config(state="disabled")
            self.auto_decrypt_btn.config(state="normal")

    def _auto_decrypt_caesar(self):
        """Run auto-decryption analysis for Caesar cipher"""
        msg = self.msg_text.get("1.0", "end").strip()
        if not msg:
            self._write("No message to decrypt.\n")
            return
            
        self._write("Running Caesar cipher auto-analysis...\n")
        candidates = analyze_caesar_candidates(msg, top_n=5)
        
        # Display results
        for i, (shift, plaintext, score) in enumerate(candidates):
            self._write(f"\n--- Candidate #{i+1} (Shift: {shift}, Score: {score:.2f}) ---\n")
            self._write(f"{plaintext}\n")
            
        # Set the most likely shift in the UI
        if candidates:
            best_shift = candidates[0][0]
            self.caesar_shift.set(best_shift)

    def _init_module_path(self):
        mod_name = self.module_sel.get()
        self.current_module_name = mod_name
        self.current_module_data = self.modules.get(mod_name)
        self._update_paths()

    def _update_paths(self):
        if "chain" in self.current_module_data:
            self.path_sel["values"] = [""]  # no paths for chains (or could enumerate the chain's elements for this)
            self.path_sel.current(0)
            self.path_sel.config(state="disabled")
        else:
            path_values = [""]
            if "paths" in self.current_module_data:
                path_values += sorted(self.current_module_data["paths"])
            self.path_sel["values"] = path_values
            self.path_sel.current(0)
            self.path_sel.config(state="readonly")

    def _switch_module_type(self, module_type):
        # Update radio
        self.tool_type.set(module_type)
        # Change panels
        if module_type == "module":
            if self.current_module_type != "module":
                self.other_frame.pack_forget()
                self.module_frame.pack(fill="x", expand=False, padx=6, pady=6, before=self.go_button.master)
                self.current_module_type = "module"
        else:
            if self.current_module_type != "other":
                self.module_frame.pack_forget()
                self.other_frame.pack(fill="x", expand=False, padx=6, pady=6, before=self.go_button.master)
                self.current_module_type = "other"
                # Initialize the selected tool's options
                self._update_tool_options()

    def _write(self, text):
        self.results_text.insert("end", text)

    def _process_message(self):
        # clear results
        self.results_text.delete("1.0", "end")

        # get message text
        msg = self.msg_text.get("1.0", "end").strip()
        if not msg:
            self._write("No message to process.\n")
            return

        # determine mode
        flawed = self.flawed.get()

        outputs = []
        if self.current_module_type == "module":
            mod_name = self.module_sel.get()
            path = self.path_sel.get()
            if self.all_modules.get():
                for name, data in self.modules.items():
                    func = multi_step_decode if "chain" in data else decode_message_with_module
                    outputs += func(data, msg, flawed)
            else:
                data = self.modules.get(mod_name)
                if data:
                    func = multi_step_decode if "chain" in data else decode_message_with_module
                    outputs = func(data, msg, flawed)
        else:  # other tools
            if self.cipher_mode.get() == "auto":
                # Run auto-detection
                self._auto_decrypt_caesar()
                return
            else:
                # Manual shift
                shift = self.caesar_shift.get()
                outputs = [caesar_translate(msg, shift)]

        if not outputs:
            self._write("No results.\n")
            return

        uniq = list(dict.fromkeys(outputs))

        # when in other mode, accuracy filter happens inline like module path
        scored_lines = []
        for line in uniq:
            accuracy = compute_accuracy(line, self.dictionary)
            scored_lines.append((line, accuracy))

        # sort highest accuracy first
        scored_lines.sort(key=lambda pair: pair[1], reverse=True)

        # display results
        for line, accuracy in scored_lines:
            self._write(f"{line}  [{accuracy:.1%}]\n\n")