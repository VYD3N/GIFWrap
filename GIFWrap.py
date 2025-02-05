import tkinter as tk
from tkinter import ttk, filedialog
from gif_converter import GifConverter
import threading
import os
import queue
import time

class GifConverterGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("GIFWrap")
        self.window.geometry("600x400")
        
        # Set icon
        try:
            # Try different icon sizes
            icons = []
            icon_dir = 'icons'
            print("Looking for icons in:", os.path.abspath(icon_dir))
            
            for size in [16, 32, 48, 64, 128, 256]:
                icon_path = os.path.join(icon_dir, f'gifwrap_{size}.png')
                try:
                    if os.path.exists(icon_path):
                        print(f"Loading icon: {icon_path}")
                        icon = tk.PhotoImage(file=icon_path)
                        icons.append(icon)
                    else:
                        print(f"Icon not found: {icon_path}")
                except Exception as e:
                    print(f"Error loading {icon_path}: {str(e)}")
                    continue
            
            if icons:
                print(f"Setting {len(icons)} icons")
                self.window.iconphoto(True, *icons)
            else:
                # Fallback to default size
                default_path = os.path.join(icon_dir, 'gifwrap.png')
                if os.path.exists(default_path):
                    print(f"Using default icon: {default_path}")
                    icon = tk.PhotoImage(file=default_path)
                    self.window.iconphoto(True, icon)
                else:
                    print(f"Default icon not found: {default_path}")
        except Exception as e:
            print(f"Error setting icon: {str(e)}")
        
        # Create converter instance
        self.converter = GifConverter()
        
        # Create message queue for thread-safe logging
        self.log_queue = queue.Queue()
        
        # Create main frame
        self.main_frame = ttk.Frame(self.window, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input file selection
        self.input_frame = ttk.LabelFrame(self.main_frame, text="Input Video", padding="5")
        self.input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.input_path = tk.StringVar()
        self.input_entry = ttk.Entry(self.input_frame, textvariable=self.input_path, width=50)
        self.input_entry.grid(row=0, column=0, padx=5)
        
        self.browse_btn = ttk.Button(self.input_frame, text="Browse", command=self.browse_input)
        self.browse_btn.grid(row=0, column=1, padx=5)
        
        # Output file selection
        self.output_frame = ttk.LabelFrame(self.main_frame, text="Output GIF", padding="5")
        self.output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.output_path = tk.StringVar()
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path, width=50)
        self.output_entry.grid(row=0, column=0, padx=5)
        
        self.save_btn = ttk.Button(self.output_frame, text="Save As", command=self.browse_output)
        self.save_btn.grid(row=0, column=1, padx=5)
        
        # Progress and status
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        self.progress = ttk.Progressbar(self.main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Custom size frame
        self.custom_frame = ttk.Frame(self.button_frame)
        self.custom_frame.grid(row=0, column=2, padx=5)
        
        self.custom_size = tk.StringVar(value="50")
        self.custom_entry = ttk.Entry(
            self.custom_frame,
            textvariable=self.custom_size,
            width=5
        )
        self.custom_entry.grid(row=0, column=0, padx=2)
        ttk.Label(self.custom_frame, text="MB").grid(row=0, column=1)
        
        # Buttons
        self.convert_btn = ttk.Button(
            self.button_frame, 
            text="Create Full (15MB)", 
            command=self.start_conversion
        )
        self.convert_btn.grid(row=0, column=0, padx=5)
        
        self.thumb_btn = ttk.Button(
            self.button_frame, 
            text="Create Preview (2MB)", 
            command=self.start_thumbnail_conversion
        )
        self.thumb_btn.grid(row=0, column=1, padx=5)
        
        self.custom_btn = ttk.Button(
            self.custom_frame,
            text="Create Custom",
            command=self.start_custom_conversion
        )
        self.custom_btn.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Log area
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Conversion Log", padding="5")
        self.log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = tk.Text(self.log_frame, height=10, width=60)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for log
        self.scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = self.scrollbar.set
        
        # Start log checker
        self.window.after(100, self.check_log_queue)
        
    def check_log_queue(self):
        """Check for new log messages"""
        while True:
            try:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, str(message) + "\n")
                self.log_text.see(tk.END)
            except queue.Empty:
                break
        self.window.after(100, self.check_log_queue)
    
    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.wmv")]
        )
        if filename:
            self.input_path.set(filename)
            # Auto-set output path (without suffix - will be added when conversion starts)
            if not self.output_path.get():
                output = os.path.splitext(filename)[0]
                self.output_path.set(output)
    
    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save GIF As",
            defaultextension=".gif",
            filetypes=[("GIF files", "*.gif")]
        )
        if filename:
            # Create directory if it doesn't exist
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            # Store base path without suffix
            base_path = os.path.splitext(filename)[0]
            self.output_path.set(base_path)
    
    def update_status(self, message):
        """Thread-safe status update"""
        self.window.after(0, lambda: self.status_var.set(message))
    
    def start_conversion(self):
        if not self.input_path.get():
            self.status_var.set("Error: Please select an input video")
            return
        
        if not self.output_path.get():
            self.status_var.set("Error: Please select output location")
            return
        
        # Add Sub15 suffix to output path
        base_path = os.path.splitext(self.output_path.get())[0]
        if not base_path.endswith('Sub15'):
            self.output_path.set(f"{base_path}_Sub15.gif")
        
        # Disable buttons during conversion
        self.convert_btn.state(['disabled'])
        self.thumb_btn.state(['disabled'])
        self.custom_btn.state(['disabled'])
        self.browse_btn.state(['disabled'])
        self.save_btn.state(['disabled'])
        self.custom_entry.state(['disabled'])
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start progress bar
        self.progress.start()
        
        # Start conversion in separate thread
        thread = threading.Thread(target=self.convert)
        thread.daemon = True
        thread.start()
    
    def start_thumbnail_conversion(self):
        if not self.input_path.get():
            self.status_var.set("Error: Please select an input video")
            return
        
        if not self.output_path.get():
            self.status_var.set("Error: Please select output location")
            return
        
        # Add Sub2 suffix to output path
        base_path = os.path.splitext(self.output_path.get())[0]
        if not base_path.endswith('Sub2'):
            self.output_path.set(f"{base_path}_Sub2.gif")
        
        # Disable buttons during conversion
        self.convert_btn.state(['disabled'])
        self.thumb_btn.state(['disabled'])
        self.custom_btn.state(['disabled'])
        self.browse_btn.state(['disabled'])
        self.save_btn.state(['disabled'])
        self.custom_entry.state(['disabled'])
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start progress bar
        self.progress.start()
        
        # Start conversion in separate thread
        thread = threading.Thread(target=self.convert_thumbnail)
        thread.daemon = True
        thread.start()
    
    def start_custom_conversion(self):
        try:
            size = int(self.custom_size.get())
            if not 1 <= size <= 100:
                self.status_var.set("Error: Size must be between 1 and 100 MB")
                return
        except ValueError:
            self.status_var.set("Error: Please enter a valid number")
            return

        if not self.input_path.get():
            self.status_var.set("Error: Please select an input video")
            return
        
        if not self.output_path.get():
            self.status_var.set("Error: Please select output location")
            return
        
        # Add Custom suffix to output path
        base_path = os.path.splitext(self.output_path.get())[0]
        if not base_path.endswith(f'Sub{size}'):
            self.output_path.set(f"{base_path}_Sub{size}.gif")
        
        # Disable buttons during conversion
        self.convert_btn.state(['disabled'])
        self.thumb_btn.state(['disabled'])
        self.custom_btn.state(['disabled'])
        self.browse_btn.state(['disabled'])
        self.save_btn.state(['disabled'])
        self.custom_entry.state(['disabled'])
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start progress bar
        self.progress.start()
        
        # Start conversion in separate thread
        thread = threading.Thread(target=lambda: self.convert_custom(size))
        thread.daemon = True
        thread.start()
    
    def convert(self):
        try:
            self.update_status("Converting...")
            
            # Redirect print statements to queue
            import sys
            class LogRedirector:
                def __init__(self, queue):
                    self.queue = queue
                def write(self, message):
                    if message.strip():  # Only queue non-empty messages
                        self.queue.put(message.strip())
                def flush(self):
                    pass
            
            sys.stdout = LogRedirector(self.log_queue)
            
            # Run conversion
            self.converter.convert_to_gif(self.input_path.get(), self.output_path.get())
            
            self.update_status("Conversion Complete!")
            
        except Exception as e:
            self.log_queue.put(f"Error: {str(e)}")
            self.update_status(f"Error: {str(e)}")
        
        finally:
            # Re-enable buttons
            self.window.after(0, lambda: self.convert_btn.state(['!disabled']))
            self.window.after(0, lambda: self.thumb_btn.state(['!disabled']))
            self.window.after(0, lambda: self.custom_btn.state(['!disabled']))
            self.window.after(0, lambda: self.browse_btn.state(['!disabled']))
            self.window.after(0, lambda: self.save_btn.state(['!disabled']))
            self.window.after(0, lambda: self.custom_entry.state(['!disabled']))
            self.window.after(0, lambda: self.progress.stop())
            sys.stdout = sys.__stdout__
    
    def convert_thumbnail(self):
        try:
            self.update_status("Converting to thumbnail...")
            
            # Redirect print statements to queue
            import sys
            class LogRedirector:
                def __init__(self, queue):
                    self.queue = queue
                def write(self, message):
                    if message.strip():  # Only queue non-empty messages
                        self.queue.put(message.strip())
                def flush(self):
                    pass
            
            sys.stdout = LogRedirector(self.log_queue)
            
            # Run thumbnail conversion
            self.converter.convert_to_thumbnail(self.input_path.get(), self.output_path.get())
            
            self.update_status("Thumbnail Creation Complete!")
            
        except Exception as e:
            self.log_queue.put(f"Error: {str(e)}")
            self.update_status(f"Error: {str(e)}")
        
        finally:
            # Re-enable buttons
            self.window.after(0, lambda: self.convert_btn.state(['!disabled']))
            self.window.after(0, lambda: self.thumb_btn.state(['!disabled']))
            self.window.after(0, lambda: self.custom_btn.state(['!disabled']))
            self.window.after(0, lambda: self.browse_btn.state(['!disabled']))
            self.window.after(0, lambda: self.save_btn.state(['!disabled']))
            self.window.after(0, lambda: self.custom_entry.state(['!disabled']))
            self.window.after(0, lambda: self.progress.stop())
            sys.stdout = sys.__stdout__
    
    def convert_custom(self, size_mb):
        try:
            self.update_status(f"Converting to {size_mb}MB...")
            
            # Update converter settings
            original_target_min = self.converter.TARGET_MIN_BYTES
            original_target_max = self.converter.TARGET_MAX_BYTES
            original_target_min_mb = self.converter.TARGET_MIN_MB
            original_target_max_mb = self.converter.TARGET_MAX_MB
            
            # Set new targets (0.99% margin)
            target_min = size_mb * 0.99
            target_max = size_mb * 0.999
            self.converter.TARGET_MIN_MB = target_min
            self.converter.TARGET_MAX_MB = target_max
            self.converter.TARGET_MIN_BYTES = int(target_min * 1024 * 1024)
            self.converter.TARGET_MAX_BYTES = int(target_max * 1024 * 1024)
            
            try:
                # Run conversion
                self.converter.convert_to_gif(self.input_path.get(), self.output_path.get())
            finally:
                # Restore original settings
                self.converter.TARGET_MIN_BYTES = original_target_min
                self.converter.TARGET_MAX_BYTES = original_target_max
                self.converter.TARGET_MIN_MB = original_target_min_mb
                self.converter.TARGET_MAX_MB = original_target_max_mb
            
            self.update_status("Custom Conversion Complete!")
            
        except Exception as e:
            self.log_queue.put(f"Error: {str(e)}")
            self.update_status(f"Error: {str(e)}")
        
        finally:
            # Re-enable buttons
            self.window.after(0, lambda: self.convert_btn.state(['!disabled']))
            self.window.after(0, lambda: self.thumb_btn.state(['!disabled']))
            self.window.after(0, lambda: self.custom_btn.state(['!disabled']))
            self.window.after(0, lambda: self.browse_btn.state(['!disabled']))
            self.window.after(0, lambda: self.save_btn.state(['!disabled']))
            self.window.after(0, lambda: self.custom_entry.state(['!disabled']))
            self.window.after(0, lambda: self.progress.stop())
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = GifConverterGUI()
    app.run() 