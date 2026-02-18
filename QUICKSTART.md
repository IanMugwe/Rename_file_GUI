# Quick Start Guide - Playlist Renamer Pro

## Installation

### Requirements
- Python 3.11 or higher
- tkinter (included with Python on most systems)
- Operating System: Windows, macOS, or Linux

### Verify Python Installation
```bash
python --version  # Should show 3.11 or higher
```

### Download & Setup
```bash
# Option 1: Download and extract the archive

# Option 2: Clone from repository
# git clone <repository_url>

# Navigate to directory
cd playlist_renamer_pro
```

### Test Installation
```bash
# Run test suite to verify everything works
python test_demo.py
```

You should see all tests passing with green checkmarks.

## First Time Usage

### Step 1: Launch the Application
```bash
python main.py
```

A window will open with the application interface.

### Step 2: Select Your Directory
1. Click the **"Browse..."** button
2. Navigate to the folder containing files you want to rename
3. The directory path will appear in the text field

### Step 3: Configure Options

**Recursive Scan** (optional):
- ☑ Check this to include files in subdirectories
- ☐ Uncheck to only process files in the selected folder

**Dry Run** (recommended for first time):
- ☑ Check this to preview without actually renaming
- ☐ Uncheck to perform actual renames

**Zero Padding:**
- Default: 2 (produces 01, 02, 03...)
- Adjust if you need more digits (001, 002, 003...)

### Step 4: Scan Files
1. Click **"Scan"** button
2. Wait for scan to complete (progress shown in status bar)
3. Review the list of files found
4. Check the statistics: "Files: X | With numbers: Y | Avg confidence: Z"

### Step 5: Choose Format

**Use a Preset:**
- Select from dropdown: "Preset"
- Choose one of the pre-made formats

**Or Enter Custom Format:**
```
{number}. {title}              → 1. Episode Title.mp4
{number:02d}. {title}          → 01. Episode Title.mp4
S{season}E{episode}. {title}   → S01E02. Episode Title.mp4
[{number}] {title}             → [1] Episode Title.mp4
```

### Step 6: Generate Preview
1. Click **"Generate Preview"**
2. Review the preview table showing:
   - Original filenames
   - Extracted numbers
   - Proposed new names
   - Confidence scores

**Warning Signs:**
- Red text or warnings → check for conflicts
- Low confidence (< 0.5) → verify numbers are correct
- Duplicate numbers → may indicate issues

### Step 7: Review Conflicts

If conflicts are detected, you'll see a warning dialog:

**Common Conflicts:**
- **Duplicate target names:** Two files would get the same name
- **Number gaps:** Missing numbers in sequence (e.g., 1, 2, 4, 5)
- **File collisions:** Would overwrite existing files

**How to Fix:**
- Adjust format string
- Manually rename problematic files first
- Use different zero padding

### Step 8: Execute Rename

**Dry Run (Safe):**
1. ☑ Check "Dry run"
2. Click **"Execute Rename"**
3. Confirm dialog
4. Watch progress bar
5. See completion message (no files actually renamed)

**Actual Rename:**
1. ☐ Uncheck "Dry run"
2. Click **"Execute Rename"**
3. **IMPORTANT:** Confirm you've reviewed the preview!
4. Watch progress bar
5. See completion message

### Step 9: Verify Results
1. Navigate to your directory in file explorer
2. Check that files were renamed correctly
3. Review the log file (if enabled)

## Example Workflows

### Workflow 1: TV Show Episodes
**Problem:** Files like "show.s01e05.1080p.web-dl.mp4"
**Solution:**
1. Scan directory
2. Format: `S{season}E{episode}. {title}`
3. Result: "S01E05. Show.mp4"

### Workflow 2: Numbered Tutorials
**Problem:** Files like "Tutorial_Part_12_[1080p].mp4"
**Solution:**
1. Scan directory
2. Format: `{number:02d}. {title}`
3. Result: "12. Tutorial Part.mp4"

### Workflow 3: Podcast Episodes
**Problem:** Files like "MyPodcast-Episode-042-Title-20230815.mp3"
**Solution:**
1. Scan directory
2. Format: `{number:03d}. {title}`
3. Result: "042. MyPodcast Title.mp3"

## Tips & Tricks

### Getting Better Results

**Tip 1: Pre-clean Junk**
If filenames have lots of random text, the parser might struggle.
Consider manually removing obvious junk first.

**Tip 2: Check Confidence Scores**
- High (0.9): Very reliable, go ahead
- Medium (0.6): Usually good, but verify
- Low (0.3): Double-check these numbers

**Tip 3: Use Dry Run First**
Always test with dry run enabled on important files!

**Tip 4: Start Small**
Test on a small subset of files first, then scale up.

**Tip 5: Export Before Renaming**
Click "Export CSV" to save a record of changes.

### Keyboard Shortcuts

- **Browse:** Alt+B (Windows/Linux)
- **Scan:** Alt+S
- **Preview:** Alt+P
- **Execute:** Alt+R

### Handling Special Cases

