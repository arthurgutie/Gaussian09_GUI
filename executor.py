import tkinter as tk
from tkinter import ttk, messagebox
import os
from pathlib import Path
import threading
import time

class ExecutorModule(tk.LabelFrame):
    def __init__(self, parent, ssh_manager, terminal, config=None):
        super().__init__(parent, text="Execution & Process Monitoring", padx=15, pady=15, bg="#e7f5ff")
        self.ssh_manager = ssh_manager
        self.terminal = terminal
        self.is_running = False
        
        self.output_path = Path.cwd() / "Output"
        self.output_path.mkdir(parents=True, exist_ok=True)

        config = config or {}
        self.last_path = config.get("last_path", "")
        
        self._create_widgets()
        self.refresh_file_list()

    def _create_widgets(self):
        self.paned = tk.PanedWindow(self, orient="horizontal", sashrelief="raised", sashwidth=4, bg="#e7f5ff")
        self.paned.pack(fill="both", expand=True)

        # --- LEFT: FILE TREE ---
        left_side = tk.Frame(self.paned, bg="#e7f5ff")
        self.paned.add(left_side, width=280)

        self.tree = ttk.Treeview(left_side, show="tree")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_file_select)
        
        # Style for the newest file
        self.tree.tag_configure("newest", font=("Consolas", 9, "bold"), foreground="#087f5b", background="#e6fcf5")

        btn_frame = tk.Frame(left_side, pady=10, bg="#e7f5ff")
        btn_frame.pack(fill="x")
        
        # Row 1: Basic controls
        l1 = tk.Frame(btn_frame, bg="#e7f5ff"); l1.pack(fill="x")
        tk.Button(l1, text=" 🔄 ", command=self.refresh_file_list, width=3).pack(side="left", padx=2)
        self.run_btn = tk.Button(l1, text=" 🚀 Run ", command=self.start_thread_execution, bg="#40c057", fg="white", font=("Arial", 9, "bold"))
        self.run_btn.pack(side="right", padx=2)
        self.kill_btn = tk.Button(l1, text=" 🛑 Stop ", command=self.kill_calculation, bg="#ff8787", font=("Arial", 9, "bold"))
        self.kill_btn.pack(side="right", padx=2)

        self.btn_del = tk.Button(l1, text=" 🗑 Delete ", command=self.delete_selected_file, bg="#fa5252", fg="white", font=("Arial", 8, "bold"))
        self.btn_del.pack(side="right", fill="x", expand=True, padx=2)

        # Row 2: Monitoring, Sync & Delete
        l2 = tk.Frame(btn_frame, pady=5, bg="#e7f5ff"); l2.pack(fill="x")
        self.btn_check = tk.Button(l2, text=" 🔍 Check SCF ", command=self.check_remote_progress, bg="#845ef7", fg="white", font=("Arial", 8))
        self.btn_check.pack(side="left", fill="x", expand=True, padx=2)
        
        self.btn_sync = tk.Button(l2, text=" 📥 Sync ", command=self.check_and_recover, bg="#339af0", fg="white", font=("Arial", 8))
        self.btn_sync.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_tail_log = tk.Button(l2, text="👁️ Tail Log", command=self.tail_current_remote_log, bg="#f59f00", fg="white", font=("Arial", 8, "bold"))
        self.btn_tail_log.pack(side="left", fill="x", expand=True, padx=2)
        
        # Row 3: Core state analysis (pstree)
        l3 = tk.Frame(btn_frame, pady=5, bg="#e7f5ff")
        l3.pack(fill="x")
        tk.Label(l3, text="PID:", font=("Arial", 8, "bold"), bg="#e7f5ff").pack(side="left", padx=2)
        self.ent_pid_check = tk.Entry(l3, width=8, font=("Consolas", 9))
        self.ent_pid_check.pack(side="left", padx=2)
        
        tk.Button(l3, text="🌳 pstree", command=self.check_pstree, bg="#f76707", fg="white", font=("Arial", 8)).pack(side="left", padx=2)
        
        # --- RIGHT: PREVIEW & EDIT ---
        right_side = tk.Frame(self.paned, bg="#e7f5ff")
        self.paned.add(right_side, stretch="always")

        edit_tools = tk.Frame(right_side, bg="#e7f5ff")
        edit_tools.pack(fill="x", pady=(0, 5))
        
        tk.Label(edit_tools, text="Keywords:", font=("Arial", 8, "bold"), bg="#e7f5ff").pack(side="left", padx=5)
        self.kw_dict = ttk.Combobox(edit_tools, values=[
            "EmpiricalDispersion=GD3", "Geom=Connectivity", "Freq=HPModes", 
            "SCRF=(Solvent=Water)", "IOP(1/11=1)", "Pop=Full", "MaxStep=30"
        ], width=20)
        self.kw_dict.pack(side="left", padx=5)
        tk.Button(edit_tools, text="Add", command=self.add_keyword, font=("Arial", 7)).pack(side="left")
        tk.Button(edit_tools, text="💾 Save", command=self.save_preview, bg="#1971c2", fg="white", font=("Arial", 8)).pack(side="right", padx=5)

        self.preview_text = tk.Text(right_side, font=("Consolas", 10), undo=True, bg="#ffffff")
        self.preview_text.pack(fill="both", expand=True)

    def safe_log(self, msg, tag=None):
        self.after(0, lambda: self.terminal.write_log(msg, tag))

    def _get_sub_dir(self, local_path):
        """Extracts the tree structure (Project/Molecule) relative to the Output folder for the remote server"""
        try:
            return local_path.relative_to(self.output_path).parent.as_posix()
        except ValueError:
            return ""

    def tail_current_remote_log(self):
        """Reads the last lines of the remote log and displays it in the preview area."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a .gjf file in the tree to target the remote log.")
            return
        if not self.ssh_manager.is_connected:
            messagebox.showwarning("Connection", "You must be connected to the SSH server.")
            return

        local_path = Path(self.tree.item(selected[0])['values'][0])
        sub_dir = self._get_sub_dir(local_path)
        remote_log_name = local_path.name.replace(".gjf", ".log")
        cmd = f"tail -n 20 '{remote_log_name}'"

        def run():
            self.safe_log(f"Reading the last 20 lines of {remote_log_name}...", "info")
            ok, out = self.ssh_manager.run_command_sync(cmd, sub_dir=sub_dir)
            
            def update_ui():
                self.preview_text.delete("1.0", tk.END)
                if ok:
                    self.preview_text.insert("1.0", f"--- REMOTE LOG TAIL (LIVE FROM SERVER) ---\n\n{out}")
                else:
                    self.preview_text.insert("1.0", f"❌ Unable to read {remote_log_name}.\nThe calculation might not have started writing yet.")
            self.after(0, update_ui)

        threading.Thread(target=run, daemon=True).start()

    def _get_newest_gjf(self):
        try:
            files = [p for p in self.output_path.rglob('*.gjf') if p.is_file()]
            if not files: return None
            return max(files, key=lambda p: p.stat().st_mtime)
        except Exception:
            return None

    def on_file_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        path_str = self.tree.item(selected[0])['values'][0]
        path = Path(path_str)
        if path.is_file() and path.suffix.lower() == ".gjf":
            try:
                with open(path, 'r') as f:
                    content = f.read()
                self.preview_text.delete("1.0", tk.END)
                self.preview_text.insert("1.0", content)
                self.last_path = path_str
            except Exception: pass

    def check_remote_progress(self):
        selected = self.tree.selection()
        if not selected or not self.ssh_manager.is_connected: return
        
        local_path = Path(self.tree.item(selected[0])['values'][0])
        sub_dir = self._get_sub_dir(local_path)
        log_name = local_path.name.replace(".gjf", ".log")
        chk_name = local_path.name.replace(".gjf", ".chk")
        cmd = f"grep -i 'scf done' {log_name} | tail -n 5"
        
        def run():
            self.safe_log(f"Checking progress for {log_name}...", "info")
            ok, out = self.ssh_manager.run_command_sync(cmd, sub_dir=sub_dir)
            chk_size = self.ssh_manager.get_remote_file_size(chk_name, sub_dir=sub_dir)
            
            if ok:
                msg = out if out else "(No SCF Done found yet)"
                self.safe_log(f"--- [PROGRESS] {log_name} ---\n.chk size: {chk_size}\n{msg}", "success")
            else:
                self.safe_log(f"--- [PROGRESS] {log_name} ---\n.chk size: {chk_size}\n(Log file not found or empty)", "error")
                
        threading.Thread(target=run, daemon=True).start()

    def check_pstree(self):
        pid = self.ent_pid_check.get().strip()
        if not pid or not self.ssh_manager.is_connected:
            messagebox.showwarning("Warning", "Please provide a valid PID and check your SSH link.")
            return
            
        def run():
            self.safe_log(f"Requesting core tree status for PID {pid}...", "info")
            ok, out = self.ssh_manager.run_command_sync(f"pstree -p {pid}")
            if ok and out:
                core_count = out.count("g09")
                self.safe_log(f"--- [CORE TREE STATUS] ---\n{out}\n🎯 Status: Job running on {core_count} sub-cores.", "success")
            else:
                self.safe_log(f"PID {pid} not found on server or terminated.", "error")
        threading.Thread(target=run, daemon=True).start()

    def check_and_recover(self):
        selected = self.tree.selection()
        if not selected or not self.ssh_manager.is_connected: return
        local_path = Path(self.tree.item(selected[0])['values'][0])
        sub_dir = self._get_sub_dir(local_path)
        
        def run():
            self.safe_log("Syncing with server...", "info")
            for ext in [".log", ".chk"]:
                remote_f = local_path.name.replace(".gjf", ext)
                if self.ssh_manager.download_file(remote_f, local_path.parent / remote_f, sub_dir=sub_dir):
                    self.safe_log(f"Recovered: {remote_f}", "success")
            self.after(0, self.refresh_file_list)
        threading.Thread(target=run, daemon=True).start()

    def delete_selected_file(self):
        selected = self.tree.selection()
        if not selected: return
        path_str = self.tree.item(selected[0])['values'][0]
        path = Path(path_str)
        if path.is_file():
            if messagebox.askyesno("Confirmation", f"Permanently delete {path.name}?"):
                try:
                    path.unlink()
                    self.safe_log(f"🗑️ Local file deleted: {path.name}", "success")
                    self.preview_text.delete("1.0", tk.END)
                    self.refresh_file_list()
                except Exception as e:
                    messagebox.showerror("Error", f"Unable to delete file: {e}")

    def kill_calculation(self):
        selected = self.tree.selection()
        if not selected or not self.ssh_manager.is_connected: return
        local_path = Path(self.tree.item(selected[0])['values'][0])
        sub_dir = self._get_sub_dir(local_path)
        filename = local_path.name
        find_pid_cmd = f"ps -u $USER -opid,cmd | grep 'g09' | grep '{filename}' | grep -v grep | awk '{{print $1}}'"
        
        def run():
            ok, pid = self.ssh_manager.run_command_sync(find_pid_cmd, sub_dir=sub_dir)
            if ok and pid.strip():
                for p in pid.strip().split('\n'):
                    self.ssh_manager.run_command_sync(f"kill -9 {p}", sub_dir=sub_dir)
                    self.safe_log(f"Terminated: {filename} (PID {p})", "error")
            else:
                self.safe_log(f"No active process found for {filename}", "info")
        threading.Thread(target=run, daemon=True).start()

    def start_thread_execution(self):
        selected = self.tree.selection()
        if not selected: return
        path_str = self.tree.item(selected[0])['values'][0]
        threading.Thread(target=self.run_calculation, args=(Path(path_str),), daemon=True).start()

    def run_calculation(self, local_path):
        if not self.ssh_manager.is_connected: return
        self.is_running = True
        self.after(0, lambda: self.run_btn.config(state="disabled"))
        
        sub_dir = self._get_sub_dir(local_path)
        filename = local_path.name
        log_name = filename.replace(".gjf", ".log")
        chk_name = filename.replace(".gjf", ".chk")

        self.safe_log(f"Uploading {filename} to {sub_dir}...", "info")
        if self.ssh_manager.upload_file(local_path, filename, sub_dir=sub_dir):
            cmd = f"sed -i 's/\\r$//' {filename} && g09 < {filename} > {log_name}"
            pid = self.ssh_manager.execute_command_background(cmd, sub_dir=sub_dir)
            if pid:
                self.safe_log(f"🚀 Job Started! PID: {pid}", "success")
                self.after(0, lambda: self.ent_pid_check.delete(0, tk.END))
                self.after(0, lambda: self.ent_pid_check.insert(0, str(pid)))
                self.after(0, lambda: self.kill_btn.config(state="normal"))
                self.monitor_process(pid, log_name, chk_name, local_path.parent, sub_dir)
        self._reset_states()

    def monitor_process(self, pid, log_name, chk_name, download_dir, sub_dir):
        """Asynchronously monitors the remote job status, handles network disconnections gracefully, and downloads the output files upon completion"""
        while self.is_running:
            try:
                success, out = self.ssh_manager.run_command_sync(f"ps -p {pid}")
                
                if not success:
                    if "Not connected" in str(out) or "Connection lost" in str(out):
                        self.safe_log("⚠️ SSH connection lost or PC asleep. Waiting...", "error")
                        time.sleep(20)
                        continue
                    else:
                        self.safe_log(f"Process {pid} no longer detected. Job finished or interrupted.", "info")
                        break
                else:
                    pass
                    
            except Exception:
                self.safe_log("⚠️ Network error detected. Resuming tracking once connection is restored...", "error")
                time.sleep(20)
                continue
            time.sleep(5)
        
        self.safe_log(f"Job finished. Downloading final files (Job: {pid})...", "success")
        for f in [log_name, chk_name]:
            if self.ssh_manager.download_file(f, download_dir / f, sub_dir=sub_dir):
                self.safe_log(f"Successfully downloaded: {f}", "success")
        self.after(0, self.refresh_file_list)

    def add_keyword(self):
        kw = self.kw_dict.get()
        if not kw: return
        lines = self.preview_text.get("1.0", tk.END).splitlines()
        for i, line in enumerate(lines):
            if line.startswith("#"):
                lines[i] = f"{line.strip()} {kw}"
                break
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", "\n".join(lines))

    def save_preview(self):
        selected = self.tree.selection()
        if not selected: return
        path_str = self.tree.item(selected[0])['values'][0]
        
        # Taking 'end-1c' instead of tk.END to prevent adding a newline on each save
        with open(path_str, 'w') as f:
            f.write(self.preview_text.get("1.0", "end-1c"))
            
        self.safe_log(f"Updated: {Path(path_str).name}", "success")

    def refresh_file_list(self):
        self.newest_file = self._get_newest_gjf()
        for i in self.tree.get_children(): self.tree.delete(i)
        self._populate_node("", self.output_path)

    def _populate_node(self, parent_node, current_path):
        try:
            for path in sorted(current_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if path.is_dir():
                    node = self.tree.insert(parent_node, "end", text=f"  📁 {path.name}", open=False, values=(str(path),))
                    self._populate_node(node, path)
                elif path.suffix.lower() == ".gjf":
                    tags = ("newest",) if getattr(self, 'newest_file', None) == path else ()
                    self.tree.insert(parent_node, "end", text=f"  📄 {path.name}", values=(str(path),), tags=tags)
        except Exception: pass

    def _reset_states(self):
        self.is_running = False
        self.after(0, lambda: self.run_btn.config(state="normal"))
        self.after(0, lambda: self.kill_btn.config(state="disabled"))

    def get_state(self): return {"last_path": str(self.last_path)}