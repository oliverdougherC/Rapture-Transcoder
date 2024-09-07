import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys

# Add the directory containing HT_linuxbuild.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from HT_linuxbuild import main as transcoder_main_function, pause_event

# Default paths and values
USER = os.getenv('USER')
DEFAULT_INPUT_DIR = f"/home/{USER}/media/transcode_input"
DEFAULT_OUTPUT_DIR = f"/home/{USER}/media/transcode_output"
DEFAULT_THREADS = 4
DEFAULT_CONFIG = "config.json"

def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

class TranscoderGUI:
    def __init__(self, master):
        self.master = master
        master.title("Handbrake Transcoder")

        # Ensure default directories exist
        ensure_directory_exists(DEFAULT_INPUT_DIR)
        ensure_directory_exists(DEFAULT_OUTPUT_DIR)

        self.delete_original_var = tk.BooleanVar()
        self.create_widgets()

    def create_widgets(self):
        # Input Directory
        self.input_label = tk.Label(self.master, text="Input Directory:")
        self.input_label.grid(row=0, column=0, sticky="e")
        self.input_entry = tk.Entry(self.master, width=50)
        self.input_entry.insert(0, DEFAULT_INPUT_DIR)
        self.input_entry.grid(row=0, column=1)
        self.input_button = tk.Button(self.master, text="Browse", command=self.browse_input)
        self.input_button.grid(row=0, column=2)

        # Output Directory
        self.output_label = tk.Label(self.master, text="Output Directory:")
        self.output_label.grid(row=1, column=0, sticky="e")
        self.output_entry = tk.Entry(self.master, width=50)
        self.output_entry.insert(0, DEFAULT_OUTPUT_DIR)
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
        self.threads_label = tk.Label(self.master, text="Number of Threads:")
        self.threads_label.grid(row=3, column=0, sticky="e")
        self.threads_spinbox = ttk.Spinbox(self.master, from_=1, to=16, width=5)
        self.threads_spinbox.set(DEFAULT_THREADS)
        self.threads_spinbox.grid(row=3, column=1, sticky="w")

        # Delete Original Checkbox
        self.delete_original_check = tk.Checkbutton(self.master, text="Delete original files after successful transcoding", variable=self.delete_original_var)
        self.delete_original_check.grid(row=4, column=1, sticky="w")

        # Start and Pause Buttons
        self.start_button = tk.Button(self.master, text="Start Transcoding", command=self.start_transcoding)
        self.start_button.grid(row=5, column=1)
        self.pause_button = tk.Button(self.master, text="Pause", command=self.pause_transcoding)
        self.pause_button.grid(row=5, column=2)

        # Progress Label
        self.progress = tk.StringVar()
        self.progress_label = tk.Label(self.master, textvariable=self.progress)
        self.progress_label.grid(row=6, column=1, columnspan=2)

    def browse_input(self):
        directory = filedialog.askdirectory(initialdir=self.input_entry.get())
        if directory:
            ensure_directory_exists(directory)
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, directory)

    def browse_output(self):
        directory = filedialog.askdirectory(initialdir=self.output_entry.get())
        if directory:
            ensure_directory_exists(directory)
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)

    def browse_config(self):
        config_file = filedialog.askopenfilename(initialdir=os.path.dirname(self.config_entry.get()),
                                                 filetypes=[("JSON files", "*.json")])
        if config_file:
            self.config_entry.delete(0, tk.END)
            self.config_entry.insert(0, config_file)

    def start_transcoding(self):
        input_dir = self.input_entry.get()
        output_dir = self.output_entry.get()
        config_file = self.config_entry.get()
        threads = self.threads_spinbox.get()

        if not input_dir or not output_dir or not config_file:
            messagebox.showerror("Error", "Please fill in all fields")
            return

        # Ensure directories exist
        ensure_directory_exists(input_dir)
        ensure_directory_exists(output_dir)

        delete_original = self.delete_original_var.get()

        threading.Thread(target=self.run_transcoding, args=(input_dir, output_dir, config_file, threads, delete_original)).start()

    def run_transcoding(self, input_dir, output_dir, config_file, threads, delete_original):
        self.progress.set("Transcoding and verification in progress...")
        sys.argv = [sys.argv[0], "-c", config_file, "-i", input_dir, "-o", output_dir, "-t", threads]
        if delete_original:
            sys.argv.append("--delete-original")
        transcoder_main_function()
        self.progress.set("Transcoding and verification completed!")

    def pause_transcoding(self):
        if pause_event.is_set():
            pause_event.clear()
            self.pause_button.config(text="Pause")
        else:
            pause_event.set()
            self.pause_button.config(text="Resume")

if __name__ == "__main__":
    root = tk.Tk()
    gui = TranscoderGUI(root)
    root.mainloop()