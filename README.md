# GaussianGUI - Computational Chemistry Dashboard

A lightweight, robust, and asynchronous graphical interface built in Python/Tkinter to streamline the workflow of computational chemists using Gaussian 09/16 on remote SSH servers. 

This tool abstracts tedious command-line interactions, file transfers, and manual log parsing, allowing researchers to focus entirely on chemistry.

## 🚀 Key Features

* **Smart GJF Generator:** Build Gaussian input files (`.gjf`) from `.xyz` coordinates or restart from an existing checkpoint (`.chk`) file. Includes dynamic configuration for core allocation, memory requirements, electronic methods (DFT, Semi-Empirical, Post-HF), and standard basis sets.
* **Relaxed PES Scan Setup:** Dedicated UI dialog to easily configure coordinate scanning (`ModRedundant`) for reaction profiling and transition state searches.
* **Isolated Remote Execution:** Automatically replicates your local project folder structure (e.g., `Project_Name/Molecule_Name/`) inside a generic `gaussian_gui_work` root directory on the server, preventing file conflicts.
* **Asynchronous SSH Engine:** Built on `paramiko`. Submits jobs via background processes and captures the PID. The user interface remains fully responsive during remote operations.
* **Live Process Monitoring:** * Real-time `.chk` file size tracking.
  * Live SCF progress checking using remote text extraction.
  * Deep core allocation inspection via `pstree` to verify parallelization efficiency.
* **Automated Data Retrieval:** Automatically downloads `.log` and `.chk` files upon job completion. Features one-click formatted checkpoint (`.fchk`) generation and retrieval.
* **Intelligent Log Parser:** Automatically detects calculation types, extracts final energies, flags Error/Normal terminations, parses frequencies (highlighting imaginary modes), and tabulates energy curves from Relaxed Scans.

## 🧬 Core Functions Technical Overview

* **`execute_command_background` (`ssh_manager.py`):** Opens a non-blocking SSH session channel to run the Gaussian command using a background shell wrapper (`nohup`), capturing and returning the process PID immediately without freezing the GUI loop.
* **`monitor_process` (`executor.py`):** Runs in a dedicated background thread to query the server status via `ps -p {pid}` every 5 seconds. It features built-in network fault tolerance (safely pausing and retrying if the client PC goes to sleep or loses Wi-Fi) and triggers the file download sequence as soon as the job ends.
* **`extract_scan_csv` (`log_parser.py`):** Parses the standard orientation matrices throughout a relaxed potential energy surface (PES) scan log, extracts the 3D coordinates for the targeted bond atoms, mathematically computes the exact distance at each step, and exports a clean structural history report to a `.csv` file.

## ⚙️ Development Setup

This application was developed and tested using **Python 3.12.5**.

### 1. Clone the repository
```bash
git clone [https://github.com/YourUsername/Gaussian09_GUI.git](https://github.com/YourUsername/Gaussian09_GUI.git)
cd GaussianGUI