**Case 1: Files with No Numbers**
These will show "?" in the preview and won't be renamed.
Solution: Manually add numbers to filenames first.

**Case 2: Wrong Numbers Detected**
The parser picked up year (2023) or resolution (1080).
Solution: Review extraction method, possibly clean filename manually.

**Case 3: Duplicate Numbers**
Multiple files have same episode number.
Solution: Review original files - are they actually duplicates?

## Safety Features

### What Protects You

✓ **Two-Phase Commit:** All-or-nothing rename (never half-done)
✓ **Automatic Rollback:** Any failure reverts all changes
✓ **Conflict Detection:** Warns before problems occur
✓ **Dry Run Mode:** Test without risk
✓ **CSV Export:** Document changes before executing
✓ **Audit Logs:** Track all operations

### What to Back Up

**Recommended (for peace of mind):**
- Back up important files before bulk operations
- Test on copies first
- Use version control if available

**The tool is safe, but backups never hurt!**

## Troubleshooting

### Problem: "Permission Denied"
**Cause:** Don't have write access to directory
**Solution:** 
- Check folder permissions
- Run as administrator (Windows) or with sudo (Linux)
- Choose a different directory

### Problem: "No Files Found"
**Cause:** Wrong directory or extension filter
**Solution:**
- Verify correct directory selected
- Check if files have supported extensions
- Try "recursive scan" if files are in subfolders

### Problem: "Operation Failed"
**Cause:** File in use, locked, or disk full
**Solution:**
- Close programs using the files
- Check disk space
- Review error logs: `~/.playlist_renamer/logs/`

### Problem: UI Frozen
**Cause:** Large operation in progress
**Solution:**
- Wait for progress bar to complete
- Use "Cancel" button if needed
- For 10,000+ files, this is normal (may take minutes)

### Problem: Wrong Names Generated
**Cause:** Format string incorrect or parser extracted wrong numbers
**Solution:**
- Review format string syntax
- Check confidence scores in preview
- Adjust format or manually fix source files

## Getting Help

### Check Logs
```bash
# Logs location
~/.playlist_renamer/logs/

# View recent log
cat ~/.playlist_renamer/logs/renamer_<date>.log

# View transaction details
cat ~/.playlist_renamer/logs/transaction_<id>.json
```

### Report Issues

Include:
1. Python version: `python --version`
2. Operating system
3. Sample filenames (anonymized if needed)
4. Error messages from logs
5. Steps to reproduce

## Advanced Usage

### Command Line (for power users)

```python
# Direct API usage (planned feature)
from playlist_renamer import RenamerAPI

api = RenamerAPI()
result = api.rename_directory(
    path="/path/to/files",
    format="{number:02d}. {title}",
    dry_run=True
)
```

### Batch Processing

For multiple directories:
1. Create a shell script
2. Call the application for each directory
3. Use dry-run mode for each batch
4. Review all previews
5. Execute all renames

### Custom Parsers

The architecture supports custom parsers.
See `TECHNICAL.md` for plugin development guide.

## Best Practices

### Before Renaming
- [ ] Back up important files
- [ ] Test on a small sample first
- [ ] Use dry-run mode
- [ ] Export preview to CSV
- [ ] Review conflict warnings
- [ ] Check confidence scores

### During Renaming
- [ ] Monitor progress bar
- [ ] Don't interrupt the operation
- [ ] Don't modify files manually during rename
- [ ] Keep application window visible

### After Renaming
- [ ] Verify results in file explorer
- [ ] Check audit logs
- [ ] Keep logs for reference
- [ ] Test that files still work (play videos, etc.)

## FAQ

**Q: Is this safe for my files?**
A: Yes. The two-phase commit system prevents partial renames, and automatic rollback protects your data. However, always backup important files.

**Q: Can I undo a rename?**
A: Yes. Check the logs directory for transaction records and undo scripts.

**Q: How many files can it handle?**
A: Tested with 10,000+ files. Performance depends on your disk speed.

**Q: What file types are supported?**
A: All file types. Presets exist for video, audio, and documents.

**Q: Can it rename folders?**
A: Currently only files. Folder renaming may be added later.

**Q: Is my data sent anywhere?**
A: No. Everything runs locally on your computer.

**Q: Can I customize the format?**
A: Yes! Use any combination of {number}, {title}, {season}, {episode}.

**Q: What if two files would get the same name?**
A: Conflict detection warns you before renaming. Adjust format to fix.

## Quick Reference

### Format Placeholders
| Placeholder | What it does |
|------------|--------------|
| `{number}` | Episode/item number |
| `{title}` | Cleaned filename |
| `{season}` | Season number (if detected) |
| `{episode}` | Episode number (if detected) |

### Format Examples
```
{number}. {title}
{number:02d} - {title}
S{season}E{episode} - {title}
[{number:03d}] {title}
```

### File Locations
```
Application: playlist_renamer_pro/main.py
Logs: ~/.playlist_renamer/logs/
Config: ~/.playlist_renamer/config/ (future)
```

---

**Happy Renaming! 🎬🎵📁**
