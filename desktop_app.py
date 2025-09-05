#!/usr/bin/env python3
"""
Desktop application for Braille Card Generator using tkinter.
This provides a native desktop experience for users who prefer not to use web browsers.

Note: This desktop script is experimental/unmaintained and not wired to Liblouis
translation tables in Python. The recommended and supported path is the web app
via `backend.py` (local) or Vercel.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import webbrowser
import os
import sys
import subprocess
import platform
from pathlib import Path
import tempfile
import json

# Import the backend functionality
try:
    from backend import translate_with_liblouis, create_braille_mesh
except ImportError:
    # If backend.py is not in the same directory, we'll need to handle this
    print("Warning: backend.py not found. Some features may not work.")

class BrailleCardGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Braille Card Generator")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Set up the main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(3, weight=1)
        
        self.setup_ui()
        self.setup_styles()
        
    def setup_styles(self):
        """Set up custom styles for the application."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Info.TLabel', font=('Arial', 9))
        
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_label = ttk.Label(self.main_frame, text="Braille Card Generator", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Info panel
        info_frame = ttk.LabelFrame(self.main_frame, text="About", padding="10")
        info_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        info_text = """This application generates 3D printable braille business cards.
        
Card Specifications:
• Size: 3.5 in × 2 in (90mm × 52mm)
• Thickness: 2.0mm
• Grid: 13 columns × 4 rows
• Braille Grade: UEB Grade 1 (uncontracted) or Grade 2 (contracted)

The generated STL file can be 3D printed to create tactile braille business cards."""
        
        info_label = ttk.Label(info_frame, text=info_text, style='Info.TLabel', justify=tk.LEFT)
        info_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Grade selection
        grade_frame = ttk.LabelFrame(self.main_frame, text="Braille Grade", padding="10")
        grade_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.grade_var = tk.StringVar(value="g2")
        ttk.Radiobutton(grade_frame, text="Grade 2 (Contracted) - Recommended", 
                       variable=self.grade_var, value="g2").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(grade_frame, text="Grade 1 (Uncontracted)", 
                       variable=self.grade_var, value="g1").grid(row=1, column=0, sticky=tk.W)
        
        # Text input section
        input_frame = ttk.LabelFrame(self.main_frame, text="Card Text (Up to 4 lines)", padding="10")
        input_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        input_frame.columnconfigure(1, weight=1)
        
        # Line inputs
        self.line_vars = []
        for i in range(4):
            ttk.Label(input_frame, text=f"Line {i+1}:").grid(row=i, column=0, sticky=tk.W, padx=(0, 10))
            var = tk.StringVar()
            self.line_vars.append(var)
            entry = ttk.Entry(input_frame, textvariable=var, width=50)
            entry.grid(row=i, column=1, sticky=(tk.W, tk.E), pady=2)
        
        # Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        self.generate_btn = ttk.Button(button_frame, text="Generate STL", command=self.generate_stl)
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_web_btn = ttk.Button(button_frame, text="Open Web Version", command=self.open_web_version)
        self.open_web_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.help_btn = ttk.Button(button_frame, text="Help", command=self.show_help)
        self.help_btn.pack(side=tk.LEFT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def generate_stl(self):
        """Generate the STL file."""
        # Get input values
        lines = [var.get().strip() for var in self.line_vars]
        grade = self.grade_var.get()
        
        # Validate input
        if all(not line for line in lines):
            messagebox.showerror("Error", "Please enter text in at least one line.")
            return
        
        # Check line lengths
        for i, line in enumerate(lines):
            if line and len(line) > 50:
                messagebox.showerror("Error", f"Line {i+1} is too long. Please keep it under 50 characters.")
                return
        
        # Start generation in a separate thread
        self.generate_btn.config(state='disabled')
        self.status_var.set("Generating STL file...")
        
        thread = threading.Thread(target=self._generate_stl_thread, args=(lines, grade))
        thread.daemon = True
        thread.start()
        
    def _generate_stl_thread(self, lines, grade):
        """Generate STL in a separate thread."""
        try:
            # Import backend functions
            from backend import create_braille_mesh
            
            # Create the mesh
            mesh = create_braille_mesh(lines, grade)
            
            # Ask user where to save the file
            filename = self._get_save_filename()
            if not filename:
                return
            
            # Export to STL
            mesh.export(filename, file_type='stl')
            
            # Show success message
            self.root.after(0, lambda: self._show_success(filename))
            
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))
        finally:
            self.root.after(0, lambda: self._reset_ui())
    
    def _get_save_filename(self):
        """Get the filename from the user."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".stl",
            filetypes=[("STL files", "*.stl"), ("All files", "*.*")],
            title="Save STL file as"
        )
        return filename
    
    def _show_success(self, filename):
        """Show success message."""
        messagebox.showinfo("Success", f"STL file generated successfully!\n\nSaved to: {filename}")
        self.status_var.set("STL file generated successfully")
    
    def _show_error(self, error_msg):
        """Show error message."""
        messagebox.showerror("Error", f"Failed to generate STL file:\n\n{error_msg}")
        self.status_var.set("Error generating STL file")
    
    def _reset_ui(self):
        """Reset the UI after generation."""
        self.generate_btn.config(state='normal')
    
    def open_web_version(self):
        """Open the web version of the application."""
        try:
            # Start the Flask server if not already running
            if not self._is_server_running():
                self._start_server()
            
            # Open the web browser
            webbrowser.open('http://localhost:5001')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open web version:\n\n{str(e)}")
    
    def _is_server_running(self):
        """Check if the Flask server is running."""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 5001))
            sock.close()
            return result == 0
        except:
            return False
    
    def _start_server(self):
        """Start the Flask server in a separate thread."""
        def run_server():
            try:
                from backend import app
                app.run(debug=False, port=5001, use_reloader=False)
            except Exception as e:
                print(f"Server error: {e}")
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
    
    def show_help(self):
        """Show help information."""
        help_text = """Braille Card Generator Help

How to Use:
1. Select the braille grade (Grade 2 is recommended for most users)
2. Enter up to 4 lines of text for your business card
3. Click "Generate STL" to create the 3D model
4. Save the STL file to your computer
5. Use a 3D printer to print the braille card

Tips:
• Grade 2 braille uses contractions and is more space-efficient
• Grade 1 braille spells out each letter (good for learning)
• Each line can contain up to 13 braille cells
• The card size is optimized for 3.5" × 2" business cards

For more information, visit the web version or check the README file."""
        
        help_window = tk.Toplevel(self.root)
        help_window.title("Help")
        help_window.geometry("500x400")
        
        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

def main():
    """Main function to run the application."""
    root = tk.Tk()
    app = BrailleCardGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

