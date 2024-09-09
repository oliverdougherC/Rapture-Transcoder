import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
import json
import platform
import time
import queue
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the directory containing HT_linuxbuild.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from HT_macbuild import main as transcoder_main_function, command_queue

# Default values
DEFAULT_CONFIG = "config.json"

def load_config(config_file):
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Expand environment variables in the paths
        for key in ['input_directory', 'output_directory']:
            if key in config:
                config[key] = os.path.expandvars(config[key])
        
        return config
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_file}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from config file: {config_file}")
        return {}

def ensure_directory_exists(path):
    if path and not os.path.exists(path):
        os.makedirs(path)
        logging.info(f"Created directory: {path}")

class TranscoderGUI:
    def __init__(self, master):
        self.master = master
        master.title("Handbrake Transcoder")

        # Load config
        self.config = load_config(DEFAULT_CONFIG)

        # Get default directories and threads from config
        self.default_input_dir = self.config.get("input_directory", "")
        self.default_output_dir = self.config.get("output_directory", "")
        self.default_threads = self.config.get("default_threads", 4)  # Use 4 as fallback if not in config

        # Convert paths to the correct format for the current OS
        self.default_input_dir = os.path.expanduser(os.path.expandvars(self.default_input_dir))
        self.default_output_dir = os.path.expanduser(os.path.expandvars(self.default_output_dir))

        # Ensure default directories exist (only if they're not empty)
        if self.default_input_dir:
            ensure_directory_exists(self.default_input_dir)
        if self.default_output_dir:
            ensure_directory_exists(self.default_output_dir)

        self.delete_original_var = tk.BooleanVar()
        self.total_files = 0
        self.processed_files = 0
        self.current_progress = 0
        self.current_file = None
        self.is_transcoding = False
        self.is_paused = False
        self.cancel_flag = False
        self.create_widgets()
        self.progress_queue = queue.Queue()

    def create_widgets(self):
        # Input Directory
        self.input_label = tk.Label(self.master, text="Input Directory:")
        self.input_label.grid(row=0, column=0, sticky="e")
        self.input_entry = tk.Entry(self.master, width=50)
        self.input_entry.insert(0, self.default_input_dir)
        self.input_entry.grid(row=0, column=1)
        self.input_button = tk.Button(self.master, text="Browse", command=self.browse_input)
        self.input_button.grid(row=0, column=2)

        # Output Directory
        self.output_label = tk.Label(self.master, text="Output Directory:")
        self.output_label.grid(row=1, column=0, sticky="e")
        self.output_entry = tk.Entry(self.master, width=50)
        self.output_entry.insert(0, self.default_output_dir)
        self.output_entry.grid(row=1, column=1)
        self.output_button = tk.Button(self.master, text="Browse", command=self.browse_output)
        self.output_button.grid(row=1, column=2)

        # Config File
        self.config_label = tk.Label(self.master, text="Config File:")
        self.config_label.grid(row=2, column=0, sticky="e")
        self.config_entry = tk.Entry(self.master, width=50)
        self.config_entry.insert(0, DEFAULT_CONFIG)
        self.config_entry.grid(row=2, column=1)
        self.config_button = tk.Button(self.master, text="Browse", command=self.browse_config)
        self.config_button.grid(row=2, column=2)

        # Threads
        self.threads_label = tk.Label(self.master, text="Number of Threads per Task:")
        self.threads_label.grid(row=3, column=0, sticky="e")
        self.threads_spinbox = ttk.Spinbox(self.master, from_=1, to=16, width=5)
        self.threads_spinbox.set(self.default_threads)
        self.threads_spinbox.grid(row=3, column=1, sticky="w")

        # Delete Original Checkbox
        self.delete_original_check = tk.Checkbutton(self.master, text="Delete original files after successful transcoding", variable=self.delete_original_var)
        self.delete_original_check.grid(row=4, column=1, sticky="w")

        # Button Frame
        self.button_frame = tk.Frame(self.master)
        self.button_frame.grid(row=5, column=1, columnspan=2, pady=5)

        # Start Button
        self.start_button = tk.Button(self.button_frame, text="Start Transcoding", command=self.start_transcoding)
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Pause Button
        self.pause_button = tk.Button(self.button_frame, text="Pause", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        # Cancel Button
        self.cancel_button = tk.Button(self.button_frame, text="Cancel", command=self.cancel_transcoding, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.master, length=300, mode='determinate')
        self.progress_bar.grid(row=6, column=1, columnspan=2, pady=5)

        # Progress Percentage
        self.progress_percentage = tk.StringVar()
        self.progress_percentage.set("0%")
        self.percentage_label = tk.Label(self.master, textvariable=self.progress_percentage)
        self.percentage_label.grid(row=6, column=3, pady=5)

        # File Count
        self.file_count = tk.StringVar()
        self.file_count.set("0 / 0 files processed")
        self.file_count_label = tk.Label(self.master, textvariable=self.file_count)
        self.file_count_label.grid(row=7, column=1, columnspan=2, pady=5)

        # Status Label
        self.status = tk.StringVar()
        self.status_label = tk.Label(self.master, textvariable=self.status)
        self.status_label.grid(row=8, column=1, columnspan=2, pady=5)

    def browse_input(self):
        directory = filedialog.askdirectory(initialdir=os.path.expandvars(self.input_entry.get()))
        if directory:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, directory)

    def browse_output(self):
        directory = filedialog.askdirectory(initialdir=os.path.expandvars(self.output_entry.get()))
        if directory:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)

    def browse_config(self):
        config_file = filedialog.askopenfilename(initialdir=os.path.dirname(self.config_entry.get()),
                                                 filetypes=[("JSON files", "*.json")])
        if config_file:
            self.config_entry.delete(0, tk.END)
            self.config_entry.insert(0, config_file)

    def start_transcoding(self):
        input_dir = os.path.expandvars(self.input_entry.get())
        output_dir = os.path.expandvars(self.output_entry.get())
        config_file = self.config_entry.get()
        threads = int(self.threads_spinbox.get())  # Ensure this is an integer

        if not input_dir or not output_dir or not config_file:
            messagebox.showerror("Error", "Please fill in all fields")
            return

        # Ensure directories exist
        ensure_directory_exists(input_dir)
        ensure_directory_exists(output_dir)

        # Check if input directory is empty
        if not os.listdir(input_dir):
            messagebox.showerror("Error", "Input directory is empty")
            return

        delete_original = self.delete_original_var.get()

        # Count total files
        self.total_files = sum(1 for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and any(f.lower().endswith(ext) for ext in self.config.get('file_types', [])))
        self.processed_files = 0
        self.current_file = None
        self.current_progress = 0
        logging.debug(f"Total files to process: {self.total_files}")
        self.update_initial_progress()

        self.is_transcoding = True
        self.cancel_flag = False
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
        threading.Thread(target=self.run_transcoding, args=(input_dir, output_dir, config_file, threads, delete_original)).start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.config(text="Resume")
            self.status.set("Transcoding paused")
            command_queue.put('p')
        else:
            self.pause_button.config(text="Pause")
            self.status.set("Transcoding resumed")
            command_queue.put('r')

    def cancel_transcoding(self):
        self.cancel_flag = True
        self.status.set("Cancelling transcoding...")

    def run_transcoding(self, input_dir, output_dir, config_file, threads, delete_original):
        self.status.set("Transcoding in progress...")
        
        def progress_callback(file_processed, progress):
            self.master.after(0, self.update_progress, file_processed, progress)
            return self.cancel_flag

        def command_callback():
            try:
                return command_queue.get_nowait()
            except queue.Empty:
                return None

        try:
            sys.argv = [
                sys.argv[0],
                "-c", config_file,
                "-i", input_dir,
                "-o", output_dir,
                "-t", str(threads)  # Ensure threads is passed as a string
            ]
            if delete_original:
                sys.argv.append("--delete-original")
            
            logging.debug(f"Launching transcoder with arguments: {sys.argv}")
            
            transcoder_main_function(input_dir, output_dir, progress_callback, command_callback, delete_original)
        except Exception as e:
            logging.error(f"Error during transcoding: {str(e)}", exc_info=True)
            self.status.set(f"Error during transcoding: {str(e)}")
        
        self.is_transcoding = False
        self.master.after(0, self.update_buttons)
        
        if self.cancel_flag:
            self.status.set("Transcoding cancelled")
        else:
            self.status.set("Transcoding completed!")

    def update_progress(self, file_processed, progress):
        if file_processed != self.current_file:
            self.current_file = file_processed
            if self.processed_files < self.total_files:
                self.processed_files += 1
        self.current_progress = progress
        
        if self.total_files > 0:
            overall_progress = ((self.processed_files - 1) * 100 + progress) / self.total_files
            self.progress_bar['value'] = overall_progress
            self.progress_percentage.set(f"{overall_progress:.1f}%")
        
        self.file_count.set(f"Processing file {self.processed_files}/{self.total_files}")
        self.status.set(f"Processing: {file_processed} - {progress:.1f}%")

    def update_initial_progress(self):
        if self.total_files > 0:
            self.progress_bar['value'] = 0
            self.progress_percentage.set("0.0%")
        self.file_count.set(f"Processing file 0/{self.total_files}")
        self.status.set("Ready to start transcoding")

    def update_buttons(self):
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    gui = TranscoderGUI(root)
    root.mainloop()