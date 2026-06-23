import tkinter as tk
from tkinter import ttk
import os
import sys
import json
from pathlib import Path

# Importation des modules locaux mis à jour
from ssh_manager import SSHManager
from terminal_module import TerminalModule
from gjf_generator import GJFGenerator
from executor import ExecutorModule
from log_parser import AnalyzerModule

class GaussianGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GaussianGUI - Research Dashboard")
        self.state('zoomed')
        self.configure(bg="#f0f2f5")

        self.ssh_manager = SSHManager()
        
        # Cache management (settings persistence)
        os.makedirs("config", exist_ok=True)
        self.cache_file = "config/app_cache.json"
        self.app_cache = self.load_cache()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._init_modules()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {}

    def on_closing(self):
        """Save state before closing"""
        try:
            self.app_cache['terminal'] = self.terminal.get_state()
            self.app_cache['generator'] = self.generator.get_state()
            self.app_cache['executor'] = self.executor.get_state()
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_cache, f, indent=4)
        except Exception as e:
            print(f"DEBUG: Error saving cache: {e}")
        finally:
            if hasattr(self, 'executor'):
                self.executor.is_running = False
            self.destroy()

    def _init_modules(self):
        # Generation module (Top Left)
        self.generator = GJFGenerator(self, self.ssh_manager, config=self.app_cache.get('generator', {}))
        self.generator.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Terminal module (Bottom Right)
        self.terminal = TerminalModule(self, self.ssh_manager, config=self.app_cache.get('terminal', {}))
        self.terminal.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # Execution module (Top Right)
        self.executor_frame = tk.Frame(self)
        self.executor_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.executor = ExecutorModule(self.executor_frame, self.ssh_manager, self.terminal, config=self.app_cache.get('executor', {}))
        self.executor.pack(fill="both", expand=True)

        # Analyzer module with history (Bottom Left)
        self.analyzer_frame = tk.Frame(self)
        self.analyzer_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.analyzer = AnalyzerModule(self.analyzer_frame, self.ssh_manager, self.terminal)
        self.analyzer.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = GaussianGUI()
    app.mainloop()