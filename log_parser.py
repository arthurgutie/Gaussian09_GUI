import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import os
from pathlib import Path
import threading
import csv
import math
import platform

class AnalyzerModule(tk.LabelFrame):
    def __init__(self, parent, ssh_manager, terminal):
        super().__init__(parent, text="Analysis & Energy History", padx=15, pady=15, bg="#e9f1f7")
        self.ssh_manager = ssh_manager
        self.terminal = terminal
        
        self.output_path = Path.cwd() / "Output"
        self.output_path.mkdir(parents=True, exist_ok=True)
            
        self.current_target = None
        self._create_widgets()
        self.refresh_log_list()

    def _create_widgets(self):
        self.paned = tk.PanedWindow(self, orient="horizontal", sashrelief="raised", sashwidth=4)
        self.paned.pack(fill="both", expand=True)

        # --- LEFT: LOCAL LOG FILES LIST ---
        self.list_frame = tk.Frame(self.paned)
        self.paned.add(self.list_frame, width=250)
        
        tk.Label(self.list_frame, text="Local Log Files", font=("Arial", 9, "bold")).pack(pady=2)
        self.tree_logs = ttk.Treeview(self.list_frame, show="tree")
        self.tree_logs.pack(fill="both", expand=True)
        self.tree_logs.bind("<<TreeviewSelect>>", self.on_log_select)
        
        tk.Button(self.list_frame, text=" 🔄 Refresh List ", command=self.refresh_log_list, font=("Arial", 8)).pack(fill="x")

        self.btn_open_log = tk.Button(self.list_frame, text="📖 Open Log File", font=("Arial", 9, "bold"), bg="#d3f9d8", command=self.open_selected_log_file)
        self.btn_open_log.pack(fill="x", padx=5, pady=5)

        # --- MIDDLE: ANALYSIS DASHBOARD ---
        mid_frame = tk.Frame(self.paned)
        self.paned.add(mid_frame, stretch="always")

        top_bar = tk.Frame(mid_frame)
        top_bar.pack(fill="x", pady=(0, 10))

        self.btn_run = tk.Button(top_bar, text=" 📊 Deep Analysis ", command=self.start_analysis, 
                                 bg="#1971c2", fg="white", font=("Segoe UI", 9, "bold"), relief="flat")
        self.btn_run.pack(side="left", padx=5)

        self.selected_file_label = tk.Label(mid_frame, text="No file selected", font=("Segoe UI", 8, "italic"), fg="gray")
        self.selected_file_label.pack(anchor="w", pady=(0, 5))

        self.result_text = tk.Text(mid_frame, height=15, font=("Consolas", 10), bg="#f8f9fa")
        self.result_text.pack(fill="both", expand=True)

        # Toolbar (Export, XYZ, FCHK)
        bottom_bar = tk.Frame(mid_frame, pady=10)
        bottom_bar.pack(fill="x")

        self.export_btn = tk.Button(bottom_bar, text=" 💾 Export Report ", command=self.generate_report, bg="#40c057", fg="white", relief="flat")
        self.export_btn.pack(side="right", padx=5)

        self.btn_xyz = tk.Button(bottom_bar, text=" 📍 Extract XYZ ", command=self.extract_last_xyz, bg="#fab005", fg="white", relief="flat")
        self.btn_xyz.pack(side="right", padx=5)

        self.btn_fchk = tk.Button(bottom_bar, text=" 💎 Gen FCHK ", command=self.generate_fchk, bg="#15aabf", fg="white", relief="flat")
        self.btn_fchk.pack(side="left")

        self.btn_scan_csv = tk.Button(bottom_bar, text=" 📊 Extract Scan CSV ", command=self.extract_scan_csv, bg="#e64980", fg="white", relief="flat")
        self.btn_scan_csv.pack(side="left", padx=5)

        # --- RIGHT: ENERGY HISTORY ---
        right_frame = tk.Frame(self.paned, padx=10)
        self.paned.add(right_frame, width=180)

        tk.Label(right_frame, text="Energy History", font=("Segoe UI", 9, "bold")).pack(pady=(0,5))
        self.hist_list = tk.Listbox(right_frame, font=("Consolas", 9), bg="#e9ecef", borderwidth=0)
        self.hist_list.pack(fill="both", expand=True)

    def refresh_log_list(self):
        for i in self.tree_logs.get_children(): self.tree_logs.delete(i)
        self._populate_logs("", self.output_path)

    def _populate_logs(self, parent_node, current_path):
        try:
            for path in sorted(current_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if path.is_dir():
                    node = self.tree_logs.insert(parent_node, "end", text=f" 📁 {path.name}", open=False, values=(str(path),))
                    self._populate_logs(node, path)
                elif path.suffix.lower() == ".log":
                    self.tree_logs.insert(parent_node, "end", text=f" 📄 {path.name}", values=(str(path),))
        except Exception: pass

    def on_log_select(self, event):
        selected = self.tree_logs.selection()
        if not selected: return
        path_str = self.tree_logs.item(selected[0])['values'][0]
        if Path(path_str).is_file():
            self._set_target_file(Path(path_str))

    def _set_target_file(self, path):
        self.current_target = path
        self.selected_file_label.config(text=f"Target: {path.name}", fg="#1971c2", font=("Segoe UI", 8, "bold"))

    def start_analysis(self):
        if self.current_target and self.current_target.exists():
            self.parse_log(self.current_target)
        else:
            messagebox.showwarning("Warning", "Please select a .log file in the list first.")

    def parse_log(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            res = [f"--- ANALYSIS REPORT: {filepath.name} ---", ""]

            # 1. Termination Status
            if "Error termination" in content:
                res.append("🚨 STATUS: ERROR TERMINATION")
                lines = content.splitlines()
                for i in range(len(lines)-1, 0, -1):
                    if "Error termination" in lines[i]:
                        res.append(f"Context: {lines[i-1].strip()}")
                        break
            elif "Normal termination" in content:
                res.append("✅ STATUS: Normal termination")
            else:
                res.append("⏳ STATUS: Job Running or Interrupted")

            # 2. Relaxed PES Scan Detection
            opt_blocks = content.split("Optimization completed.")
            is_scan = len(opt_blocks) > 2

            if is_scan:
                res.append("-" * 30)
                res.append("📈 RELAXED PES SCAN DETECTED")
                energies = []
                
                for block in opt_blocks[:-1]:
                    scf_matches = re.findall(r"SCF Done:\s+E\([^\)]+\)\s+=\s+(-?\d+\.\d+)", block)
                    if scf_matches:
                        energies.append(float(scf_matches[-1]))
                
                if energies:
                    res.append(f"Steps optimized : {len(energies)}")
                    res.append("")
                    res.append("Step | Energy (A.U.)")
                    res.append("-" * 25)
                    
                    for i, e in enumerate(energies):
                        res.append(f"{i+1:4d} | {e:13.6f}")
                        
                    self.hist_list.insert(0, f"Scan: {len(energies)} pts | {filepath.stem[:10]}")

            else:
                # Standard SCF Energies
                scf_matches = re.findall(r"SCF Done:\s+E\([^\)]+\)\s+=\s+(-?\d+\.\d+)", content)
                if scf_matches:
                    final_e = float(scf_matches[-1])
                    res.append(f"Final Energy: {final_e:.6f} A.U.")
                    self.hist_list.insert(0, f"{final_e:.6f} | {filepath.stem[:10]}")

            # 3. Calculation Time
            cpu_match = re.search(r"Job cpu time:\s+(.+)\.", content)
            elap_match = re.search(r"Elapsed time:\s+(.+)\.", content)
            if cpu_match: res.append(f"⏱️ CPU Time: {cpu_match.group(1)}")
            if elap_match: res.append(f"🕒 Real Time: {elap_match.group(1)}")

            # 4. Geometry & Frequencies
            res.append("-" * 30)
            if not is_scan and "Stationary point found" in content:
                res.append("📍 Optimization: Stationary point found.")
            
            freqs = re.findall(r"Frequencies --\s+(-?\d+\.\d+)", content)
            if freqs:
                res.append(f"📊 Lowest Freq: {freqs[0]} cm-1")
                if float(freqs[0]) < 0:
                    res.append("🚨 ALERT: Imaginary frequency (TS)!")

            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "\n".join(res))

        except Exception as e:
            messagebox.showerror("Error", f"Parsing failed: {e}")

    def generate_fchk(self):
        """Generates the .fchk file on the remote server and downloads it to the correct local folder."""
        if not self.ssh_manager or not self.ssh_manager.is_connected:
            messagebox.showwarning("SSH", "Connection required.")
            return
        if not self.current_target: return
        
        base_name = self.current_target.stem
        chk_file, fchk_file = f"{base_name}.chk", f"{base_name}.fchk"
        local_fchk = self.current_target.parent / fchk_file

        # Extract the project sub-directory for remote execution targeting
        try:
            sub_dir = self.current_target.relative_to(self.output_path).parent.as_posix()
        except ValueError:
            sub_dir = ""

        def run_remote():
            self.terminal.write_log(f"Remote: formchk {chk_file}", "command")
            success, out = self.ssh_manager.run_command_sync(f"formchk -3 {chk_file} {fchk_file}", sub_dir=sub_dir)
            if success and self.ssh_manager.download_file(fchk_file, local_fchk, sub_dir=sub_dir):
                self.terminal.write_log(f"FCHK retrieved: {fchk_file}", "success")
            else:
                self.terminal.write_log(f"Formchk error: {out}", "error")

        threading.Thread(target=run_remote, daemon=True).start()

    def extract_last_xyz(self):
        if not self.current_target: return
        try:
            with open(self.current_target, 'r') as f:
                lines = f.readlines()
            start_idx = -1
            for i in range(len(lines)-1, 0, -1):
                if "Standard orientation:" in lines[i]:
                    start_idx = i + 5
                    break
            if start_idx != -1:
                atoms = []
                for line in lines[start_idx:]:
                    if "---" in line: break
                    p = line.split()
                    if len(p) > 5: atoms.append(f"{p[1]}  {p[3]} {p[4]} {p[5]}")
                xyz_path = self.current_target.parent / f"{self.current_target.stem}_final.xyz"
                with open(xyz_path, 'w') as f_out:
                    f_out.write(f"{len(atoms)}\nExtracted from {self.current_target.name}\n" + "\n".join(atoms))
                messagebox.showinfo("Success", f"XYZ saved: {xyz_path.name}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def generate_report(self):
        if not self.current_target: return
        report_path = self.current_target.parent / f"Report_{self.current_target.stem}.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self.result_text.get("1.0", tk.END))
        messagebox.showinfo("Export", f"Report saved: {report_path.name}")
    
    def extract_scan_csv(self):
        """Parses a relaxed PES scan log file to extract geometry coordinates and calculate bond distances, exporting the results to a CSV report."""
        if not self.current_target:
            messagebox.showwarning("Warning", "No target file selected.")
            return
            
        try:
            with open(self.current_target, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 1. Identify scanned atoms (ModRedundant B ... S)
            modred_match = re.search(r'B\s+(\d+)\s+(\d+)\s+S', content)
            if not modred_match:
                messagebox.showinfo("Info", "No bond scan command (B ... S) found in log.")
                return
            
            atom1_idx = int(modred_match.group(1))
            atom2_idx = int(modred_match.group(2))

            # 2. Split log by optimization steps
            steps = re.split(r'Optimization completed\.|Stationary point found\.', content)
            results = []
            
            for step in steps[:-1]: 
                energies = re.findall(r'SCF Done:\s+E\([^\)]+\)\s+=\s+([-+0-9.]+)', step)
                if not energies:
                    continue
                
                opt_energy = energies[-1]
                
                orientations = step.split('Standard orientation:')
                if len(orientations) == 1:
                    orientations = step.split('Input orientation:')
                
                if len(orientations) > 1:
                    lines = orientations[-1].splitlines()
                    coords_a1, coords_a2 = None, None
                    
                    for line in lines[5:]:
                        if '---------------------------------------------------------------------' in line:
                            break
                        
                        parts = line.split()
                        if len(parts) >= 6:
                            idx = int(parts[0])
                            if idx == atom1_idx:
                                coords_a1 = (float(parts[3]), float(parts[4]), float(parts[5]))
                            elif idx == atom2_idx:
                                coords_a2 = (float(parts[3]), float(parts[4]), float(parts[5]))
                                
                    if coords_a1 and coords_a2:
                        results.append({
                            'Energy': opt_energy,
                            'A1': coords_a1,
                            'A2': coords_a2
                        })

            if not results:
                messagebox.showinfo("Info", "Could not extract coordinates for specified atoms.")
                return

            # 3. Write output to CSV
            csv_path = self.current_target.parent / f"{self.current_target.stem}_scan.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as f_out:
                writer = csv.writer(f_out)
                writer.writerow(['Step', 'Energy_au', 
                                 f'A{atom1_idx}_X', f'A{atom1_idx}_Y', f'A{atom1_idx}_Z',
                                 f'A{atom2_idx}_X', f'A{atom2_idx}_Y', f'A{atom2_idx}_Z',
                                 'Distance_A'])
                
                for i, res in enumerate(results):
                    a1, a2 = res['A1'], res['A2']
                    dist = math.sqrt((a1[0] - a2[0])**2 + (a1[1] - a2[1])**2 + (a1[2] - a2[2])**2)
                    
                    writer.writerow([i+1, res['Energy'], 
                                     a1[0], a1[1], a1[2],
                                     a2[0], a2[1], a2[2],
                                     f"{dist:.4f}"])
                                     
            messagebox.showinfo("Success", f"Scan CSV saved:\n{csv_path.name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Extraction failed: {e}")

    def open_selected_log_file(self):
        """Open .log file selected with the default text editor of the system."""
        selected = self.tree_logs.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a log file from the list first.")
            return
        file_path = self.tree_logs.item(selected[0])['values'][0]
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "The system could not find the specified file.")
            return
        try:
            current_os = platform.system()
            if current_os == "Windows":
                os.startfile(file_path)
            elif current_os == "Darwin":  # macOS
                os.system(f"open '{file_path}'")
            else:
                os.system(f"xdg-open '{file_path}'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the file: {str(e)}")