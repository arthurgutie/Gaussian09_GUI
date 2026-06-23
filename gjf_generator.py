import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        border_frame = tk.Frame(tw, background="#dee2e6")
        border_frame.pack(fill="both", expand=True)
        
        label = tk.Label(border_frame, text=self.text, justify='left',
                         background="#ffffff", foreground="#212529",
                         font=("Segoe UI", 9, "normal"))
        label.pack(padx=1, pady=1, ipadx=8, ipady=5)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class OptionsDialog(tk.Toplevel):
    def __init__(self, parent, mode, current_options):
        super().__init__(parent)
        self.title(f"{mode} Options")
        self.geometry("320x450")
        self.result = current_options
        self.vars = {}

        options_map = {
            "Opt": ["ReadFreeze", "ModRedundant", "TS", "Saddle=1", "Loose", "Tight", "VeryTight"],
            "Freq": ["ReadFC", "VibRot", "Anharmonic", "Raman", "NNHuckel", "SaveNM"]
        }
        
        ttk.Label(self, text=f"Select {mode} Options:", font=('Arial', 10, 'bold')).pack(pady=10)
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20)
        
        current_list = current_options.split(",") if current_options else []
        for opt in options_map.get(mode, []):
            var = tk.BooleanVar(value=opt in current_list)
            self.vars[opt] = var
            ttk.Checkbutton(container, text=opt, variable=var).pack(anchor="w", pady=2)

        if mode == "Opt":
            ttk.Separator(container, orient="horizontal").pack(fill="x", pady=15)
            
            f_step = ttk.Frame(container)
            f_step.pack(fill="x", pady=2)
            ttk.Label(f_step, text="MaxStep (int):").pack(side="left")
            self.maxstep_val = tk.StringVar(value="30")
            for o in current_list:
                if "MaxStep=" in o: self.maxstep_val.set(o.split('=')[1])
            ttk.Entry(f_step, textvariable=self.maxstep_val, width=8).pack(side="right")
            
            f_cyc = ttk.Frame(container)
            f_cyc.pack(fill="x", pady=2)
            ttk.Label(f_cyc, text="MaxCycles (int):").pack(side="left")
            self.maxcycles_val = tk.StringVar()
            for o in current_list:
                if "MaxCycles=" in o: self.maxcycles_val.set(o.split('=')[1])
            ttk.Entry(f_cyc, textvariable=self.maxcycles_val, width=8).pack(side="right")

        ttk.Button(self, text="Apply", command=self.save_and_close).pack(pady=15)
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def save_and_close(self):
        selected = [opt for opt, var in self.vars.items() if var.get()]
        if hasattr(self, 'maxstep_val') and self.maxstep_val.get():
            selected.append(f"MaxStep={self.maxstep_val.get()}")
        if hasattr(self, 'maxcycles_val') and self.maxcycles_val.get():
            selected.append(f"MaxCycles={self.maxcycles_val.get()}")

        self.result = ",".join(selected)
        self.destroy()


