import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

# ---------------------------
# Functions
# ---------------------------
def parse_files(folder_path, file_ext=".mp3"):
    files = [f for f in os.listdir(folder_path) if f.endswith(file_ext)]
    parsed = []

    for f in sorted(files):
        name, ext = os.path.splitext(f)

        # Remove trailing "Copy"
        name = re.sub(r'\s*Copy$', '', name, flags=re.IGNORECASE)

        # Normalize spaces
        name = re.sub(r'\s+', ' ', name).strip()

        # Match outer number + dash, then keep the rest
        match = re.match(r'^(0*\d+)\s*-\s*(.+)$', name)
        if match:
            outer_number = match.group(1)
            title = match.group(2).strip()

            # 🚀 Remove any leading dash left behind
            title = re.sub(r'^-\s*', '', title)

            parsed.append({
                "original": f,
                "number": outer_number,
                "title": title,
                "ext": ext
            })

    return parsed


def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_path_var.set(folder)
        refresh_preview()

def refresh_preview(*args):
    folder = folder_path_var.get()
    fmt = format_var.get()
    tree.delete(*tree.get_children())
    if not os.path.isdir(folder):
        return
    files_data = parse_files(folder)
    previews.clear()
    for fdata in files_data:
        try:
            new_name = fmt.format(number=fdata["number"], title=fdata["title"]) + fdata["ext"]
        except Exception:
            new_name = f"{fdata['number']} - {fdata['title']}{fdata['ext']}"
        previews[fdata["original"]] = new_name
        tree.insert("", tk.END, values=(fdata["original"], new_name))

def apply_rename():
    folder = folder_path_var.get()
    if not os.path.isdir(folder):
        messagebox.showerror("Error", "Please select a valid folder.")
        return
    for old_name, new_name in previews.items():
        old_path = os.path.join(folder, old_name)
        new_path = os.path.join(folder, new_name)
        if old_path != new_path:
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename {old_name}: {e}")
    messagebox.showinfo("Done", "Files renamed successfully!")
    refresh_preview()

# ---------------------------
# GUI
# ---------------------------
root = tk.Tk()
root.title("Playlist Renamer")

folder_path_var = tk.StringVar()
# format_var = tk.StringVar(value="{number} - {title}")
format_var = tk.StringVar(value="{number}. {title}")

previews = {}

# Folder selection
folder_frame = tk.Frame(root)
folder_frame.pack(fill="x", padx=10, pady=5)
tk.Label(folder_frame, text="Folder:").pack(side="left")
tk.Entry(folder_frame, textvariable=folder_path_var, width=50).pack(side="left", padx=5)
tk.Button(folder_frame, text="Browse", command=select_folder).pack(side="left")

# Format input
format_frame = tk.Frame(root)
format_frame.pack(fill="x", padx=10, pady=5)
tk.Label(format_frame, text="Format:").pack(side="left")
fmt_entry = tk.Entry(format_frame, textvariable=format_var, width=30)
fmt_entry.pack(side="left", padx=5)
format_var.trace_add("write", refresh_preview)

tk.Label(format_frame, text="Use {number} and {title}").pack(side="left")

# Treeview for preview
tree = ttk.Treeview(root, columns=("Original", "Preview"), show="headings", height=15)
tree.heading("Original", text="Original Filename")
tree.heading("Preview", text="Preview New Filename")
tree.pack(fill="both", padx=10, pady=5, expand=True)

# Rename button
tk.Button(root, text="Rename Files", command=apply_rename).pack(pady=10)

root.mainloop()

