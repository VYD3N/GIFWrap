import tkinter as tk
from tkinter import ttk, filedialog
from gif_converter import GifConverter
import threading
import os
import queue
import time
from frame_editor import FrameEditor
from moviepy.editor import VideoFileClip
import math
import cv2
import numpy as np
from luma_api import LumaAPI
from datetime import datetime

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
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create GIF Converter tab
        self.gif_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.gif_frame, text="GIF Converter")
        
        # Create Luma AI tab
        self.luma_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.luma_frame, text="AI Video Generator")
        
        # Setup GIF converter tab (move existing widgets to gif_frame)
        self.setup_gif_tab()
        
        # Setup Luma tab
        self.setup_luma_tab()
        
        # Initialize Luma API with callback
        self.luma_api = LumaAPI()
        try:
            self.luma_api.setup_callback(port=5000)
        except Exception as e:
            print(f"Warning: Callback setup failed, falling back to polling: {str(e)}")
        
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
    
    def setup_gif_tab(self):
        # Create main frame
        self.main_frame = ttk.Frame(self.gif_frame, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input file selection
        self.input_frame = ttk.LabelFrame(self.main_frame, text="Input File", padding="5")
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
        
        # Add button to button frame
        self.edit_btn = ttk.Button(
            self.button_frame,
            text="Edit Frames",
            command=self.open_frame_editor
        )
        self.edit_btn.grid(row=1, column=1, padx=5)
        
        # Log area
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Conversion Log", padding="5")
        self.log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = tk.Text(self.log_frame, height=10, width=60)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for log
        self.scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = self.scrollbar.set
        
        # Add FPS selection frame
        self.fps_frame = ttk.LabelFrame(self.main_frame, text="FPS Settings", padding="5")
        self.fps_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # FPS dropdown with added 18 FPS option
        self.fps_var = tk.StringVar(value="12")
        fps_options = ["12", "15", "18", "20", "24", "30"]  # Added 18 FPS
        self.fps_dropdown = ttk.Combobox(
            self.fps_frame, 
            textvariable=self.fps_var,
            values=fps_options,
            width=5,
            state="readonly"
        )
        self.fps_dropdown.grid(row=0, column=0, padx=5)
        ttk.Label(self.fps_frame, text="FPS").grid(row=0, column=1, padx=5)
        
        # Move output frame down
        self.output_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        # Adjust other widget row numbers accordingly...
    
    def setup_luma_tab(self):
        """Setup the Luma AI video generation tab"""
        # Prompt frame
        prompt_frame = ttk.LabelFrame(self.luma_frame, text="Prompt", padding="5")
        prompt_frame.pack(fill='x', pady=5)
        
        self.prompt_var = tk.StringVar()
        self.prompt_entry = ttk.Entry(prompt_frame, textvariable=self.prompt_var, width=60)
        self.prompt_entry.pack(fill='x', padx=5, pady=5)
        
        # Output directory frame
        output_frame = ttk.LabelFrame(self.luma_frame, text="Output Directory", padding="5")
        output_frame.pack(fill='x', pady=5)
        
        self.luma_output_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Videos", "GIFWrap"))
        output_entry = ttk.Entry(output_frame, textvariable=self.luma_output_dir, width=50)
        output_entry.pack(side='left', fill='x', expand=True, padx=5)
        
        def browse_output():
            directory = filedialog.askdirectory(
                title="Select Output Directory",
                initialdir=self.luma_output_dir.get()
            )
            if directory:
                self.luma_output_dir.set(directory)
                # Create directory if it doesn't exist
                os.makedirs(directory, exist_ok=True)
        
        ttk.Button(
            output_frame,
            text="Browse",
            command=browse_output
        ).pack(side='right', padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.luma_frame, text="Generation Options", padding="5")
        options_frame.pack(fill='x', pady=5)
        
        # Ray-2 option
        self.ray2_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Use Ray-2 Model",
            variable=self.ray2_var
        ).pack(anchor='w', padx=5, pady=2)
        
        # Aspect ratio frame (for text generation)
        aspect_frame = ttk.Frame(options_frame)
        aspect_frame.pack(fill='x', pady=2)
        
        ttk.Label(aspect_frame, text="Aspect Ratio:").pack(side='left', padx=5)
        self.aspect_var = tk.StringVar(value="16:9")
        aspect_combo = ttk.Combobox(
            aspect_frame,
            textvariable=self.aspect_var,
            values=["1:1", "3:4", "4:3", "9:16", "16:9", "9:21", "21:9"],
            state="readonly",
            width=10
        )
        aspect_combo.pack(side='left', padx=5)
        
        # Loop option
        self.loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="Loop Video", 
            variable=self.loop_var
        ).pack(anchor='w', padx=5, pady=2)
        
        # Image frames
        self.keyframes_frame = ttk.LabelFrame(self.luma_frame, text="Keyframes (Optional)", padding="5")
        self.keyframes_frame.pack(fill='x', pady=5)
        
        # Start frame
        start_frame = ttk.Frame(self.keyframes_frame)
        start_frame.pack(fill='x', pady=2)
        ttk.Label(start_frame, text="Start Frame:").pack(side='left', padx=5)
        self.start_frame_var = tk.StringVar()
        ttk.Entry(
            start_frame, 
            textvariable=self.start_frame_var, 
            width=40, 
            state='readonly'
        ).pack(side='left', padx=5)
        ttk.Button(
            start_frame,
            text="Browse",
            command=lambda: self.browse_keyframe('start')
        ).pack(side='left', padx=5)
        
        # End frame
        end_frame = ttk.Frame(self.keyframes_frame)
        end_frame.pack(fill='x', pady=2)
        ttk.Label(end_frame, text="End Frame:").pack(side='left', padx=5)
        self.end_frame_var = tk.StringVar()
        ttk.Entry(
            end_frame, 
            textvariable=self.end_frame_var, 
            width=40, 
            state='readonly'
        ).pack(side='left', padx=5)
        ttk.Button(
            end_frame,
            text="Browse",
            command=lambda: self.browse_keyframe('end')
        ).pack(side='left', padx=5)
        
        # Generation buttons
        buttons_frame = ttk.Frame(self.luma_frame)
        buttons_frame.pack(fill='x', pady=10)
        
        ttk.Button(
            buttons_frame,
            text="Generate from Text",
            command=self.generate_from_text
        ).pack(side='left', padx=5)
        
        ttk.Button(
            buttons_frame,
            text="Generate with Keyframes",
            command=self.generate_with_keyframes
        ).pack(side='left', padx=5)
        
        # Status and progress
        self.luma_status_var = tk.StringVar(value="Ready")
        ttk.Label(
            self.luma_frame, 
            textvariable=self.luma_status_var
        ).pack(fill='x', pady=5)
        
        self.luma_progress = ttk.Progressbar(
            self.luma_frame, 
            mode='indeterminate'
        )
        self.luma_progress.pack(fill='x', pady=5)
        
        # Log area
        log_frame = ttk.LabelFrame(self.luma_frame, text="Generation Log", padding="5")
        log_frame.pack(fill='both', expand=True, pady=5)
        
        self.luma_log = tk.Text(log_frame, height=10, width=60)
        self.luma_log.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.luma_log.yview)
        scrollbar.pack(side='right', fill='y')
        self.luma_log['yscrollcommand'] = scrollbar.set
    
    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.wmv"),
                ("All files", "*.*")
            ]
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
        self.disable_buttons()
        
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
        self.disable_buttons()
        
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
        self.disable_buttons()
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start progress bar
        self.progress.start()
        
        # Start conversion in separate thread
        thread = threading.Thread(target=lambda: self.convert_custom(size))
        thread.daemon = True
        thread.start()
    
    def disable_buttons(self):
        self.convert_btn.state(['disabled'])
        self.thumb_btn.state(['disabled'])
        self.custom_btn.state(['disabled'])
        self.browse_btn.state(['disabled'])
        self.save_btn.state(['disabled'])
        self.custom_entry.state(['disabled'])
    
    def enable_buttons(self):
        self.window.after(0, lambda: self.convert_btn.state(['!disabled']))
        self.window.after(0, lambda: self.thumb_btn.state(['!disabled']))
        self.window.after(0, lambda: self.custom_btn.state(['!disabled']))
        self.window.after(0, lambda: self.browse_btn.state(['!disabled']))
        self.window.after(0, lambda: self.save_btn.state(['!disabled']))
        self.window.after(0, lambda: self.custom_entry.state(['!disabled']))
        self.window.after(0, lambda: self.progress.stop())
    
    def convert(self):
        try:
            self.update_status("Converting...")
            
            # Use selected FPS
            fps = float(self.fps_var.get())
            self.converter.MIN_FPS = fps
            self.converter.MAX_FPS = fps
            
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
            self.enable_buttons()
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
            self.enable_buttons()
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
            self.enable_buttons()
    
    def open_frame_editor(self):
        if not self.input_path.get():
            self.status_var.set("Error: Please select an input video")
            return
        
        editor = FrameEditor(self.window, self.input_path.get())
        self.window.wait_window(editor.window)
        
        if hasattr(editor, 'result'):
            # Store selected frames for conversion
            self.selected_frames = editor.result
    
    def generate_from_text(self):
        if not self.prompt_var.get():
            self.luma_status_var.set("Error: Please enter a prompt")
            return
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.luma_output_dir.get(), exist_ok=True)
            
            # Generate unique filename based on prompt
            safe_prompt = "".join(x for x in self.prompt_var.get()[:30] if x.isalnum() or x in (' ', '-', '_'))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"luma_{safe_prompt}_{timestamp}.mp4"
            output_path = os.path.join(self.luma_output_dir.get(), output_filename)
            
            self.disable_buttons()
            self.luma_progress.start()
            self.luma_status_var.set("Starting video generation...")
            self.luma_log.delete(1.0, tk.END)
            
            def log_message(msg):
                self.window.after(0, lambda: self.luma_log.insert(tk.END, f"{msg}\n"))
                self.window.after(0, lambda: self.luma_log.see(tk.END))
            
            def update_status(state):
                status_msg = f"Generation status: {state}"
                self.luma_status_var.set(status_msg)
                log_message(status_msg)
            
            def generate():
                try:
                    log_message("Starting generation...")
                    generation = self.luma_api.generate_video(
                        self.prompt_var.get(),
                        use_ray2=self.ray2_var.get(),
                        aspect_ratio=self.aspect_var.get(),
                        loop=self.loop_var.get()
                    )
                    log_message(f"Generation ID: {generation.get('id')}")
                    
                    generation = self.luma_api.wait_for_generation(
                        generation,
                        callback=update_status
                    )
                    
                    log_message("Downloading video...")
                    self.luma_api.download_video(generation['assets']['video'], output_path)
                    log_message(f"Video saved to: {output_path}")
                    self.luma_status_var.set("Video generation complete!")
                    
                    # Open output directory
                    if os.path.exists(output_path):
                        os.startfile(os.path.dirname(output_path))
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    log_message(f"ERROR: {error_msg}")
                    self.luma_status_var.set(error_msg)
                finally:
                    self.enable_buttons()
                    self.luma_progress.stop()
            
            thread = threading.Thread(target=generate)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.luma_log.insert(tk.END, f"ERROR: {error_msg}\n")
            self.luma_status_var.set(error_msg)
            self.enable_buttons()
            self.luma_progress.stop()
    
    def generate_with_keyframes(self):
        """Generate video with keyframes"""
        if not self.prompt_var.get():
            self.luma_status_var.set("Error: Please enter a prompt")
            return
        
        if not self.start_frame_var.get() and not self.end_frame_var.get():
            self.luma_status_var.set("Error: Please select at least one keyframe")
            return
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.luma_output_dir.get(), exist_ok=True)
            
            # Generate unique filename based on prompt
            safe_prompt = "".join(x for x in self.prompt_var.get()[:30] if x.isalnum() or x in (' ', '-', '_'))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"luma_{safe_prompt}_{timestamp}.mp4"
            output_path = os.path.join(self.luma_output_dir.get(), output_filename)
            
            self.disable_buttons()
            self.luma_progress.start()
            self.luma_status_var.set("Starting generation...")
            self.luma_log.delete(1.0, tk.END)  # Clear log
            
            def log_message(msg):
                self.window.after(0, lambda: self.luma_log.insert(tk.END, f"{msg}\n"))
                self.window.after(0, lambda: self.luma_log.see(tk.END))
            
            def update_status(state):
                status_msg = f"Generation status: {state}"
                self.luma_status_var.set(status_msg)
                log_message(status_msg)
            
            def generate():
                try:
                    log_message("Processing keyframes...")
                    keyframes = {}
                    
                    if self.start_frame_var.get():
                        log_message(f"Processing start frame: {self.start_frame_var.get()}")
                        keyframes['frame0'] = {
                            'type': 'image',
                            'url': self.start_frame_var.get()
                        }
                    
                    if self.end_frame_var.get():
                        log_message(f"Processing end frame: {self.end_frame_var.get()}")
                        keyframes['frame1'] = {
                            'type': 'image',
                            'url': self.end_frame_var.get()
                        }
                    
                    log_message("Starting generation...")
                    generation = self.luma_api.generate_from_image(
                        self.prompt_var.get(),
                        keyframes=keyframes,
                        use_ray2=self.ray2_var.get(),
                        loop=self.loop_var.get()
                    )
                    log_message(f"Generation ID: {generation.get('id')}")
                    
                    generation = self.luma_api.wait_for_generation(
                        generation,
                        callback=update_status
                    )
                    
                    log_message("Downloading video...")
                    self.luma_api.download_video(generation['assets']['video'], output_path)
                    log_message(f"Video saved to: {output_path}")
                    self.luma_status_var.set("Video generation complete!")
                    
                    # Open output directory
                    if os.path.exists(output_path):
                        os.startfile(os.path.dirname(output_path))
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    log_message(f"ERROR: {error_msg}")
                    self.luma_status_var.set(error_msg)
                finally:
                    self.enable_buttons()
                    self.luma_progress.stop()
            
            thread = threading.Thread(target=generate)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.luma_log.insert(tk.END, f"ERROR: {error_msg}\n")
            self.luma_status_var.set(error_msg)
            self.enable_buttons()
            self.luma_progress.stop()
    
    def browse_keyframe(self, frame_type):
        """Browse for keyframe image"""
        filename = filedialog.askopenfilename(
            title=f"Select {frame_type.title()} Frame",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png"),
                ("All files", "*.*")
            ]
        )
        if filename:
            if frame_type == 'start':
                self.start_frame_var.set(filename)
            else:
                self.end_frame_var.set(filename)
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = GifConverterGUI()
    app.run() 