class ScanBuilderDialog(tk.Toplevel):
    def __init__(self, parent, current_val):
        super().__init__(parent)
        self.title("Relaxed Scan Setup")
        self.geometry("320x250")
        self.result = current_val
        
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)
        
        self.atom1 = tk.StringVar()
        self.atom2 = tk.StringVar()
        self.steps = tk.StringVar()
        self.step_size = tk.StringVar()
        
        self._parse_current(current_val)
        self._build_ui()
        
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        self.wait_window()

    def _parse_current(self, val):
        if val and val.startswith("B "):
            parts = val.split()
            if len(parts) >= 6:
                self.atom1.set(parts[1])
                self.atom2.set(parts[2])
                self.steps.set(parts[4])
                self.step_size.set(parts[5])

    def _build_ui(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Bond to scan:", font=("Arial", 9, "bold")).pack(anchor="w")
        
        f_atoms = ttk.Frame(container)
        f_atoms.pack(fill="x", pady=5)
        ttk.Label(f_atoms, text="Atom 1:").pack(side="left")
        ttk.Entry(f_atoms, textvariable=self.atom1, width=5).pack(side="left", padx=5)
        ttk.Label(f_atoms, text="Atom 2:").pack(side="left")
        ttk.Entry(f_atoms, textvariable=self.atom2, width=5).pack(side="left", padx=5)
        
        lbl_help_atoms = ttk.Label(f_atoms, text=" [?]", foreground="blue", cursor="hand2")
        lbl_help_atoms.pack(side="left")
        ToolTip(lbl_help_atoms, "Indices of the two atoms defining the bond to scan,\nexactly as numbered in the XYZ coordinates list.")

        ttk.Label(container, text="Scan parameters:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(10, 0))
        
        f_params = ttk.Frame(container)
        f_params.pack(fill="x", pady=5)
        
        ttk.Label(f_params, text="Steps:").pack(side="left")
        ttk.Entry(f_params, textvariable=self.steps, width=5).pack(side="left", padx=5)
        
        lbl_help_steps = ttk.Label(f_params, text="[?] ", foreground="blue", cursor="hand2")
        lbl_help_steps.pack(side="left", padx=(0, 5))
        ToolTip(lbl_help_steps, "Number of scanning steps after the initial geometry.\nFor example, 10 steps will result in a total of 11 calculated points on the energy curve.")
        
        ttk.Label(f_params, text="Step Size (Å):").pack(side="left")
        ttk.Entry(f_params, textvariable=self.step_size, width=6).pack(side="left", padx=5)
        
        lbl_help_size = ttk.Label(f_params, text="[?]", foreground="blue", cursor="hand2")
        lbl_help_size.pack(side="left")
        ToolTip(lbl_help_size, "Distance variation per step in Ångströms.\nUse a positive value to stretch the bond,\nor a NEGATIVE value (e.g., -0.1) to push the atoms together.")

        btn_f = ttk.Frame(container)
        btn_f.pack(fill="x", side="bottom", pady=10)
        ttk.Button(btn_f, text="✔ Apply", command=self.confirm).pack(side="right", padx=5)
        ttk.Button(btn_f, text="✖ Clear", command=self.clear).pack(side="right")

    def close_dialog(self):
        self.grab_release()
        self.destroy()

    def confirm(self):
        a1, a2 = self.atom1.get(), self.atom2.get()
        st, sz = self.steps.get(), self.step_size.get()
        if a1 and a2 and st and sz:
            self.result = f"B {a1} {a2} S {st} {sz}"
        self.close_dialog()

    def clear(self):
        self.result = ""
        self.close_dialog()


class BasisBuilderDialog(tk.Toplevel):
    def __init__(self, parent, family, current_val):
        super().__init__(parent)
        self.title(f"{family} Basis Builder")
        self.geometry("480x600")
        self.family = family
        self.result = None
        
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)
        
        if family == "Pople":
            self.v_core, self.v_val, self.v_diff, self.v_pol = parent.p_core, parent.p_val, parent.p_diff, parent.p_pol
        elif family == "Ahlrichs":
            self.v_ahl_zeta, self.v_ahl_pol, self.v_ahl_diff = parent.a_zeta, parent.a_pol, parent.a_diff
        elif family == "Dunning":
            self.v_d_zeta, self.v_d_aug = parent.d_zeta, parent.d_aug
        self.final_name = tk.StringVar(value=current_val)
        self._build_ui()
        self.update_name()
        
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        self.update_idletasks()
        self.wait_window()

    def _build_ui(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        if self.family == "Pople":
            l_core = ttk.Label(container, text="Core Gaussians (e.g. 6 in 6-31G):", font=("Arial", 9, "bold"))
            l_core.pack(anchor="w")
            ToolTip(l_core, "Standard is 6. Higher means better description of core electrons (O(N^3) cost).")
            
            f_core = ttk.Frame(container); f_core.pack(fill="x", pady=5)
            for v in ["3", "4", "5", "6"]:
                ttk.Radiobutton(f_core, text=v, variable=self.v_core, value=v, command=self.update_name).pack(side="left", padx=5)

            l_val = ttk.Label(container, text="Valence Split (Zeta):", font=("Arial", 9, "bold"))
            l_val.pack(anchor="w", pady=(10,0))
            ToolTip(l_val, "31G (Double Zeta) or 311G (Triple Zeta). More functions allow for better bond flexibility.")
            
            f_val = ttk.Frame(container); f_val.pack(fill="x", pady=5)
            for v in ["21G", "31G", "311G"]:
                ttk.Radiobutton(f_val, text=v, variable=self.v_val, value=v, command=self.update_name).pack(side="left", padx=5)

            l_diff = ttk.Label(container, text="Diffuse Functions (+):", font=("Arial", 9, "bold"))
            l_diff.pack(anchor="w", pady=(10,0))
            ToolTip(l_diff, "Mandatory for Anions and Excited States. Allows electrons to roam far from nuclei.")
            
            f_dif = ttk.Frame(container); f_dif.pack(fill="x", pady=5)
            for txt, val in [("None", ""), ("+", "+"), ("++", "++")]:
                ttk.Radiobutton(f_dif, text=txt, variable=self.v_diff, value=val, command=self.update_name).pack(side="left", padx=5)

            l_pol = ttk.Label(container, text="Polarization (d, p):", font=("Arial", 9, "bold"))
            l_pol.pack(anchor="w", pady=(10,0))
            ToolTip(l_pol, "Adds angular flexibility. Essential for geometry optimization and accurate angles.")
            
            self.cb_pol = ttk.Combobox(container, textvariable=self.v_pol, values=["", "(d)", "(d,p)", "(2d,p)", "(2df,2pd)"])
            self.cb_pol.pack(fill="x", pady=5)
            self.cb_pol.bind("<<ComboboxSelected>>", lambda e: self.update_name())

        elif self.family == "Ahlrichs":
            l_zeta = ttk.Label(container, text="Valence Zeta:", font=("Arial", 9, "bold"))
            l_zeta.pack(anchor="w")
            ToolTip(l_zeta, "Defines the radial flexibility (SV/TZV/QZV).\nTZV is the standard for high-quality DFT research.")
            f_z = ttk.Frame(container); f_z.pack(fill="x", pady=5)
            for v in ["SV", "TZV", "QZV"]:
                ttk.Radiobutton(f_z, text=v, variable=self.v_ahl_zeta, value=v, command=self.update_name).pack(side="left", padx=5)

            l_p = ttk.Label(container, text="Polarization:", font=("Arial", 9, "bold"))
            l_p.pack(anchor="w", pady=(10,0))
            ToolTip(l_p, "Adds orbital flexibility (P/PP).\nPP is essential for correlation methods like MP2 or CCSD.")
            f_p = ttk.Frame(container); f_p.pack(fill="x", pady=5)
            for v in ["", "P", "PP"]:
                ttk.Radiobutton(f_p, text=v if v else "None", variable=self.v_ahl_pol, value=v, command=self.update_name).pack(side="left", padx=5)

            c_diff = ttk.Checkbutton(container, text="Diffuse (D)", variable=self.v_ahl_diff, command=self.update_name)
            c_diff.pack(anchor="w", pady=10)
            ToolTip(c_diff, "CANNOT BE USED LIKED THIS : Must get the basis set and copy paste it in the .gjf file, and input <method>/GEN at the level of theory spot. Adds large-radius functions.\nCrucial for Anions (-), Excited States, and weak interactions.")

        elif self.family == "Minimal":
            l_min = ttk.Label(container, text="Select Minimal Basis:", font=("Arial", 9, "bold"))
            l_min.pack(anchor="w")
            for b in ["STO-3G", "3-21G"]:
                ttk.Radiobutton(container, text=b, variable=self.final_name, value=b).pack(anchor="w", pady=5)

        elif self.family == "Dunning":
            l_aug = ttk.Label(container, text="Augmentation:", font=("Arial", 9, "bold"))
            l_aug.pack(anchor="w")
            ttk.Checkbutton(container, text="Add 'aug-' prefix (Diffuse)", variable=self.v_d_aug, command=self.update_name).pack(anchor="w", pady=5)
            ToolTip(l_aug, "Adds diffuse functions to all atoms. Mandatory for anions and van der Waals.")

            l_zeta = ttk.Label(container, text="Valence Zeta:", font=("Arial", 9, "bold"))
            l_zeta.pack(anchor="w", pady=(10,0))
            f_z = ttk.Frame(container); f_z.pack(fill="x", pady=5)
            for v in ["pVDZ", "pVTZ", "pVQZ", "pV5Z"]:
                ttk.Radiobutton(f_z, text=v, variable=self.v_d_zeta, value=v, command=self.update_name).pack(side="left", padx=5)

        res_frame = ttk.LabelFrame(container, text=" Selected Basis Set ", padding=10)
        res_frame.pack(fill="x", pady=20)
        ttk.Label(res_frame, textvariable=self.final_name, font=("Consolas", 12, "bold"), foreground="#1971c2").pack()

        btn_f = ttk.Frame(container)
        btn_f.pack(fill="x", side="bottom", pady=10)
        ttk.Button(btn_f, text="✔ Use this basis", command=self.confirm).pack(side="right", padx=5)
        ttk.Button(btn_f, text="✖ Cancel", command=self.close_dialog).pack(side="right")

    def update_name(self):
        if self.family == "Pople":
            name = f"{self.v_core.get()}-{self.v_val.get()}"
            if self.v_diff.get(): name = name.replace("G", f"{self.v_diff.get()}G")
            name += self.v_pol.get()
            self.final_name.set(name)
        elif self.family == "Ahlrichs":
            name = f"def2-{self.v_ahl_zeta.get()}"
            if self.v_ahl_pol.get(): name += self.v_ahl_pol.get()
            if self.v_ahl_diff.get(): name += "D"
            self.final_name.set(name)
        elif self.family == "Dunning":
            prefix = "aug-cc-" if self.v_d_aug.get() else "cc-"
            self.final_name.set(f"{prefix}{self.v_d_zeta.get()}")

    def close_dialog(self): 
        self.grab_release()
        self.destroy()

    def confirm(self): 
        self.result = self.final_name.get()
        self.close_dialog()


class GJFGenerator(tk.LabelFrame):
    def __init__(self, parent, ssh_manager=None, config=None):
        super().__init__(parent, text=" 1. GJF Input Generator ", padx=15, pady=15, bg="#e9f1f7")
        self.ssh_manager = ssh_manager
        config = config or {}
        
        self.source_var = tk.StringVar(value=config.get("source_var", "XYZ"))
        self.project_name = tk.StringVar(value=config.get("project_name", "Project"))
        self.mol_name = tk.StringVar(value=config.get("mol_name", "Molecule1"))
        self.nproc = tk.IntVar(value=config.get("nproc", 8))
        self.mem = tk.StringVar(value=config.get("mem", "16"))
        self.chk_path = tk.StringVar(value=config.get("chk_path", "No CHK selected"))
        self.theory = tk.StringVar(value=config.get("theory", "B3LYP"))
        self.basis_set_name = tk.StringVar(value=config.get("basis", "6-31G(d)"))
        self.kw_sp = tk.BooleanVar(value=config.get("kw_sp", False))
        self.kw_opt = tk.BooleanVar(value=config.get("kw_opt", True))
        self.kw_freq = tk.BooleanVar(value=config.get("kw_freq", False))
        self.kw_calcfc = tk.BooleanVar(value=config.get("kw_calcfc", False))
        self.scf_opt = tk.StringVar(value=config.get("scf_opt", ""))
        self.guess_opt = tk.StringVar(value=config.get("guess_opt", ""))
        self.extra_keywords = tk.StringVar(value=config.get("extra_keywords", ""))
        self.charge = tk.StringVar(value=config.get("charge", "0"))
        self.mult = tk.StringVar(value=config.get("mult", "1"))
        self.opt_details = config.get("opt_details", "")
        self.freq_details = config.get("freq_details", "")
        self.scan_details = tk.StringVar(value=config.get("scan_details", ""))
        
        self.p_core = tk.StringVar(value=config.get("p_core", "6"))
        self.p_val = tk.StringVar(value=config.get("p_val", "31G"))
        self.p_diff = tk.StringVar(value=config.get("p_diff", ""))
        self.p_pol = tk.StringVar(value=config.get("p_pol", "(d)"))
        
        self.a_zeta = tk.StringVar(value=config.get("a_zeta", "TZV"))
        self.a_pol = tk.StringVar(value=config.get("a_pol", "P"))
        self.a_diff = tk.BooleanVar(value=config.get("a_diff", False))
        
        self.d_zeta = tk.StringVar(value=config.get("d_zeta", "pVTZ"))
        self.d_aug = tk.BooleanVar(value=config.get("d_aug", False))
        self.route_preview = tk.StringVar()
        
        self.output_path = Path.cwd() / "Output"
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.setup_ui()
        self.theory.trace_add("write", self._check_theory_needs)
        self.theory.trace_add("write", self._update_route_preview)
        self.basis_set_name.trace_add("write", self._update_route_preview)

        self._update_route_preview()

    def _check_theory_needs(self, *args):
        if self.theory.get() == "PM6":
            self.basis_set_name.set("")
        elif not self.basis_set_name.get():
            self.basis_set_name.set("6-31G(d)")
        self._update_route_preview()

    def _update_route_preview(self, *args):
        theory = self.theory.get()
        basis = self.basis_set_name.get()
        if theory == "PM6":
            self.route_preview.set(f"Active Method: PM6")
        else:
            self.route_preview.set(f"Active Method: {theory}/{basis}")

    def setup_ui(self):
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=5)

        top = ttk.LabelFrame(main, text=" 1. Project & Molecule Management ")
        top.pack(fill="x", pady=5)
        ttk.Label(top, text="Project:").grid(row=0, column=0, padx=5)
        self.cb_project = ttk.Combobox(top, textvariable=self.project_name, values=self._get_dirs(self.output_path))
        self.cb_project.grid(row=0, column=1, padx=5)
        ttk.Label(top, text="Molecule:").grid(row=0, column=2, padx=5)
        self.cb_mol = ttk.Combobox(top, textvariable=self.mol_name)
        self.cb_mol.grid(row=0, column=3, padx=5)

        self.project_name.trace_add("write", self.update_molecule_list)
        self.update_molecule_list()

        mid = ttk.LabelFrame(main, text=" 2. Geometry Details ")
        mid.pack(fill="both", expand=True, pady=5)
        l_geom = ttk.Frame(mid)
        l_geom.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Radiobutton(l_geom, text="XYZ Data", variable=self.source_var, value="XYZ", command=self.sync_geom_state).pack(anchor="w")
        
        px = ttk.Frame(l_geom)
        px.pack(fill="x")
        ttk.Label(px, text="C:").pack(side="left")
        ttk.Entry(px, textvariable=self.charge, width=3).pack(side="left", padx=2)
        ttk.Label(px, text="M:").pack(side="left")
        ttk.Entry(px, textvariable=self.mult, width=3).pack(side="left", padx=2)
        
        ttk.Button(px, text="Load .xyz", command=self.load_xyz_file, width=10).pack(side="right")
        self.cb_calcfc = ttk.Checkbutton(px, text="CalcFC", variable=self.kw_calcfc)
        self.cb_calcfc.pack(side="right", padx=10)
        ToolTip(self.cb_calcfc, "Calculate Force Constants at first step.\nRecommended for Transition States.")
        
        self.txt_geometry = tk.Text(l_geom, height=10, width=30, font=("Courier", 9))
        self.txt_geometry.pack(fill="both", expand=True)

        r_geom = ttk.Frame(mid)
        r_geom.pack(side="right", fill="both", expand=True, padx=5)
        ttk.Radiobutton(r_geom, text="Restart (CHK)", variable=self.source_var, value="CHK", command=self.sync_geom_state).pack(anchor="w")
        ttk.Button(r_geom, text="Select .chk", command=self.select_chk).pack(fill="x", pady=2)
        ttk.Label(r_geom, textvariable=self.chk_path, wraplength=150, foreground="blue").pack()

        bot = ttk.LabelFrame(main, text=" 3. Method, Keywords & Resources ")
        bot.pack(fill="x", pady=5)
        
        r1 = ttk.Frame(bot)
        r1.pack(fill="x", pady=2)
        
        methods = {
            "PM6": "Semi-Empirical - Very Fast (Pre-opt)",
            "RHF": "Restricted HF - Baseline O(N³)", 
            "UHF": "Unrestricted HF - Open-shell O(N³)",
            "B3LYP": "DFT Hybrid - Standard O(N³)", 
            "PBE0": "DFT Hybrid - Robust O(N³)", 
            "wB97XD": "DFT-Dispersion - Recommended O(N³)",
            "MP2": "Post-HF (Perturbation) - O(N⁵)", 
            "CCSD": "Post-HF (Coupled Cluster) - O(N⁶)", 
            "CCSD(T)": "Post-HF (Gold Standard) - O(N⁷)"
        }
        
        ttk.Label(r1, text="Theory:").pack(side="left", padx=5)
        self.cb_theory = ttk.Combobox(r1, textvariable=self.theory, values=list(methods.keys()), width=10)
        self.cb_theory.pack(side="left")
        h_m = ttk.Label(r1, text=" [?]", foreground="blue", cursor="hand2")
        h_m.pack(side="left")
        ToolTip(h_m, "\n".join([f"{k}: {v}" for k,v in methods.items()]))

        basis_frame = ttk.Frame(r1)
        basis_frame.pack(side="left", padx=(15, 5))
        
        ttk.Label(basis_frame, text="Basis Family:").pack(side="left")
        
        for family in ["Minimal", "Pople", "Ahlrichs", "Dunning"]:
            btn = ttk.Button(basis_frame, text=family, width=8, 
                             command=lambda f=family: self.open_basis_builder(f))
            btn.pack(side="left", padx=2)

        help_b = ttk.Label(r1, text=" [?]", foreground="blue", cursor="hand2")
        help_b.pack(side="left")
        
        basis_info = (
            "Categories & Usage:\n"
            "- Minimal: STO-3G, 3-21G (Very fast, low accuracy, for pre-optimization)\n"
            "- Pople: 6-31G, 6-311G etc. (Standard for Organic/Small molecules)\n"
            "- Dunning: cc-pVDZ, cc-pVTZ (Correlation consistent, high precision)\n"
            "- Aug- (Prefix): Adds diffuse functions (Critical for anions and excited states)\n"
            "- Ahlrichs: Def2SVP, Def2TZVP (Modern, balanced, excellent for DFT)"
        )
        ToolTip(help_b, basis_info)
        
        ttk.Label(r1, text="nProc:").pack(side="left", padx=(15, 2))
        ttk.Entry(r1, textvariable=self.nproc, width=3).pack(side="left")
        tk.Scale(r1, from_=1, to=24, orient="horizontal", variable=self.nproc, showvalue=False, length=80).pack(side="left", padx=5)

        ttk.Label(r1, text="Mem (GB):").pack(side="left", padx=(10, 2))
        ttk.Entry(r1, textvariable=self.mem, width=4).pack(side="left")

        r2 = ttk.Frame(bot)
        r2.pack(fill="x", pady=5)
        ttk.Checkbutton(r2, text="SP", variable=self.kw_sp, command=self.logic_sp).pack(side="left", padx=5)
        ttk.Checkbutton(r2, text="Opt", variable=self.kw_opt, command=self.logic_keywords).pack(side="left")
        ttk.Button(r2, text="+", width=2, command=lambda: self.open_options_menu("Opt")).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r2, text="Freq", variable=self.kw_freq, command=self.logic_keywords).pack(side="left")
        ttk.Button(r2, text="+", width=2, command=lambda: self.open_options_menu("Freq")).pack(side="left", padx=(0, 10))
        
        self.btn_scan = ttk.Button(r2, text="📐 Scan", command=self.open_scan_menu)
        self.btn_scan.pack(side="left", padx=(5, 10))
        ToolTip(self.btn_scan, "Configure a Relaxed PES Scan (ModRedundant).\nVaries a specific bond step-by-step to generate an energy profile.")
        
        ttk.Label(r2, text="SCF:").pack(side="left", padx=(10, 0))
        self.cb_scf = ttk.Combobox(r2, textvariable=self.scf_opt, values=["", "Tight", "XQC", "QC"], width=7)
        self.cb_scf.pack(side="left", padx=2)
        lbl_help_scf = ttk.Label(r2, text="[?]", foreground="blue", cursor="hand2")
        lbl_help_scf.pack(side="left", padx=(0, 5))
        ToolTip(lbl_help_scf, "Default: Standard convergence.\nTight: Stricter convergence criteria.\nXQC: Finds convergence with DIIS first, switches to QC if it fails.\nQC: Quadratic Convergence, very robust but slow.")
        
        ttk.Label(r2, text="Guess:").pack(side="left")
        self.cb_guess = ttk.Combobox(r2, textvariable=self.guess_opt, values=["", "Read", "Mix"], width=7)
        self.cb_guess.pack(side="left", padx=2)
        
        lbl_help_guess = ttk.Label(r2, text="[?]", foreground="blue", cursor="hand2")
        lbl_help_guess.pack(side="left", padx=(0, 5))
        ToolTip(lbl_help_guess, "Mix: Breaks spatial symmetry (crucial for open-shell singlets/diradicals).\nRead: Uses orbitals from a previous checkpoint file.")

        r3 = ttk.Frame(bot)
        r3.pack(fill="x", pady=2)
        ttk.Label(r3, text="Extra:").pack(side="left", padx=5)
        ttk.Entry(r3, textvariable=self.extra_keywords).pack(side="left", fill="x", expand=True, padx=5)

        r_gen = ttk.Frame(bot)
        r_gen.pack(fill="x", side="bottom", pady=10)
        ttk.Button(r_gen, text="GENERATE .GJF", command=self.generate_gjf).pack(side="right", padx=5)
        self.lbl_full_route = tk.Label(r_gen, textvariable=self.route_preview, font=("Consolas", 10, "bold"), fg="#1971c2", bg="#e7f5ff", padx=12, pady=4, relief="flat")
        self.lbl_full_route.pack(side="right", padx=10)

    def open_options_menu(self, mode):
        current = self.opt_details if mode == "Opt" else self.freq_details
        dialog = OptionsDialog(self, mode, current)
        if mode == "Opt": self.opt_details = dialog.result
        else: self.freq_details = dialog.result
    
    def open_scan_menu(self):
        dialog = ScanBuilderDialog(self, self.scan_details.get())
        self.scan_details.set(dialog.result)
        if self.scan_details.get():
            self.kw_opt.set(True)
            self.kw_sp.set(False)

    def open_basis_builder(self, family):
        dialog = BasisBuilderDialog(self, family, self.basis_set_name.get())
        if dialog.result:
            self.basis_set_name.set(dialog.result)

    def logic_keywords(self):
        if self.kw_opt.get() or self.kw_freq.get(): self.kw_sp.set(False)
        if not any([self.kw_opt.get(), self.kw_freq.get()]): self.kw_sp.set(True)

    def logic_sp(self):
        if self.kw_sp.get():
            self.kw_opt.set(False)
            self.kw_freq.set(False)
        else: self.kw_opt.set(True)

    def load_xyz_file(self):
        path = filedialog.askopenfilename(filetypes=[("XYZ Files", "*.xyz")])
        if path:
            with open(path, 'r') as f:
                lines = f.readlines()
                self.txt_geometry.delete("1.0", tk.END)
                self.txt_geometry.insert("1.0", "".join(lines[2:]).strip())
            self.source_var.set("XYZ")
            self.sync_geom_state()

    def generate_gjf(self):
        target_dir = self.output_path / self.project_name.get() / self.mol_name.get()
        target_dir.mkdir(parents=True, exist_ok=True)
        
        prefix = "init_" if self.source_var.get() == "XYZ" else ""
        current_basis = self.basis_set_name.get()
        c_basis = current_basis.replace("*","d").replace("(","").replace(")","").replace("+","p").replace(",", "")
        base_n = f"{prefix}{self.mol_name.get()}_{self.theory.get()}_{c_basis}"
        
        counter = 1
        f_path = target_dir / f"{base_n}.gjf"
        while f_path.exists():
            f_path = target_dir / f"{base_n}_{counter}.gjf"
            counter += 1
        
        kws = []
        if self.kw_sp.get(): kws.append("SP")
        
        if self.kw_opt.get():
            o_details = self.opt_details
            
            if self.source_var.get() == "CHK":
                if "ReadFC" not in o_details:
                    o_details = "ReadFC," + o_details if o_details else "ReadFC"
            elif self.source_var.get() == "XYZ" and self.kw_calcfc.get():
                if "CalcFC" not in o_details:
                    o_details = "CalcFC," + o_details if o_details else "CalcFC"
                    
            if self.scan_details.get() and "ModRedundant" not in o_details:
                o_details = o_details + ",ModRedundant" if o_details else "ModRedundant"
                
            o_str = f"=({o_details})" if "," in o_details else (f"={o_details}" if o_details else "")
            kws.append(f"Opt{o_str}")
            
        if self.kw_freq.get():
            fr_str = f"=({self.freq_details})" if "," in self.freq_details else (f"={self.freq_details}" if self.freq_details else "")
            kws.append(f"Freq{fr_str}")
        
        theory = self.theory.get()
        if theory == "PM6":
            route = f"# {theory} {' '.join(kws)}"
        else:
            route = f"# {theory}/{current_basis} {' '.join(kws)}"

        if self.scf_opt.get(): route += f" SCF={self.scf_opt.get()}"
        if self.extra_keywords.get(): route += f" {self.extra_keywords.get()}"

        lines = [f"%mem={self.mem.get()}GB", f"%nprocshared={self.nproc.get()}", f"%chk={f_path.stem}.chk"]

        ui_guess = self.guess_opt.get()

        if self.source_var.get() == "CHK":
            lines.insert(2, f"%oldchk={self.chk_path.get()}")
            if ui_guess == "Mix":
                route += " Geom=AllCheck Guess=(Read,Mix)"
            else:
                route += " Geom=AllCheck Guess=Read"
            lines.extend([route, "", "Job started from chk file", "", ""])
            
        else:
            if ui_guess: 
                route += f" Guess={ui_guess}"
            lines.extend([route, "", f"Job: {f_path.name}", "", f"{self.charge.get()} {self.mult.get()}"])
            lines.append(self.txt_geometry.get("1.0", tk.END).strip())
            lines.append("")
            
            if self.scan_details.get():
                lines.append(self.scan_details.get())
                lines.append("")
                
            lines.append("")
            
        with open(f_path, "w") as f: f.write("\n".join(lines))
        messagebox.showinfo("Success", f"Generated: {f_path.name}")

    def _get_dirs(self, path):
        if path.exists() and path.is_dir():
            return sorted([d.name for d in path.iterdir() if d.is_dir()])
        return []

    def update_molecule_list(self, *args):
        project_path = self.output_path / self.project_name.get()
        mols = self._get_dirs(project_path)
        self.cb_mol.config(values=mols)
        if not mols:
            self.cb_mol.set("")

    def select_chk(self):
        path = filedialog.askopenfilename(filetypes=[("Checkpoint Files", "*.chk")])
        if path:
            self.chk_path.set(os.path.basename(path))
            self.source_var.set("CHK")
            self.sync_geom_state()

    def sync_geom_state(self):
        state = "normal" if self.source_var.get() == "XYZ" else "disabled"
        self.txt_geometry.configure(state=state, bg="white" if state=="normal" else "#f0f0f0")
        
        if self.source_var.get() == "CHK":
            self.cb_calcfc.state(['disabled'])
        else:
            self.cb_calcfc.state(['!disabled'])

    def get_state(self):
        return {
            "source_var": self.source_var.get(),
            "project_name": self.project_name.get(),
            "mol_name": self.mol_name.get(),
            "nproc": self.nproc.get(),
            "mem": self.mem.get(),
            "chk_path": self.chk_path.get(),
            "theory": self.theory.get(),
            "basis": self.basis_set_name.get(),
            "kw_sp": self.kw_sp.get(),
            "kw_opt": self.kw_opt.get(),
            "kw_freq": self.kw_freq.get(),
            "kw_calcfc": self.kw_calcfc.get(),
            "scf_opt": self.scf_opt.get(),
            "guess_opt": self.guess_opt.get(),
            "extra_keywords": self.extra_keywords.get(),
            "charge": self.charge.get(),
            "mult": self.mult.get(),
            "opt_details": self.opt_details,
            "freq_details": self.freq_details,
            "scan_details": self.scan_details.get(),
            "p_core": self.p_core.get(),
            "p_val": self.p_val.get(),
            "p_diff": self.p_diff.get(),
            "p_pol": self.p_pol.get(),
            "a_zeta": self.a_zeta.get(),
            "a_pol": self.a_pol.get(),
            "a_diff": self.a_diff.get(),
            "d_zeta": self.d_zeta.get(),
            "d_aug": self.d_aug.get()
        }