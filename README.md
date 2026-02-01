# Rename_file_GUI

markdown
# Playlist & Batch File Renamer GUI

A simple Python GUI application that lets you **preview, edit, and batch-rename files in any folder**, especially files that contain **numbering, prefixes, or inconsistent naming**.

While commonly used after downloading playlists with tools like **yt-dlp**, this application works with **any numbered files** such as:
- Lecture series
- Audiobooks
- Lessons
- Courses
- Recordings
- Documents or media files

---

## ✨ Features

- 📂 Select **any folder** containing files to rename
- 👀 Live **preview** of renamed filenames before applying changes
- ✏️ Edit filenames **directly from the GUI** (double-click to edit)
- 🔢 Smart handling of numbered filenames
- 🧹 Automatically cleans:
  - Extra spaces
  - Trailing `Copy`
  - Unwanted dashes
- 🧩 Flexible rename templates:
  - `{number}` → detected leading number (e.g. `01`)
  - `{title}` → cleaned filename title
- ✅ Safe batch renaming with confirmation

---

## 🖼 Example

### Before

01 - 1.ADABU ZA KWENDA KATIKA SWALA.mp3
02 - 2.NIA YA SWALA   Copy.mp3

### After

1. ADABU ZA KWENDA KATIKA SWALA.mp3
2. NIA YA SWALA.mp3

Or, using `{title}` only:

1.ADABU ZA KWENDA KATIKA SWALA.mp3

---

## 🛠 Requirements

- Python **3.8+**
- Tkinter (for the GUI)

### Install Tkinter (Linux / Ubuntu / Debian)
bash
sudo apt install python3-tk

> Tkinter is preinstalled on Windows and most macOS Python distributions.

---

## 🚀 Usage

1. Clone the repository:

bash
git clone https://github.com/IanMugwe/Rename_file_GUI.git
cd Rename_file_GUI


2. Run the application:

bash
python3 rename_gui.py


3. In the GUI:

   * Click **Browse** and select any folder
   * Choose or type a rename format:

     * `{number}. {title}`
     * `{title}`
     * `{number} - {title}`
   * Double-click any preview name to edit it manually
   * Click **Rename Files** to apply changes

---

## 🧠 Rename Format Templates

You can customize filenames using placeholders:

| Placeholder | Description                             |
| ----------- | --------------------------------------- |
| `{number}`  | Detected leading number (e.g. `01`)     |
| `{title}`   | Cleaned title without unwanted prefixes |

### Examples

{number}. {title}
{title}
{number} - {title}

---

## ⚠️ Notes

* Files are renamed **in place**
* The preview shows exactly what will be applied
* Already-correct filenames are skipped automatically
* Always review the preview before confirming

---

## 📌 Roadmap / Ideas

* Undo / rollback support
* Drag-and-drop reordering
* Support for more filename patterns
* Multi-folder batch mode
* Packaging as a standalone executable

---

## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome.
Feel free to open an issue or submit a pull request.

---

## 📄 License

MIT License
Free to use, modify, and distribute.

