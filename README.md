# md_replace.py

A powerful command-line tool for find-and-replace operations in markdown files with backup and undo capability.

## Features

- **Recursive search** - Finds all `.md` files in a directory and subdirectories
- **Dry-run mode** - Preview changes before executing
- **Whole-word matching** - Replace only complete words (e.g., `Var` won't match inside `Variance`)
- **Case-insensitive replacement** - Optional case-insensitive matching
- **Automatic backups** - Creates `.backup/` directory with original files
- **Undo functionality** - Restore files to their original state
- **Operation history** - Track all replacements made
- **User confirmation** - Prompts before making changes
- **LaTeX support** - Works with backslash sequences like `\text{rank}`

## Installation

No external dependencies required. Just Python 3.6+

```bash
python3 md_replace.py --help
```

## Usage

### Basic replacement

```bash
python3 md_replace.py ./docs "old text" "new text"
```

### Preview changes first (dry-run)

```bash
python3 md_replace.py ./docs "old text" "new text" --dry-run
```

### Whole-word replacement

Only match complete words, not substrings:

```bash
python3 md_replace.py ./docs "Var" "\mathrm{Var}" --whole-word
```

This will:
- Replace `Var equals 5` → `\mathrm{Var} equals 5` 
- Keep `Variance = 10` unchanged 

### Case-insensitive replacement

```bash
python3 md_replace.py ./docs "OLD" "new" --case-insensitive
```

### Combine options

```bash
python3 md_replace.py ./docs "pattern" "replacement" --whole-word --case-insensitive --dry-run
```

### Undo the last operation

```bash
python3 md_replace.py ./docs --undo
```

Restores all files from the most recent replacement operation.

### List all backup operations

```bash
python3 md_replace.py ./docs --list-backups
```

Shows:
- Search and replacement strings used
- Number of files modified
- Sample files affected

## Examples

### LaTeX mathematical notation

Replace `\text{rank}` with `\mathrm{rank}`:

```bash
python3 md_replace.py /mnt/d/obsidian-vault '\text{rank}' '\mathrm{rank}' --whole-word
```

### Refactor variable names

Replace `oldVar` with `newVariable` throughout your documentation:

```bash
python3 md_replace.py ./docs "oldVar" "newVariable" --dry-run
# Preview changes, then run without --dry-run to execute
python3 md_replace.py ./docs "oldVar" "newVariable"
```

### Fix inconsistent terminology

Replace both uppercase and lowercase variants:

```bash
python3 md_replace.py ./docs "api" "API" --case-insensitive
```

### Bulk link updates

Replace markdown links:

```bash
python3 md_replace.py ./docs "[Old Name](old-link.md)" "[New Name](new-link.md)"
```

## How It Works

### Workflow

1. **Scan** - Recursively finds all `.md` files in the target directory
2. **Preview** - Shows matches found (with `--dry-run` or during confirmation)
3. **Confirm** - Prompts user to confirm before proceeding
4. **Backup** - Creates `.backup/` directory preserving original files
5. **Replace** - Performs replacement on working files
6. **Record** - Saves operation metadata for undo capability

### Backup Structure

Backups are stored in `.backup/` with the same directory structure as originals:

```
docs/
├── file1.md
├── subdir/
│   └── file2.md
└── .backup/
    ├── file1.md
    └── subdir/
        └── file2.md
```

### Undo Mechanism

Each replacement operation is recorded in `.backup/metadata.json`:

```json
{
  "operations": [
    {
      "search": "\\text{rank}",
      "replacement": "\\mathrm{rank}",
      "case_insensitive": false,
      "whole_word": true,
      "files": {
        "MATH/1030/Rank and Nullity.md": 5,
        "STAT/2006/Sample Statistics.md": 2
      }
    }
  ]
}
```

When you run `--undo`, the most recent operation is reversed by restoring files from backup.

## Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without modifying files |
| `--whole-word` | Match only complete words (ignore substrings) |
| `--case-insensitive` | Perform case-insensitive matching |
| `--undo` | Restore files from the last operation |
| `--list-backups` | Show all backup operations |
| `--help` | Display help message |

## Tips & Tricks

### Shell escaping for special characters

When using backslashes (LaTeX), use single quotes to prevent shell interpretation:

```bash
# ✓ Correct - single quotes preserve backslashes
python3 md_replace.py ./docs '\text{Var}' '\mathrm{Var}' --whole-word

# ✗ Wrong - double quotes require double backslashes
python3 md_replace.py ./docs "\\text{Var}" "\\mathrm{Var}" --whole-word
```

### Always use dry-run first

For large batches, always preview first:

```bash
python3 md_replace.py ./docs "search" "replace" --dry-run
# Review the output, then run without --dry-run
python3 md_replace.py ./docs "search" "replace"
```

### Check what changed

After replacement, view backups to see what was changed:

```bash
diff docs/file.md docs/.backup/file.md
```

### Multiple replacements

Run replacements in sequence. Each one can be individually undone:

```bash
python3 md_replace.py ./docs "old1" "new1"
python3 md_replace.py ./docs "old2" "new2"
python3 md_replace.py ./docs --undo  # Undoes "old2" → "new2"
python3 md_replace.py ./docs --undo  # Undoes "old1" → "new1"
```

## Error Handling

The script handles common errors gracefully:

- **File encoding issues** - Skips files that can't be read as UTF-8
- **Permission errors** - Reports which files it couldn't write to
- **Invalid regex patterns** - Escapes all special characters automatically
- **Directory not found** - Exits with clear error message

If a file fails to process, it's skipped and the operation continues with remaining files.

## Requirements

- Python 3.6 or higher
- Write access to target directory
- UTF-8 file encoding (standard for markdown)
