import sys
import os
import json
import logging
import threading
import queue
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox, QProgressBar, 
                             QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Add the directory containing HT_macbuild.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from HT_macbuild import main as transcoder_main_function, command_queue

# Default values
DEFAULT_CONFIG = "config.json"

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

class TranscoderThread(QThread):
    progress_update = pyqtSignal(str, float)
    overall_progress_update = pyqtSignal(float)
    status_update = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, input_dir, output_dir, config_file, threads, delete_original):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config_file = config_file
        self.threads = threads
        self.delete_original = delete_original
        self.cancel_flag = False
        self.file_count = 0
        self.files_processed = 0

    def run(self):
        def progress_callback(file_processed, progress):
            self.progress_update.emit(file_processed, progress)
            if progress == 100:
                self.files_processed += 1
                overall_progress = (self.files_processed / self.file_count) * 100
                self.overall_progress_update.emit(overall_progress)
            return self.cancel_flag

        def command_callback():
            try:
                return command_queue.get_nowait()
            except queue.Empty:
                return None

        try:
            # Count the number of files to be processed
            self.file_count = sum(1 for f in os.listdir(self.input_dir) if os.path.isfile(os.path.join(self.input_dir, f)))
            
            transcoder_main_function(self.input_dir, self.output_dir, progress_callback, command_callback, self.delete_original)
        except Exception as e:
            self.status_update.emit(f"Error during transcoding: {str(e)}")
        finally:
            self.finished.emit()

    def cancel(self):
        self.cancel_flag = True

class TranscoderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config(DEFAULT_CONFIG)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Handbrake Transcoder")
        self.setGeometry(100, 100, 600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Input Directory
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input Directory:"))
        self.input_entry = QLineEdit(self.config.get("input_directory", ""))
        input_layout.addWidget(self.input_entry)
        input_button = QPushButton("Browse")
        input_button.clicked.connect(self.browse_input)
        input_layout.addWidget(input_button)
        layout.addLayout(input_layout)

        # Output Directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))
        self.output_entry = QLineEdit(self.config.get("output_directory", ""))
        output_layout.addWidget(self.output_entry)
        output_button = QPushButton("Browse")
        output_button.clicked.connect(self.browse_output)
        output_layout.addWidget(output_button)
        layout.addLayout(output_layout)

        # Config File
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("Config File:"))
        self.config_entry = QLineEdit(DEFAULT_CONFIG)
        config_layout.addWidget(self.config_entry)
        config_button = QPushButton("Browse")
        config_button.clicked.connect(self.browse_config)
        config_layout.addWidget(config_button)
        layout.addLayout(config_layout)

        # Threads
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(QLabel("Number of Threads per Task:"))
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 16)
        self.threads_spinbox.setValue(self.config.get("default_threads", 4))
        threads_layout.addWidget(self.threads_spinbox)
        layout.addLayout(threads_layout)

        # Delete Original Checkbox
        self.delete_original_check = QCheckBox("Delete original files after successful transcoding")
        layout.addWidget(self.delete_original_check)

        # Buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Transcoding")
        self.start_button.clicked.connect(self.start_transcoding)
        button_layout.addWidget(self.start_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_transcoding)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Current File Progress Bar
        self.current_progress_bar = QProgressBar()
        layout.addWidget(self.current_progress_bar)

        # Overall Progress Bar (initially hidden)
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setVisible(False)
        layout.addWidget(self.overall_progress_bar)

        # Status Label
        self.status_label = QLabel("Ready to start transcoding")
        layout.addWidget(self.status_label)

        self.show()

    def browse_input(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if directory:
            self.input_entry.setText(directory)

    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_entry.setText(directory)

    def browse_config(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Config File", "", "JSON Files (*.json)")
        if file_name:
            self.config_entry.setText(file_name)

    def start_transcoding(self):
        input_dir = self.input_entry.text()
        output_dir = self.output_entry.text()
        config_file = self.config_entry.text()
        threads = self.threads_spinbox.value()
        delete_original = self.delete_original_check.isChecked()

        if not input_dir or not output_dir or not config_file:
            QMessageBox.critical(self, "Error", "Please fill in all fields")
            return

        ensure_directory_exists(input_dir)
        ensure_directory_exists(output_dir)

        file_count = sum(1 for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)))
        if file_count == 0:
            QMessageBox.critical(self, "Error", "Input directory is empty")
            return

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

        # Show overall progress bar if there's more than one file
        self.overall_progress_bar.setVisible(file_count > 1)

        self.transcoder_thread = TranscoderThread(input_dir, output_dir, config_file, threads, delete_original)
        self.transcoder_thread.progress_update.connect(self.update_progress)
        self.transcoder_thread.overall_progress_update.connect(self.update_overall_progress)
        self.transcoder_thread.status_update.connect(self.update_status)
        self.transcoder_thread.finished.connect(self.transcoding_finished)
        self.transcoder_thread.start()

    def toggle_pause(self):
        if self.pause_button.text() == "Pause":
            self.pause_button.setText("Resume")
            self.status_label.setText("Transcoding paused")
            command_queue.put('p')
        else:
            self.pause_button.setText("Pause")
            self.status_label.setText("Transcoding resumed")
            command_queue.put('r')

    def cancel_transcoding(self):
        self.transcoder_thread.cancel()
        self.status_label.setText("Cancelling transcoding...")

    def update_progress(self, file_processed, progress):
        self.current_progress_bar.setValue(int(progress))
        self.status_label.setText(f"Processing: {file_processed} - {progress:.1f}%")

    def update_overall_progress(self, progress):
        self.overall_progress_bar.setValue(int(progress))

    def update_status(self, status):
        self.status_label.setText(status)

    def transcoding_finished(self):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Transcoding completed!")
        self.overall_progress_bar.setVisible(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = TranscoderGUI()
    sys.exit(app.exec())