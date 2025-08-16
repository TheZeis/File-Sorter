import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import defaultdict

# ------------------------------
# LoRA Sorter – Enhanced Version
# Features added:
# - Undo/Restore Last Move & Batch Undo/Redo History
# - Custom Extensions List (comma-separated)
# - Orphan Finder (missing siblings by base name)
# - Duplicate Detector (same base name in multiple subfolders)
# - Search Bar to filter preview results
# - Progress Bar / Status Indicator
# - Export Log to .txt
# - Conflict Handling Options: skip / overwrite / rename
# ------------------------------

class LoRASorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LoRA Sorter – Enhanced")
        self.root.geometry("950x650")
        self.root.configure(bg="#1e1e1e")

        # ---- Styles ----
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TButton", foreground="white", background="#333", padding=6, relief="flat")
        style.configure("TCheckbutton", background="#1e1e1e", foreground="white")
        style.configure("TLabel", background="#1e1e1e", foreground="white")
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="white")
        style.configure("TCombobox", fieldbackground="#2d2d2d", foreground="white")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("Horizontal.TProgressbar", troughcolor="#2d2d2d", background="#5a5a5a")

        self.make_menu()

        # ---- Top controls frame ----
        top = ttk.Frame(root)
        top.pack(padx=16, pady=10, fill="x")

        self.select_button = ttk.Button(top, text="Choose Reference Files", command=self.choose_files)
        self.select_button.grid(row=0, column=0, padx=(0,8))

        ttk.Label(top, text="Extensions (comma-separated)").grid(row=0, column=1, sticky="w")
        self.ext_entry = ttk.Entry(top, width=45)
        self.ext_entry.grid(row=0, column=2, padx=6)
        self.ext_entry.insert(0, ".html,.civitai.info,.json,.preview.png,.safetensors")

        ttk.Label(top, text="On conflict:").grid(row=0, column=3, padx=(16,4))
        self.conflict_mode = tk.StringVar(value="skip")
        self.conflict_combo = ttk.Combobox(top, textvariable=self.conflict_mode, state="readonly", width=12,
                                           values=["skip", "overwrite", "rename"])
        self.conflict_combo.grid(row=0, column=4)

        self.auto_confirm = tk.BooleanVar()
        self.auto_confirm_check = ttk.Checkbutton(top, text="Auto-confirm", variable=self.auto_confirm)
        self.auto_confirm_check.grid(row=0, column=5, padx=(16,0))

        # ---- Action buttons ----
        actions = ttk.Frame(root)
        actions.pack(padx=16, pady=(0,8), fill="x")
        self.preview_button = ttk.Button(actions, text="Preview Matches", command=self.preview_matches)
        self.preview_button.pack(side="left")
        self.move_button = ttk.Button(actions, text="Move Files", command=self.run_sorter)
        self.move_button.pack(side="left", padx=8)
        self.undo_button = ttk.Button(actions, text="Undo", command=self.undo_last)
        self.undo_button.pack(side="left")
        self.redo_button = ttk.Button(actions, text="Redo", command=self.redo_last)
        self.redo_button.pack(side="left", padx=8)
        self.orphan_button = ttk.Button(actions, text="Orphan Finder", command=self.orphan_finder)
        self.orphan_button.pack(side="left")
        self.dup_button = ttk.Button(actions, text="Duplicate Detector", command=self.duplicate_detector)
        self.dup_button.pack(side="left", padx=8)
        self.export_button = ttk.Button(actions, text="Export Log", command=self.export_log)
        self.export_button.pack(side="left")

        # ---- Search & Preview list ----
        sp = ttk.Frame(root)
        sp.pack(padx=16, pady=(0,8), fill="both")
        ttk.Label(sp, text="Search preview:").pack(anchor="w")
        self.search_var = tk.StringVar()
        sr = ttk.Frame(sp)
        sr.pack(fill="x", pady=4)
        self.search_entry = ttk.Entry(sr, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(sr, text="Filter", command=self.apply_filter).pack(side="left", padx=6)
        ttk.Button(sr, text="Clear", command=self.clear_filter).pack(side="left")

        pv = ttk.Frame(sp)
        pv.pack(fill="both", expand=True)
        self.preview_list = tk.Listbox(pv, height=8, bg="#252526", fg="white")
        self.preview_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(pv, orient="vertical", command=self.preview_list.yview)
        sb.pack(side="right", fill="y")
        self.preview_list.config(yscrollcommand=sb.set)

        # ---- Progress Bar ----
        prog = ttk.Frame(root)
        prog.pack(padx=16, pady=(0,8), fill="x")
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(prog, textvariable=self.status_var).pack(anchor="w")
        self.progress = ttk.Progressbar(prog, mode="indeterminate")
        self.progress.pack(fill="x")

        # ---- Log ----
        logf = ttk.Frame(root)
        logf.pack(padx=16, pady=(0,16), fill="both", expand=True)
        ttk.Label(logf, text="Log:").pack(anchor="w")
        self.log = tk.Text(logf, wrap="word", bg="#252526", fg="white", insertbackground="white")
        self.log.pack(fill="both", expand=True)

        # ---- Internal state ----
        self.reference_files = []
        self.preview_results = {}  # ref_file -> target_dir
        self.filtered_preview_items = []
        self.base_dir = None

        # History stacks: list of batches, each batch is list of (src_path_after_move, dest_path_after_move)
        # We store moves as (from_path, to_path) that actually occurred, so we can reverse them.
        self.history = []
        self.redo_stack = []

    # ------------------------------ UI helpers ------------------------------
    def make_menu(self):
        menubar = tk.Menu(self.root)
        filem = tk.Menu(menubar, tearoff=0)
        filem.add_command(label="Choose Reference Files", command=self.choose_files)
        filem.add_command(label="Preview Matches", command=self.preview_matches)
        filem.add_command(label="Move Files", command=self.run_sorter)
        filem.add_separator()
        filem.add_command(label="Export Log", command=self.export_log)
        filem.add_separator()
        filem.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filem)

        editm = tk.Menu(menubar, tearoff=0)
        editm.add_command(label="Undo", command=self.undo_last)
        editm.add_command(label="Redo", command=self.redo_last)
        menubar.add_cascade(label="Edit", menu=editm)

        toolsm = tk.Menu(menubar, tearoff=0)
        toolsm.add_command(label="Orphan Finder", command=self.orphan_finder)
        toolsm.add_command(label="Duplicate Detector", command=self.duplicate_detector)
        menubar.add_cascade(label="Tools", menu=toolsm)

        self.root.config(menu=menubar)

    def log_line(self, text):
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def parse_extensions(self):
        raw = self.ext_entry.get().strip()
        if not raw:
            return None  # None means move all related files regardless of extension
        # Normalize: ensure each starts with dot where applicable
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        exts = set()
        for p in parts:
            if p.startswith('.') or p.startswith('*'):
                exts.add(p)
            else:
                exts.add('.' + p)
        return exts

    def pick_base_dir(self):
        if not self.base_dir:
            bd = filedialog.askdirectory(title="Select Base Folder to Search")
            if not bd:
                return None
            self.base_dir = bd
        return self.base_dir

    def start_progress(self, msg="Working..."):
        self.status_var.set(msg)
        self.progress.start(10)
        self.root.update_idletasks()

    def stop_progress(self, msg="Done"):
        self.progress.stop()
        self.status_var.set(msg)
        self.root.update_idletasks()

    def update_preview_list(self):
        self.preview_list.delete(0, tk.END)
        for ref_file, target_dir in self.preview_results.items():
            item = f"{os.path.basename(ref_file)}  →  {target_dir}"
            self.preview_list.insert(tk.END, item)
        self.filtered_preview_items = list(self.preview_results.items())

    def apply_filter(self):
        q = self.search_var.get().lower().strip()
        self.preview_list.delete(0, tk.END)
        if not q:
            for ref_file, target_dir in self.preview_results.items():
                self.preview_list.insert(tk.END, f"{os.path.basename(ref_file)}  →  {target_dir}")
            self.filtered_preview_items = list(self.preview_results.items())
            return
        filt = []
        for ref_file, target_dir in self.preview_results.items():
            name = os.path.basename(ref_file).lower()
            if q in name or q in target_dir.lower():
                filt.append((ref_file, target_dir))
        self.filtered_preview_items = filt
        for ref_file, target_dir in filt:
            self.preview_list.insert(tk.END, f"{os.path.basename(ref_file)}  →  {target_dir}")

    def clear_filter(self):
        self.search_var.set("")
        self.apply_filter()

    # ------------------------------ Core actions ------------------------------
    def choose_files(self):
        files = filedialog.askopenfilenames(title="Select Reference Files")
        if files:
            self.reference_files = list(files)
            self.log_line(f"Selected {len(files)} reference files.")

    def preview_matches(self):
        if not self.reference_files:
            messagebox.showerror("Error", "No reference files selected.")
            return
        base_dir = self.pick_base_dir()
        if not base_dir:
            return

        self.preview_results = {}
        self.log_line("--- Previewing Matches ---")
        self.start_progress("Scanning subfolders…")

        try:
            for ref_file in self.reference_files:
                ref_name, _ = os.path.splitext(os.path.basename(ref_file))
                match_found = False
                for root, _, files in os.walk(base_dir):
                    for file in files:
                        file_name, _ = os.path.splitext(file)
                        if file_name == ref_name:
                            self.preview_results[ref_file] = root
                            self.log_line(f"Match found: {os.path.basename(ref_file)} -> {root}")
                            match_found = True
                            break
                    if match_found:
                        break
                if not match_found:
                    self.log_line(f"No match found for {os.path.basename(ref_file)}")
        finally:
            self.stop_progress("Preview ready")

        if not self.preview_results:
            self.log_line("No matches found for any reference files.")
        else:
            self.log_line("Preview complete. Use 'Move Files' to confirm.")
        self.update_preview_list()

    def _resolve_conflict(self, dest_path):
        mode = self.conflict_mode.get()
        if mode == "overwrite":
            try:
                os.remove(dest_path)
            except FileNotFoundError:
                pass
            return dest_path
        elif mode == "rename":
            base, ext = os.path.splitext(dest_path)
            i = 1
            candidate = f"{base} ({i}){ext}"
            while os.path.exists(candidate):
                i += 1
                candidate = f"{base} ({i}){ext}"
            return candidate
        else:  # skip
            return None

    def _should_move_ext(self, filename, exts):
        if exts is None:
            return True
        # Accept exact ext match or special token '*.preview.png' etc if provided
        # We'll handle multi-dot extensions by comparing full tail after first dot
        for e in exts:
            if e.startswith('*'):
                # treat as wildcard suffix
                if filename.endswith(e[1:]):
                    return True
            else:
                if filename.endswith(e):
                    return True
        return False

    def run_sorter(self):
        if not self.reference_files:
            messagebox.showerror("Error", "No reference files selected.")
            return

        if self.auto_confirm.get() and not self.preview_results:
            # auto preview using stored base_dir or ask
            base_dir = self.pick_base_dir()
            if not base_dir:
                return
            self.preview_matches()

        if not self.preview_results:
            messagebox.showerror("Error", "No preview results available. Run Preview first or enable Auto-confirm.")
            return

        exts = self.parse_extensions()
        batch_moves = []  # list of (src, dest) that actually happened
        self.start_progress("Moving files…")
        try:
            for ref_file, target_dir in self.preview_results.items():
                ref_name, _ = os.path.splitext(os.path.basename(ref_file))
                ref_dir = os.path.dirname(ref_file)
                # Move all related files from the ref_dir
                for related in os.listdir(ref_dir):
                    related_name, _ = os.path.splitext(related)
                    if related_name == ref_name and self._should_move_ext(related, exts):
                        src_path = os.path.join(ref_dir, related)
                        dest_path = os.path.join(target_dir, related)
                        if os.path.exists(dest_path):
                            new_dest = self._resolve_conflict(dest_path)
                            if new_dest is None:
                                self.log_line(f"Skipped {related} (exists in {target_dir})")
                                continue
                            else:
                                dest_path = new_dest
                        shutil.move(src_path, dest_path)
                        self.log_line(f"Moved {related} → {target_dir}")
                        batch_moves.append((dest_path, src_path))  # store reverse: from current location back to original
        finally:
            self.stop_progress("Move complete")

        if batch_moves:
            self.history.append(batch_moves)
            self.redo_stack.clear()
            self.log_line("--- File moving complete ---")
        else:
            self.log_line("No files moved.")

    # ------------------------------ Undo/Redo ------------------------------
    def undo_last(self):
        if not self.history:
            self.log_line("Nothing to undo.")
            return
        batch = self.history.pop()
        undone = []
        self.start_progress("Undoing last batch…")
        try:
            for current_path, original_path in reversed(batch):
                # current_path is where file is now; move it back to original_path
                if not os.path.exists(current_path):
                    self.log_line(f"Missing file (cannot undo): {current_path}")
                    continue
                # Handle conflicts at original location using same policy
                if os.path.exists(original_path):
                    new_dest = self._resolve_conflict(original_path)
                    if new_dest is None:
                        self.log_line(f"Undo skipped (exists): {os.path.basename(original_path)}")
                        continue
                    else:
                        original_path = new_dest
                shutil.move(current_path, original_path)
                undone.append((original_path, current_path))
                self.log_line(f"Restored {os.path.basename(original_path)}")
        finally:
            self.stop_progress("Undo complete")
        if undone:
            self.redo_stack.append(undone)

    def redo_last(self):
        if not self.redo_stack:
            self.log_line("Nothing to redo.")
            return
        batch = self.redo_stack.pop()
        redone = []
        self.start_progress("Redoing…")
        try:
            for current_path, original_path in reversed(batch):
                # Move back to the path before undo
                if not os.path.exists(current_path):
                    self.log_line(f"Missing file (cannot redo): {current_path}")
                    continue
                if os.path.exists(original_path):
                    new_dest = self._resolve_conflict(original_path)
                    if new_dest is None:
                        self.log_line(f"Redo skipped (exists): {os.path.basename(original_path)}")
                        continue
                    else:
                        original_path = new_dest
                shutil.move(current_path, original_path)
                redone.append((original_path, current_path))
                self.log_line(f"Re-moved {os.path.basename(original_path)}")
        finally:
            self.stop_progress("Redo complete")
        if redone:
            self.history.append(redone)

    # ------------------------------ Tools ------------------------------
    def orphan_finder(self):
        base_dir = self.pick_base_dir()
        if not base_dir:
            return
        exts = self.parse_extensions()
        if not exts:
            messagebox.showinfo("Orphan Finder", "Please specify the extensions list to check for orphans.")
            return
        self.log_line("--- Orphan Finder ---")
        self.start_progress("Scanning for orphans…")
        try:
            # Map: directory -> base_name -> set(exts present)
            dir_map = defaultdict(lambda: defaultdict(set))
            for root, _, files in os.walk(base_dir):
                for f in files:
                    base, ext = os.path.splitext(f)
                    # Handle multi-dot extensions by checking suffixes in exts
                    for e in exts:
                        if e.startswith('*'):
                            if f.endswith(e[1:]):
                                dir_map[root][base].add(e)
                        else:
                            if f.endswith(e):
                                dir_map[root][base].add(e)
            expected = set(exts)
            found_any = False
            for root, base_dict in dir_map.items():
                for base, have in base_dict.items():
                    missing = expected - have
                    if missing:
                        found_any = True
                        self.log_line(f"Orphan: {base} in {root} missing {sorted(missing)}")
            if not found_any:
                self.log_line("No orphans found.")
        finally:
            self.stop_progress("Orphan scan complete")

    def duplicate_detector(self):
        base_dir = self.pick_base_dir()
        if not base_dir:
            return
        self.log_line("--- Duplicate Detector ---")
        self.start_progress("Scanning for duplicates…")
        try:
            # Map base name -> set of directories containing it
            locations = defaultdict(set)
            for root, _, files in os.walk(base_dir):
                for f in files:
                    base, _ = os.path.splitext(f)
                    locations[base].add(root)
            dups = {b: dirs for b, dirs in locations.items() if len(dirs) > 1}
            if not dups:
                self.log_line("No duplicates found across subfolders.")
            else:
                for b, dirs in dups.items():
                    self.log_line(f"Duplicate base '{b}' found in:")
                    for d in sorted(dirs):
                        self.log_line(f"  - {d}")
        finally:
            self.stop_progress("Duplicate scan complete")

    def export_log(self):
        content = self.log.get("1.0", tk.END)
        if not content.strip():
            messagebox.showinfo("Export Log", "Log is empty.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log_line(f"Log exported to: {path}")
        except Exception as e:
            messagebox.showerror("Export Log", f"Failed to save log: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LoRASorterApp(root)
    root.mainloop()
