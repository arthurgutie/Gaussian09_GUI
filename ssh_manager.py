import paramiko
import os

class SSHManager:
    def __init__(self):
        self.ssh_client = None
        self.is_connected = False
        self.machines_file = "machines/machines.txt"
        
        # Generic root folder on the remote server
        self.remote_base_dir = "gaussian_gui_work"
        self.current_terminal_dir = self.remote_base_dir
        
        os.makedirs("machines", exist_ok=True)

    def connect(self, machine, username, password):
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(machine, username=username, password=password, timeout=10)
            
            self._exec(f"mkdir -p {self.remote_base_dir}")
            self.is_connected = True
            return True, f"Connected to {machine}"
        except Exception as e:
            self.is_connected = False
            return False, str(e)

    def check_connection_status(self):
        """Quickly checks if the SSH channel is active without overloading the server"""
        if not self.ssh_client or not self.is_connected:
            self.is_connected = False
            return False
        try:
            transport = self.ssh_client.get_transport()
            if transport is None or not transport.is_active():
                self.is_connected = False
                return False
            transport.send_ignore()
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def _exec(self, full_cmd):
        """Standard blocking method for short commands"""
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(full_cmd)
            out = stdout.read().decode('utf-8', 'replace').strip()
            err = stderr.read().decode('utf-8', 'replace').strip()
            return (True, out) if stdout.channel.recv_exit_status() == 0 else (False, err)
        except Exception as e:
            self.is_connected = False
            raise ConnectionError("SSH Connection lost during command execution.") from e

    def _get_work_dir(self, sub_dir):
        """Builds the remote path with the project/molecule subfolder"""
        if sub_dir:
            sub_dir_unix = str(sub_dir).replace('\\', '/')
            return f"'{self.remote_base_dir}/{sub_dir_unix}'"
        return f"'{self.remote_base_dir}'"

    def run_command_sync(self, cmd, sub_dir=""):
        if not self.is_connected: return False, "Not connected"
        work_dir = self._get_work_dir(sub_dir)
        try: 
            return self._exec(f"cd {work_dir} && {cmd}")
        except Exception as e: 
            return False, str(e)

    def execute_command_background(self, cmd, sub_dir=""):
        """Launches the Gaussian calculation in the background via a non-blocking SSH session and immediately captures its PID"""
        if not self.is_connected: return None
        work_dir = self._get_work_dir(sub_dir)
        try:
            full_cmd = f"bash -lc 'cd {work_dir} && nohup bash -c \"{cmd}\" > /dev/null 2>&1 & echo $!'"
            transport = self.ssh_client.get_transport()
            chan = transport.open_session()
            chan.exec_command(full_cmd)
            out_file = chan.makefile()
            pid = out_file.readline().strip()
            return pid if pid.isdigit() else None

        except Exception:
            self.is_connected = False
            return None

    def get_remote_file_size(self, filename, sub_dir=""):
        """Retrieves the size of a remote file in MB via SFTP"""
        if not self.is_connected: return None
        work_dir = self.remote_base_dir
        if sub_dir: work_dir += f"/{str(sub_dir).replace('\\', '/')}"
        
        try:
            sftp = self.ssh_client.open_sftp()
            stat_res = sftp.stat(f"{work_dir}/{filename}")
            sftp.close()
            size_mb = stat_res.st_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except Exception:
            return "N/A (Not on server)"

    def upload_file(self, local_path, remote_name, sub_dir=""):
        try:
            work_dir_shell = self._get_work_dir(sub_dir)
            self._exec(f"mkdir -p {work_dir_shell}") # Ensure parent directory exists
            
            work_dir_sftp = self.remote_base_dir
            if sub_dir: work_dir_sftp += f"/{str(sub_dir).replace('\\', '/')}"
            
            sftp = self.ssh_client.open_sftp()
            sftp.put(str(local_path), f"{work_dir_sftp}/{remote_name}")
            sftp.close()
            return True
        except Exception:
            self.is_connected = False
            return False

    def download_file(self, remote_name, local_path, sub_dir=""):
        try:
            work_dir_sftp = self.remote_base_dir
            if sub_dir: work_dir_sftp += f"/{str(sub_dir).replace('\\', '/')}"
            
            sftp = self.ssh_client.open_sftp()
            sftp.get(f"{work_dir_sftp}/{remote_name}", str(local_path))
            sftp.close()
            return True
        except Exception:
            self.is_connected = False
            return False

    def disconnect(self):
        if self.ssh_client: 
            try: self.ssh_client.close()
            except Exception: pass
        self.is_connected = False

    def load_machines(self):
        if not os.path.exists(self.machines_file): return []
        with open(self.machines_file, "r") as f: return [l.strip() for l in f if l.strip()]

    @property
    def prompt_name(self):
        return self.current_terminal_dir.strip('"\'').split('/')[-1]

    def run_terminal_command(self, cmd):
        if not self.is_connected: return False, "Not connected"
        try:
            if cmd.strip().startswith("cd "):
                track_cmd = f"cd '{self.current_terminal_dir}' && {cmd} && pwd"
                ok, out = self._exec(track_cmd)
                if ok:
                    self.current_terminal_dir = out.strip()
                    return True, ""  
                else:
                    return False, out

            return self._exec(f"cd '{self.current_terminal_dir}' && {cmd}")
        except Exception as e:
            return False, str(e)