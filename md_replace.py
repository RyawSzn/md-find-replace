#!/usr/bin/env python3
"""
Markdown file find-and-replace utility with undo capability.

Usage:
    python md_replace.py <directory> <search_string> <replacement_string> [--dry-run] [--case-insensitive]
    python md_replace.py <directory> --undo
"""

import argparse
import os
import shutil
import json
import re
from pathlib import Path
from typing import List, Tuple
import sys


class MDReplacer:
    """Handle markdown file replacements with backup and undo."""
    
    BACKUP_DIR = ".backup"
    METADATA_FILE = ".backup/metadata.json"
    
    def __init__(self, directory: str):
        self.directory = Path(directory)
        if not self.directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        if not self.directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        self.backup_root = self.directory / self.BACKUP_DIR
    
    def find_markdown_files(self) -> List[Path]:
        """Recursively find all markdown files in directory."""
        return sorted(self.directory.rglob("*.md"))
    
    def _ensure_backup_dir(self) -> None:
        """Create backup directory if it doesn't exist."""
        self.backup_root.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self) -> dict:
        """Load backup metadata."""
        metadata_path = self.directory / self.METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return json.load(f)
        return {"operations": []}
    
    def _save_metadata(self, metadata: dict) -> None:
        """Save backup metadata."""
        metadata_path = self.directory / self.METADATA_FILE
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def _get_relative_backup_path(self, file_path: Path) -> Path:
        """Get the backup path for a file, preserving directory structure."""
        relative = file_path.relative_to(self.directory)
        return self.backup_root / relative
    
    def dry_run(self, search: str, replacement: str, case_insensitive: bool = False, whole_word: bool = False) -> List[Tuple[str, int]]:
        """Preview changes without modifying files."""
        md_files = self.find_markdown_files()
        results = []
        
        for file_path in md_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if whole_word:
                    pattern = r'(?<![a-zA-Z0-9_])' + re.escape(search) + r'(?![a-zA-Z0-9_])'
                    flags = re.IGNORECASE if case_insensitive else 0
                    count = len(re.findall(pattern, content, flags))
                elif case_insensitive:
                    count = len(re.findall(re.escape(search), content, re.IGNORECASE))
                else:
                    count = content.count(search)
                
                if count > 0:
                    rel_path = file_path.relative_to(self.directory)
                    results.append((str(rel_path), count))
            except Exception as e:
                print(f"  ⚠️  Error reading {file_path}: {e}")
        
        return results
    
    def execute_replacement(self, search: str, replacement: str, case_insensitive: bool = False, whole_word: bool = False) -> Tuple[int, int, int]:
        """Execute find-and-replace on all markdown files."""
        self._ensure_backup_dir()
        md_files = self.find_markdown_files()
        
        files_modified = 0
        total_replacements = 0
        files_skipped = 0
        operation_record = {
            "search": search,
            "replacement": replacement,
            "case_insensitive": case_insensitive,
            "whole_word": whole_word,
            "files": {}
        }
        
        for file_path in md_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    original_content = f.read()
                
                if whole_word:
                    pattern = r'(?<![a-zA-Z0-9_])' + re.escape(search) + r'(?![a-zA-Z0-9_])'
                    flags = re.IGNORECASE if case_insensitive else 0
                    new_content = re.sub(pattern, lambda m: replacement, original_content, flags=flags)
                    count = len(re.findall(pattern, original_content, flags=flags))
                elif case_insensitive:
                    new_content = re.sub(
                        re.escape(search),
                        lambda m: replacement,
                        original_content,
                        flags=re.IGNORECASE
                    )
                    count = len(re.findall(re.escape(search), original_content, re.IGNORECASE))
                else:
                    new_content = original_content.replace(search, replacement)
                    count = original_content.count(search)
                
                if new_content != original_content:
                    backup_path = self._get_relative_backup_path(file_path)
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(backup_path, "w", encoding="utf-8") as f:
                        f.write(original_content)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    
                    files_modified += 1
                    total_replacements += count
                    rel_path = str(file_path.relative_to(self.directory))
                    operation_record["files"][rel_path] = count
                    print(f"  ✓ {rel_path}: {count} replacement(s)")
                else:
                    files_skipped += 1
            except Exception as e:
                print(f"  ✗ Error processing {file_path}: {e}")
                files_skipped += 1
        
        if files_modified > 0:
            metadata = self._load_metadata()
            metadata["operations"].append(operation_record)
            self._save_metadata(metadata)
        
        return files_modified, total_replacements, files_skipped
    
    def undo_last(self) -> Tuple[bool, str]:
        """Undo the last replacement operation."""
        metadata = self._load_metadata()
        
        if not metadata["operations"]:
            return False, "No operations to undo."
        
        last_op = metadata["operations"].pop()
        search = last_op["search"]
        replacement = last_op["replacement"]
        files_restored = 0
        
        for file_rel_path, count in last_op["files"].items():
            try:
                file_path = self.directory / file_rel_path
                backup_path = self._get_relative_backup_path(file_path)
                
                if backup_path.exists():
                    shutil.copy2(backup_path, file_path)
                    files_restored += 1
                    print(f"  ✓ Restored {file_rel_path}")
                else:
                    print(f"  ⚠️  Backup not found for {file_rel_path}")
            except Exception as e:
                print(f"  ✗ Error restoring {file_rel_path}: {e}")
        
        # Save updated metadata
        self._save_metadata(metadata)
        
        msg = f"Undo successful. Restored {files_restored} file(s). Reversed: '{search}' → '{replacement}'"
        return True, msg
    
    def list_backups(self) -> str:
        """List all backup operations."""
        metadata = self._load_metadata()
        
        if not metadata["operations"]:
            return "No backup operations found."
        
        msg = "Backup operations (most recent first):\n"
        for i, op in enumerate(reversed(metadata["operations"]), 1):
            msg += f"\n  [{i}] '{op['search']}' → '{op['replacement']}'\n"
            msg += f"      Files modified: {len(op['files'])}\n"
            for file_path, count in list(op['files'].items())[:3]:
                msg += f"        - {file_path} ({count}x)\n"
            if len(op['files']) > 3:
                msg += f"        ... and {len(op['files']) - 3} more\n"
        
        return msg


