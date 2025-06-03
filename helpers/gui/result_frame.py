# helpers/gui/result_frame.py

import tkinter as tk
from tkinter import ttk
import math

class ResultFrame(ttk.Frame):
    """
    A scrollable, collapsible container for displaying:
      1) One “best overall” Text at the top
      2) A series of collapsible sections, one per module
    """

    def __init__(self, parent, dictionary_set: set[str]):
        """
        parent: the container (a Frame) in which this ResultFrame lives.
        dictionary_set: set of uppercase words for tie-breaking.
        """
        super().__init__(parent)
        self.dictionary_set = dictionary_set

        # 1) Canvas + vertical Scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        # 2) “Inner” frame that will hold all children
        self.inner_frame = ttk.Frame(self.canvas)
        # Keep the window ID so we can force its width later
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # 3) Whenever inner_frame’s size changes, update the scrollregion
        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # 4) Whenever the canvas itself is resized, force inner_frame’s width = canvas width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        """
        Called whenever the canvas (and thus window) is resized.
        1) Force inner_frame’s width to match canvas’s width.
        2) Update wraplength for each child widget (Text or Label).
        """
        # ─── Force inner_frame width ───
        new_width = event.width
        self.canvas.itemconfigure(self.inner_id, width=new_width)

        # ─── Update wraplengths ───
        wrap_len = new_width - 20  # leave a small padding
        for child in self.inner_frame.winfo_children():
            # If it’s a Text widget, update its wrap and width
            if isinstance(child, tk.Text):
                child.configure(width=wrap_len)
            # If it’s a Frame (a collapsible section), update its labels
            elif isinstance(child, ttk.Frame):
                for sub in child.winfo_children():
                    # Header frame
                    if isinstance(sub, ttk.Frame):
                        for w in sub.winfo_children():
                            if isinstance(w, ttk.Label):
                                w.configure(wraplength=wrap_len - 40)
                    # Body might contain Text widgets
                    if isinstance(sub, tk.Text):
                        sub.configure(width=wrap_len - 40)

    def display_plain_text(self, text: str):
        """
        Clear everything and display a single read-only Text widget (e.g. "No results" or Caesar output).
        """
        for child in self.inner_frame.winfo_children():
            child.destroy()

        # Estimate height as roughly one line per 40 chars
        lines_needed = max(1, int(math.ceil(len(text) / 40)))
        txt_widget = tk.Text(
            self.inner_frame,
            wrap="word",
            height=lines_needed,
            bd=1,
            relief="solid"
        )
        txt_widget.insert("1.0", text)
        txt_widget.configure(state="disabled")
        txt_widget.pack(fill="x", anchor="nw", padx=4, pady=4)

        # After packing, force wrap to current width
        self.after(10, lambda: txt_widget.configure(width=self.inner_frame.winfo_width() - 20))
        self.canvas.yview_moveto(0.0)

    def display_grouped_results(self, raw_outputs: list[str], min_acc_pct: float, raw_input: str):
        """
        raw_outputs: list of strings like "[ModuleName] translation"
        min_acc_pct: minimum required accuracy (0.0–1.0)
        raw_input: the original cipher text, for pass-through detection.

        Group them by module, compute adjusted accuracy (pass-through → 0),
        then build:
         1) “Best overall” Text at top (always visible)
         2) A collapsible section per module (sorted by that module’s max accuracy)
        """

        # 1) Strip spaces from raw_input to compare character by character
        input_stripped = "".join(raw_input.split())

        # 2) Parse and score each entry
        scored_entries = []
        for entry in raw_outputs:
            if entry.startswith("[") and "] " in entry:
                mod, txt = entry.split("] ", 1)
                mod_name = mod[1:]
            else:
                mod_name = "Unknown"
                txt = entry

            # Remove spaces to align indices
            decoded_stripped = "".join(txt.split())

            # Count “fully translated” letters vs “untranslated”
            translated_full = 0
            untranslated_chars = 0

            # Compare up to min length
            min_len = min(len(input_stripped), len(decoded_stripped))
            for i in range(min_len):
                if decoded_stripped[i] != input_stripped[i]:
                    translated_full += 1
                else:
                    untranslated_chars += 1  # pass-through is treated as untranslated

            # Any extra chars in decoded beyond min_len
            for c in decoded_stripped[min_len:]:
                if c.isalpha():
                    translated_full += 1
                else:
                    untranslated_chars += 1

            # Compute accuracy = translated_full / (translated_full + untranslated_chars)
            total_for_acc = translated_full + untranslated_chars
            accuracy_frac = (translated_full / total_for_acc) if total_for_acc > 0 else 0.0

            # Dictionary‐hits tie-breaker
            word_list = txt.split()
            dict_hits = sum(1 for w in word_list if w.upper() in self.dictionary_set)

            if accuracy_frac >= min_acc_pct:
                scored_entries.append((mod_name, txt, accuracy_frac, dict_hits))

        if not scored_entries:
            self.display_plain_text("No results.")
            return

        # 3) Group by module
        grouped: dict[str, list[tuple[str, float, int]]] = {}
        for mod_name, txt, acc, dh in scored_entries:
            grouped.setdefault(mod_name, []).append((txt, acc, dh))

        # 4) Find best overall (max by (acc, dh))
        best_mod, best_txt, best_acc, best_dh = max(
            scored_entries, key=lambda x: (x[2], x[3])
        )

        # 5) Clear existing children
        for child in self.inner_frame.winfo_children():
            child.destroy()

        # 6) Display “best overall” at top as a read-only Text
        best_text = f"[{best_mod}] {best_txt}    [{best_acc*100:.1f}%  /  {best_dh} hits]"
        lines_needed = max(1, int(math.ceil(len(best_text) / 40)))
        best_widget = tk.Text(
            self.inner_frame,
            wrap="word",
            height=lines_needed,
            bd=1,
            relief="solid"
        )
        best_widget.insert("1.0", best_text)
        best_widget.configure(state="disabled")
        best_widget.pack(fill="x", padx=4, pady=(4, 8))
        self.after(10, lambda: best_widget.configure(width=self.inner_frame.winfo_width() - 20))

        # 7) Collect module stats for sorting: (mod_name, items, min_acc, max_acc)
        module_stats = []
        for m_name, items in grouped.items():
            acc_vals = [acc for (_, acc, _) in items]
            module_stats.append((m_name, items, min(acc_vals), max(acc_vals)))

        # Sort modules by max accuracy descending
        module_stats.sort(key=lambda x: x[3], reverse=True)

        # 8) Create a collapsible section per module
        for m_name, items, min_a, max_a in module_stats:
            self._create_collapsible_section(m_name, items, min_a, max_a)

        # Scroll back up
        self.canvas.yview_moveto(0.0)

    def _create_collapsible_section(
        self,
        mod_name: str,
        items: list[tuple[str, float, int]],
        min_acc: float,
        max_acc: float
    ):
        """
        Build a single collapsible frame under inner_frame:
          - Header: "mod_name (N results, Min%–Max%) [▼]"
          - Body: each translation in its own Text box, with one blank line (pady) between them
        """
        count   = len(items)
        min_pct = min_acc * 100
        max_pct = max_acc * 100

        # Section container with a visible border
        section_frame = ttk.Frame(self.inner_frame, relief="solid", borderwidth=1)
        section_frame.pack(fill="x", padx=4, pady=2, anchor="n")

        # Header sub-frame
        header = ttk.Frame(section_frame)
        header.pack(fill="x")

        header_text = f"{mod_name} ({count} results, {min_pct:.0f}%–{max_pct:.0f}%)"
        lbl_header = ttk.Label(header, text=header_text)
        lbl_header.pack(side="left", padx=(4, 0), pady=4)

        arrow_lbl = ttk.Label(header, text="▼")
        arrow_lbl.pack(side="right", padx=(0, 4))

        # Body sub-frame (initially hidden)
        body = ttk.Frame(section_frame)
        body.pack(fill="x", padx=12, pady=(0, 4))
        body.forget()

        # Sort items by (acc, dict_hits) descending
        items_sorted = sorted(items, key=lambda x: (x[1], x[2]), reverse=True)

        # For each item, create a read-only Text widget (wrapped, bordered),
        # with a blank line (pady) beneath it to separate from next.
        for txt, acc, dh in items_sorted:
            display_line = f"{txt}    [{acc*100:.1f}%  /  {dh} hits]"
            lines_needed = max(1, int(math.ceil(len(display_line) / 40)))
            text_widget = tk.Text(
                body,
                wrap="word",
                height=lines_needed,
                bd=1,
                relief="solid"
            )
            text_widget.insert("1.0", display_line)
            text_widget.configure(state="disabled")
            text_widget.pack(fill="x", anchor="w", pady=(0, 4))
            self.after(10, lambda w=text_widget: w.configure(width=self.inner_frame.winfo_width() - 40))

        def toggle():
            if body.winfo_manager():
                # If visible → collapse
                body.forget()
                arrow_lbl.config(text="▼")
            else:
                # If hidden → expand
                body.pack(fill="x", padx=12, pady=(0, 4))
                arrow_lbl.config(text="▲")

        # Bind any click on header, label, or arrow to toggle
        header.bind("<Button-1>", lambda e: toggle())
        lbl_header.bind("<Button-1>", lambda e: toggle())
        arrow_lbl.bind("<Button-1>", lambda e: toggle())
