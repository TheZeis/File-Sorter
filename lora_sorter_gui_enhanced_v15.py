import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import defaultdict

class LoRASorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LoRA Sorter – Enhanced")
        self.root.geometry("1200x720")
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

        self.base_folder_button = ttk.Button(top, text="Set Base Folder", command=self.set_base_folder)
        self.base_folder_button.grid(row=0, column=1, padx=(0,8))

        ttk.Label(top, text="Base Folder:").grid(row=0, column=2, sticky="w")
        self.base_folder_var = tk.StringVar(value="Not selected")
        self.base_folder_label = ttk.Label(top, textvariable=self.base_folder_var)
        self.base_folder_label.grid(row=0, column=3, sticky="w", padx=(0,8))

        ttk.Label(top, text="Extensions (comma-separated)").grid(row=0, column=4, sticky="w")
        self.ext_entry = ttk.Entry(top, width=45)
        self.ext_entry.grid(row=0, column=5, padx=6)
        self.ext_entry.insert(0, ".html,.civitai.info,.json,.preview.png,.safetensors")

        ttk.Label(top, text="On conflict:").grid(row=0, column=6, padx=(16,4))
        self.conflict_mode = tk.StringVar(value="skip")
        self.conflict_combo = ttk.Combobox(top, textvariable=self.conflict_mode, state="readonly", width=12,
                                           values=["skip", "overwrite", "rename"])
        self.conflict_combo.grid(row=0, column=7)

        self.auto_confirm = tk.BooleanVar()
        self.auto_confirm_check = ttk.Checkbutton(top, text="Auto-confirm", variable=self.auto_confirm)
        self.auto_confirm_check.grid(row=0, column=8, padx=(16,0))

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
        self.move_orphans_button = ttk.Button(actions, text="Move Orphans to Sibling Folder", command=self.move_orphans_to_sibling)
        self.move_orphans_button.pack(side="left", padx=8)
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

        # ---- Log area ----
        logf = ttk.Frame(root)
        logf.pack(padx=16, pady=(0,16), fill="both", expand=True)
        log_pane = ttk.PanedWindow(logf, orient=tk.HORIZONTAL)
        log_pane.pack(fill="both", expand=True)

        # Regular log
        reg_frame = ttk.Frame(log_pane)
        ttk.Label(reg_frame, text="Log:").pack(anchor="w")
        self.log = tk.Text(reg_frame, wrap="word", bg="#252526", fg="white", insertbackground="white", width=80)
        self.log.pack(fill="both", expand=True)
        log_pane.add(reg_frame, weight=2)

        # Debug log
        dbg_frame = ttk.Frame(log_pane)
        ttk.Label(dbg_frame, text="Debug Log:").pack(anchor="w")
        self.debug_log = tk.Text(dbg_frame, wrap="word", bg="#181818", fg="#c0ff80", insertbackground="#c0ff80", width=80)
        self.debug_log.pack(fill="both", expand=True)
        log_pane.add(dbg_frame, weight=2)

        # ---- Internal state ----
        self.reference_files = []
        self.preview_results = {}  # ref_file -> list of sibling file paths
        self.filtered_preview_items = []
        self.base_dir = None

        self.history = []
        self.redo_stack = []

        self.orphan_map = {} # base_name -> { 'orphan': [file_in_base], 'siblings': [files_in_subfolders] }

    # ------------------------------ UI helpers ------------------------------
    def make_menu(self):
        menubar = tk.Menu(self.root)
        filem = tk.Menu(menubar, tearoff=0)
        filem.add_command(label="Choose Reference Files", command=self.choose_files)
        filem.add_command(label="Set Base Folder", command=self.set_base_folder)
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
        toolsm.add_command(label="Move Orphans to Sibling Folder", command=self.move_orphans_to_sibling)
        toolsm.add_command(label="Duplicate Detector", command=self.duplicate_detector)
        menubar.add_cascade(label="Tools", menu=toolsm)

        self.root.config(menu=menubar)

    def log_line(self, text):
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def debug_log_line(self, text):
        self.debug_log.insert(tk.END, text + "\n")
        self.debug_log.see(tk.END)

    def parse_extensions(self):
        raw = self.ext_entry.get().strip()
        if not raw:
            return None  # None means move all related files regardless of extension
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
            self.base_folder_var.set(self.base_dir)
        return self.base_dir

    def set_base_folder(self):
        bd = filedialog.askdirectory(title="Select Base Folder to Search")
        if bd:
            self.base_dir = bd
            self.base_folder_var.set(self.base_dir)
            self.log_line(f"Base folder set to: {self.base_dir}")

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
        for ref_file, sibling_paths in self.preview_results.items():
            for sib in sibling_paths:
                item = f"{os.path.basename(ref_file)}  →  {sib}"
                self.preview_list.insert(tk.END, item)
        self.filtered_preview_items = [
            (ref_file, sib)
            for ref_file, sibling_paths in self.preview_results.items()
            for sib in sibling_paths
        ]

    def apply_filter(self):
        q = self.search_var.get().lower().strip()
        self.preview_list.delete(0, tk.END)
        if not q:
            for ref_file, sibling_paths in self.preview_results.items():
                for sib in sibling_paths:
                    self.preview_list.insert(tk.END, f"{os.path.basename(ref_file)}  →  {sib}")
            self.filtered_preview_items = [
                (ref_file, sib)
                for ref_file, sibling_paths in self.preview_results.items()
                for sib in sibling_paths
            ]
            return
        filt = []
        for ref_file, sibling_paths in self.preview_results.items():
            for sib in sibling_paths:
                name = os.path.basename(ref_file).lower()
                sib_path = sib.lower()
                if q in name or q in sib_path:
                    filt.append((ref_file, sib))
        self.filtered_preview_items = filt
        for ref_file, sib in filt:
            self.preview_list.insert(tk.END, f"{os.path.basename(ref_file)}  →  {sib}")

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
        base_dir = self.base_dir if self.base_dir else self.pick_base_dir()
        if not base_dir:
            return

        self.preview_results = {}
        self.log_line("--- Previewing Sibling Matches ---")
        self.debug_log_line("--- [DEBUG] Previewing Sibling Matches ---")
        self.start_progress("Scanning subfolders…")

        try:
            for ref_file in self.reference_files:
                ref_basename = os.path.basename(ref_file).split('.')[0]
                ref_path = os.path.abspath(ref_file)
                ref_folder = os.path.abspath(os.path.dirname(ref_file))
                self.debug_log_line(f"[DEBUG] Reference file: {ref_file}")
                self.debug_log_line(f"[DEBUG] Reference base name for match: {ref_basename}")
                self.debug_log_line(f"[DEBUG] Reference folder (to skip): {ref_folder}")
                sibling_files = []
                # Only walk subfolders, not base folder itself
                for entry in os.scandir(base_dir):
                    if entry.is_dir():
                        folder_path = os.path.abspath(entry.path)
                        self.debug_log_line(f"[DEBUG] Scanning folder: {folder_path}")
                        if folder_path == ref_folder:
                            self.debug_log_line(f"[DEBUG] Skipping reference folder: {folder_path}")
                            continue
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                file_basename = file.split('.')[0]
                                candidate_path = os.path.abspath(os.path.join(root, file))
                                self.debug_log_line(f"[DEBUG] Found file: {candidate_path} (basename: {file_basename})")
                                if file_basename == ref_basename:
                                    if candidate_path != ref_path:
                                        self.debug_log_line(f"[DEBUG] Sibling match: {candidate_path}")
                                        sibling_files.append(candidate_path)
                                    else:
                                        self.debug_log_line(f"[DEBUG] Skipped (is reference file itself): {candidate_path}")
                                else:
                                    self.debug_log_line(f"[DEBUG] Skipped (base mismatch): {candidate_path}")
                if sibling_files:
                    self.preview_results[ref_file] = sibling_files
                    for sib in sibling_files:
                        self.log_line(f"Sibling found: {os.path.basename(ref_file)} -> {sib}")
                else:
                    self.log_line(f"No siblings found for {os.path.basename(ref_file)}")
        finally:
            self.stop_progress("Preview ready")

        if not self.preview_results:
            self.log_line("No siblings found for any reference files.")
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

    def run_sorter(self):
        # Move only the reference file to each sibling's folder
        if not self.reference_files:
            messagebox.showerror("Error", "No reference files selected.")
            return

        if self.auto_confirm.get() and not self.preview_results:
            base_dir = self.base_dir if self.base_dir else self.pick_base_dir()
            if not base_dir:
                return
            self.preview_matches()

        if not self.preview_results:
            messagebox.showerror("Error", "No preview results available. Run Preview first or enable Auto-confirm.")
            return

        batch_moves = []  # list of (src, dest) that actually happened
        self.start_progress("Moving files…")
        try:
            for ref_file, sibling_paths in self.preview_results.items():
                ref_basename = os.path.basename(ref_file)
                ref_path = os.path.abspath(ref_file)
                for sib_path in sibling_paths:
                    target_dir = os.path.dirname(sib_path)
                    dest_path = os.path.join(target_dir, ref_basename)
                    if ref_path == os.path.abspath(dest_path):
                        self.log_line(f"Skipped {ref_basename} (already in {target_dir})")
                        continue
                    if os.path.exists(dest_path):
                        new_dest = self._resolve_conflict(dest_path)
                        if new_dest is None:
                            self.log_line(f"Skipped {ref_basename} (exists in {target_dir})")
                            continue
                        else:
                            dest_path = new_dest
                    shutil.move(ref_file, dest_path)
                    self.log_line(f"Moved {ref_basename} → {target_dir}")
                    batch_moves.append((dest_path, ref_file))
                    # After moving, update ref_file to the new location for undo/redo
                    ref_file = dest_path
                    ref_path = os.path.abspath(ref_file)
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
                if not os.path.exists(current_path):
                    self.log_line(f"Missing file (cannot undo): {current_path}")
                    continue
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
        # Find orphans and store mapping for Move Orphans tool
        base_dir = self.base_dir if self.base_dir else self.pick_base_dir()
        if not base_dir:
            return
        exts = self.parse_extensions()
        if not exts:
            messagebox.showinfo("Orphan Finder", "Please specify the extensions list to check for orphans.")
            return
        self.log_line("--- Orphan Finder ---")
        self.start_progress("Scanning for orphans…")
        self.orphan_map = defaultdict(lambda: {'orphan': [], 'siblings': []})
        try:
            # Map: base_name -> set(exts present) for each folder
            folder_map = defaultdict(lambda: defaultdict(set))
            for root, _, files in os.walk(base_dir):
                for f in files:
                    base, ext = os.path.splitext(f)
                    for e in exts:
                        if e.startswith('*'):
                            if f.endswith(e[1:]):
                                folder_map[root][base].add(e)
                        else:
                            if f.endswith(e):
                                folder_map[root][base].add(e)
            expected = set(exts)
            found_any = False
            # Find orphans in base folder only
            for base, have in folder_map[base_dir].items():
                missing = expected - have
                if missing:
                    found_any = True
                    self.log_line(f"Orphan: {base} in {base_dir} missing {sorted(missing)}")
                    # Find actual orphan files
                    for e in have:
                        for f in os.listdir(base_dir):
                            if f.startswith(base) and (f.endswith(e[1:]) if e.startswith('*') else f.endswith(e)):
                                self.orphan_map[base]['orphan'].append(os.path.join(base_dir, f))
                    # Find siblings in subfolders
                    for folder in folder_map:
                        if folder == base_dir:
                            continue
                        if base in folder_map[folder]:
                            for e2 in folder_map[folder][base]:
                                for f in os.listdir(folder):
                                    if f.startswith(base) and (f.endswith(e2[1:]) if e2.startswith('*') else f.endswith(e2)):
                                        self.orphan_map[base]['siblings'].append(os.path.join(folder, f))
            if not found_any:
                self.log_line("No orphans found.")
        finally:
            self.stop_progress("Orphan scan complete")

    def move_orphans_to_sibling(self):
        # Move each orphan file to the folder of its sibling (if found)
        if not self.orphan_map:
            messagebox.showinfo("Move Orphans", "No orphan mapping found. Run Orphan Finder first.")
            return
        self.start_progress("Moving orphans…")
        batch_moves = []
        try:
            for base, info in self.orphan_map.items():
                orphans = info['orphan']
                siblings = info['siblings']
                if not siblings or not orphans:
                    continue
                # Move each orphan to the folder of the first sibling found
                target_folder = os.path.dirname(os.path.normpath(siblings[0]))
                for orphan_file in orphans:
                    orphan_file = os.path.normpath(orphan_file)
                    orphan_basename = os.path.basename(orphan_file)
                    dest_path = os.path.join(target_folder, orphan_basename)
                    dest_path = os.path.normpath(dest_path)
                    if not os.path.exists(orphan_file):
                        self.log_line(f"Skipped (not found): {orphan_file}")
                        continue
                    if os.path.abspath(orphan_file) == os.path.abspath(dest_path):
                        self.log_line(f"Skipped {orphan_basename} (already in {target_folder})")
                        continue
                    if os.path.exists(dest_path):
                        new_dest = self._resolve_conflict(dest_path)
                        if new_dest is None:
                            self.log_line(f"Skipped {orphan_basename} (exists in {target_folder})")
                            continue
                        else:
                            dest_path = new_dest
                    try:
                        shutil.move(orphan_file, dest_path)
                        self.log_line(f"Moved orphan {orphan_basename} → {target_folder}")
                        batch_moves.append((dest_path, orphan_file))
                    except Exception as e:
                        self.log_line(f"Error moving {orphan_basename}: {e}")
        finally:
            self.stop_progress("Orphan move complete")
        if batch_moves:
            self.history.append(batch_moves)
            self.redo_stack.clear()
            self.log_line("--- Orphan file moving complete ---")
        else:
            self.log_line("No orphan files moved.")

    def duplicate_detector(self):
        base_dir = self.base_dir if self.base_dir else self.pick_base_dir()
        if not base_dir:
            return
        self.log_line("--- Duplicate Detector ---")
        self.start_progress("Scanning for duplicates…")
        try:
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
        dbg_content = self.debug_log.get("1.0", tk.END)
        if not content.strip() and not dbg_content.strip():
            messagebox.showinfo("Export Log", "Log is empty.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("=== Main Log ===\n")
                f.write(content)
                f.write("\n\n=== Debug Log ===\n")
                f.write(dbg_content)
            self.log_line(f"Log exported to: {path}")
        except Exception as e:
            messagebox.showerror("Export Log", f"Failed to save log: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LoRASorterApp(root)
    root.mainloop()