def main():
    parser = argparse.ArgumentParser(
        description="Find and replace in markdown files with undo capability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes (dry-run)
  python md_replace.py ./docs "old text" "new text" --dry-run
  
  # Execute replacement
  python md_replace.py ./docs "old text" "new text"
  
  # Whole-word replacement (only exact word matches, not substrings)
  python md_replace.py ./docs "Var" "\\mathrm{Var}" --whole-word
  
  # Undo last operation
  python md_replace.py ./docs --undo
  
  # List all backups
  python md_replace.py ./docs --list-backups
  
  # Case-insensitive replacement
  python md_replace.py ./docs "OLD" "new" --case-insensitive
        """
    )
    
    parser.add_argument("directory", help="Directory containing markdown files")
    parser.add_argument("search", nargs="?", help="String to search for")
    parser.add_argument("replacement", nargs="?", help="String to replace with")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--case-insensitive", action="store_true", help="Case-insensitive replacement")
    parser.add_argument("--whole-word", action="store_true", help="Match whole words only (e.g., 'Var' won't match 'Variance')")
    parser.add_argument("--undo", action="store_true", help="Undo the last operation")
    parser.add_argument("--list-backups", action="store_true", help="List all backup operations")
    
    args = parser.parse_args()
    
    try:
        replacer = MDReplacer(args.directory)
        
        if args.undo:
            print("\n🔄 Undoing last operation...\n")
            success, msg = replacer.undo_last()
            print(f"\n{msg}\n")
            return 0 if success else 1
        
        if args.list_backups:
            print(f"\n📋 {replacer.list_backups()}\n")
            return 0
        
        if not args.search or not args.replacement:
            parser.error("search and replacement strings are required (unless using --undo or --list-backups)")
        
        print(f"\n🔍 Scanning for markdown files in: {args.directory}")
        md_files = replacer.find_markdown_files()
        print(f"Found {len(md_files)} markdown file(s)\n")
        
        if args.dry_run:
            print("📋 DRY RUN - previewing changes:\n")
            results = replacer.dry_run(args.search, args.replacement, args.case_insensitive, args.whole_word)
            
            if not results:
                print("  No matches found.")
            else:
                total = sum(count for _, count in results)
                for file_path, count in results:
                    print(f"  {file_path}: {count} match(es)")
                print(f"\n  Total: {total} replacement(s) in {len(results)} file(s)")
            
            print("\n💡 Run without --dry-run to execute the replacement.\n")
            return 0
        
        results = replacer.dry_run(args.search, args.replacement, args.case_insensitive, args.whole_word)
        if not results:
            print("  ⚠️  No matches found. Nothing to do.\n")
            return 0
        
        total = sum(count for _, count in results)
        print(f"⚠️  This will replace '{args.search}' with '{args.replacement}'")
        print(f"   {total} match(es) in {len(results)} file(s)\n")
        
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print("Cancelled.\n")
            return 0
        
        print("\n✨ Executing replacement...\n")
        files_modified, total_replacements, files_skipped = replacer.execute_replacement(
            args.search, args.replacement, args.case_insensitive, args.whole_word
        )
        
        print(f"\n✅ Done!")
        print(f"   Modified: {files_modified} file(s)")
        print(f"   Replacements: {total_replacements}")
        if files_skipped > 0:
            print(f"   Skipped: {files_skipped} file(s)")
        print(f"   Undo with: python md_replace.py {args.directory} --undo\n")
        
        return 0
    
    except ValueError as e:
        print(f"❌ Error: {e}\n", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.\n", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
