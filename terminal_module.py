import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

class TerminalModule(tk.LabelFrame):
    def __init__(self, parent, ssh_manager=None, config=None):
        super().__init__(parent, text="SSH Terminal & Network Status", padx=5, pady=5, bg="#e9f1f7")
        self.ssh_manager = ssh_manager
        self._create_ui()
        self._setup_tags()
        
        if config:
            self.cb_srv.set(config.get('server', ''))
            self.e_user.insert(0, config.get('username', ''))
            self.e_pwd.insert(0, config.get('password', ''))
            
        # Start connection check loop every 10 seconds
        self.check_connection_loop()

    def get_state(self):
        return {
            'server': self.cb_srv.get(),
            'username': self.e_user.get(),
            'password': self.e_pwd.get()
        }

    def _create_ui(self):
        cf = tk.Frame(self, pady=5)
        cf.pack(fill="x")
        
        tk.Label(cf, text="Srv:").pack(side="left")
        self.cb_srv = ttk.Combobox(cf, values=self.ssh_manager.load_machines() if self.ssh_manager else [], width=8)
        self.cb_srv.pack(side="left", padx=2)
        
        tk.Label(cf, text="U:").pack(side="left")
        self.e_user = tk.Entry(cf, width=10)
        self.e_user.pack(side="left", padx=2)
        
        tk.Label(cf, text="P:").pack(side="left")
        self.e_pwd = tk.Entry(cf, show="*", width=10)
        self.e_pwd.pack(side="left", padx=2)
        
        # Dynamic Single Button
        self.b_connect_toggle = tk.Button(self, text="Connect", command=self._toggle_connection, bg="#1971c2", fg="white", relief="flat", font=("Arial", 9, "bold"))
        self.b_connect_toggle.pack(in_=cf, side="left", padx=5, fill="x", expand=True)

        # Text Area
        self.txt = scrolledtext.ScrolledText(self, state='disabled', height=15, bg="#1e1e1e", fg="#dcdcdc", font=("Consolas", 10))
        self.txt.pack(fill="both", expand=True, pady=5)

        # Input Bar
        inf = tk.Frame(self, bg="#1e1e1e")
        inf.pack(fill="x")
        self.lbl_prompt = tk.Label(inf, text=" >", fg="#51cf66", bg="#1e1e1e", font=("Consolas", 10, "bold"))
        self.lbl_prompt.pack(side="left")
        self.e_cmd = tk.Entry(inf, bg="#2d2d2d", fg="white", borderwidth=0, font=("Consolas", 10))
        self.e_cmd.pack(side="left", fill="x", expand=True, padx=5)
        self.e_cmd.bind("<Return>", self._send_cmd)

    def _setup_tags(self):
        for t, c in [("error", "#ff6b6b"), ("success", "#51cf66"), ("info", "#339af0"), ("cmd", "#fcc419"), ("timestamp", "#868e96")]:
            self.txt.tag_config(t, foreground=c)

    def _toggle_connection(self):
        """Single button to connect or disconnect depending on the current state"""
        if self.ssh_manager and self.ssh_manager.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        m, u, p = self.cb_srv.get(), self.e_user.get(), self.e_pwd.get()
        if not all([m, u, p]): 
            return messagebox.showwarning("Error", "Fill all fields.")
        
        self._log("Connecting to server...\n", "info")
        ok, msg = self.ssh_manager.connect(m, u, p)
        self._log(msg + "\n", "success" if ok else "error")
        self.update_button_ui()

    def _disconnect(self):
        self.ssh_manager.disconnect()
        self._log("Disconnected from server.\n", "error")
        self.update_button_ui()

    def update_button_ui(self):
        """Updates the visual state of the single connection button"""
        if self.ssh_manager and self.ssh_manager.is_connected:
            self.b_connect_toggle.config(text="Online (Click to Disc.)", bg="#40c057", fg="white")
            self.lbl_prompt.config(text=f" [{self.ssh_manager.prompt_name}] >")
        else:
            self.b_connect_toggle.config(text="Connect", bg="#1971c2", fg="white")
            self.lbl_prompt.config(text=" >")

    def check_connection_loop(self):
        """Checks the connection status in the background every 10 seconds"""
        if self.ssh_manager:
            old_state = self.ssh_manager.is_connected
            new_state = self.ssh_manager.check_connection_status()
            if old_state != new_state:
                if not new_state:
                    self._log("Connection drop detected by heartbeat monitor.\n", "error")
                self.update_button_ui()
        self.after(10000, self.check_connection_loop)

    def _send_cmd(self, e):
        cmd = self.e_cmd.get().strip()
        if not cmd: return
        self.e_cmd.delete(0, tk.END)

        if not self.ssh_manager or not self.ssh_manager.is_connected:
            self._log(f"> {cmd}\nError: Not connected.\n", "error")
            return

        folder = self.ssh_manager.prompt_name
        self._log(f"[{folder}] > {cmd}\n", "cmd")

        ok, out = self.ssh_manager.run_terminal_command(cmd)
        if out: self._log(out + "\n", "success" if ok else "error")
        self.lbl_prompt.config(text=f" [{self.ssh_manager.prompt_name}] >")

    def write_log(self, msg, tag=None):
        self._log(f"[APP LOG] {msg}\n", tag)

    def _log(self, txt, tag=None):
        """Appends text with automatic timestamp insertion"""
        self.txt.configure(state='normal')
        
        # Create timestamp
        ts = f"[{datetime.now().strftime('%H:%M:%S')}] "
        
        # # Insert timestamp then the log text
        self.txt.insert(tk.END, ts, "timestamp")
        if tag:
            self.txt.insert(tk.END, txt, tag)
        else:
            self.txt.insert(tk.END, txt)
            
        self.txt.see(tk.END)
        self.txt.configure(state='disabled')