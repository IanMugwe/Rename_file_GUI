import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import customtkinter as ctk

# ---------------------------
# Functions (UNCHANGED)
# ---------------------------
def parse_files(folder_path, file_ext=".mp3"):
    files = [f for f in os.listdir(folder_path) if f.endswith(file_ext)]
    parsed = []

    for f in sorted(files):
        name, ext = os.path.splitext(f)

        name = re.sub(r'\s*Copy$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+', ' ', name).strip()

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
    previews.clear()

    if not os.path.isdir(folder):
        status_var.set("No valid folder selected")
        return

    files_data = parse_files(folder)
    status_var.set(f"{len(files_data)} files detected")

    for fdata in files_data:
        try:
            new_name = fmt.format(
                number=fdata["number"],
                title=fdata["title"]
            ) + fdata["ext"]
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
                return

    messagebox.showinfo("Done", "Files renamed successfully!")
    refresh_preview()


# ---------------------------
# CTk GUI
# ---------------------------
ctk.set_appearance_mode("System")   # Light / Dark / System
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Playlist Renamer")
root.geometry("900x550")

folder_path_var = tk.StringVar()
format_var = tk.StringVar(value="{number}. {title}")
status_var = tk.StringVar(value="Select a folder")

previews = {}

# ----- Folder Frame -----
folder_frame = ctk.CTkFrame(root)
folder_frame.pack(fill="x", padx=15, pady=(15, 5))

ctk.CTkLabel(folder_frame, text="Folder").pack(side="left", padx=(10, 5))
ctk.CTkEntry(folder_frame, textvariable=folder_path_var, width=420).pack(
    side="left", padx=5
)
ctk.CTkButton(folder_frame, text="Browse", command=select_folder).pack(
    side="left", padx=5
)

# ----- Format Frame -----
format_frame = ctk.CTkFrame(root)
format_frame.pack(fill="x", padx=15, pady=5)

ctk.CTkLabel(format_frame, text="Format").pack(side="left", padx=(10, 5))
ctk.CTkEntry(format_frame, textvariable=format_var, width=260).pack(
    side="left", padx=5
)
ctk.CTkLabel(
    format_frame, text="Use {number} and {title}", text_color="gray"
).pack(side="left", padx=10)

format_var.trace_add("write", refresh_preview)

# ----- Preview Frame -----
preview_frame = ctk.CTkFrame(root)
preview_frame.pack(fill="both", expand=True, padx=15, pady=5)

tree = ttk.Treeview(
    preview_frame,
    columns=("Original", "Preview"),
    show="headings",
    height=15
)
tree.heading("Original", text="Original Filename")
tree.heading("Preview", text="Preview New Filename")
tree.pack(fill="both", expand=True, padx=10, pady=10)

# ----- Actions Frame -----
actions_frame = ctk.CTkFrame(root)
actions_frame.pack(fill="x", padx=15, pady=(5, 15))

ctk.CTkLabel(actions_frame, textvariable=status_var).pack(
    side="left", padx=10
)
ctk.CTkButton(
    actions_frame,
    text="Rename Files",
    command=apply_rename,
    width=160
).pack(side="right", padx=10)

root.mainloop()

