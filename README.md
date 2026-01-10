# Proiect-Python
b - 1 - grep 
# Grep (Python)

A small grep-like command-line tool that searches for Python `re` regular expressions in files and folders.

It prints:
- **Normal mode:** `file:line:content`
- **Count mode:**  `file:count`

It supports:
- multiple input paths (files and/or folders)
- recursive search
- case-insensitive search
- invert match (NOT)
- counting results per file
- optional colored output / match highlighting
- logging to a file and performance stats

---

## Requirements
- Python 3 (recommended 3.9+)

---

## Run format (general)
```bash
python grep.py <regex> <inputs...> [options]
