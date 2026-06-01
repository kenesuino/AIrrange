"""
AI File Sorter - Core Library
Handles file scanning, AI API calls, and file operations.
Supports multiple AI providers: Gemini, OpenAI, OpenRouter, xAI
"""

import os
import json
import shutil
import csv
from datetime import datetime
from pathlib import Path

from providers import ProviderManager


class FileOrganizer:
    def __init__(self, config_path: str = None):
        """Initialize the organizer with configuration."""
        if config_path is None:
            config_path = Path(__file__).parent / "config.json"
        
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.target_dir = None
        self.log_file = None
        self.learning_file = None
        
        # Initialize AI provider manager
        self.provider_manager = ProviderManager(str(config_path))
    
    def get_provider_manager(self) -> ProviderManager:
        """Get the provider manager for settings access."""
        return self.provider_manager
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def set_target_directory(self, directory: str):
        """Set the directory to organize."""
        self.target_dir = Path(directory).resolve()
        self.log_file = self.target_dir / "organization_log.csv"
        
        if not self.target_dir.exists():
            raise ValueError(f"Directory does not exist: {directory}")
    
    def scan_files(self, recursive: bool = False, include_folders: bool = False, folders_only: bool = False) -> dict:
        """Scan directory for items to organize.
        
        Args:
            recursive: If True, scan subdirectories too.
            include_folders: If True, include folders as items to organize.
            folders_only: If True, ONLY scan folders, ignore files.
            
        Returns:
            dict with 'files', 'folders' (existing), and 'folders_to_organize' lists
        """
        if not self.target_dir:
            raise ValueError("Target directory not set")
        
        exclude_ext = set(self.config.get("excludeExtensions", []))
        exclude_names = {"organization_log.csv", "config.json", "app.py", 
                        "organizer_lib.py", "requirements.txt", "__pycache__",
                        "static", "templates", ".git", ".gemini", "node_modules",
                        "venv", ".env"}
        
        files = []
        folders = []
        folders_to_organize = []
        
        # Get existing folders for AI context
        for item in self.target_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                folders.append(item.name)
                
                # Add to folders_to_organize if requested
                if (include_folders or folders_only) and item.name not in exclude_names:
                    folder_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    folders_to_organize.append({
                        "name": item.name,
                        "path": str(item),
                        "relative_path": item.name,
                        "size": folder_size,
                        "extension": "",
                        "category": None,
                        "new_name": None,
                        "action": "skip",  # Default to skip for folders (safety)
                        "isFolder": True
                    })
        
        # If folders_only, return early
        if folders_only:
            return {"files": [], "folders": folders, "folders_to_organize": folders_to_organize}
        
        # Scan files
        if recursive:
            # Recursive scan
            for item in self.target_dir.rglob('*'):
                if item.is_file():
                    if item.suffix.lower() not in exclude_ext and item.name not in exclude_names:
                        rel_path = item.relative_to(self.target_dir)
                        files.append({
                            "name": item.name,
                            "path": str(item),
                            "relative_path": str(rel_path),
                            "size": item.stat().st_size,
                            "extension": item.suffix.lower(),
                            "category": None,
                            "new_name": None,
                            "action": "move",
                            "isFolder": False
                        })
        else:
            # Non-recursive scan (original behavior)
            for item in self.target_dir.iterdir():
                if item.is_file():
                    if item.suffix.lower() not in exclude_ext and item.name not in exclude_names:
                        files.append({
                            "name": item.name,
                            "path": str(item),
                            "relative_path": item.name,
                            "size": item.stat().st_size,
                            "extension": item.suffix.lower(),
                            "category": None,
                            "new_name": None,
                            "action": "move",
                            "isFolder": False
                        })
        
        return {"files": files, "folders": folders, "folders_to_organize": folders_to_organize}
    
    def get_ai_suggestions(self, files: list[dict], existing_folders: list[str] = None,
                           custom_instruction: str = "", suggest_rename: bool = False) -> list[dict]:
        """Get AI suggestions for file categories and optionally new names.
        
        Args:
            files: List of file dicts to categorize
            existing_folders: List of folder names to prioritize
            custom_instruction: User's custom instructions for the AI
            suggest_rename: If True, AI will suggest new filenames
        """
        if not files:
            return files
        
        # Prepare file list with type indicators
        file_list_str = ""
        for f in files:
            type_tag = "[FOLDER]" if f.get("isFolder") else "[FILE]"
            file_list_str += f"{type_tag} {f['name']}\n"
        
        # Build dynamic prompt
        folder_context = ""
        if existing_folders:
            folder_context = f"\n**EXISTING FOLDERS** (Prioritize these when appropriate): {', '.join(existing_folders)}"
        
        instruction_context = ""
        if custom_instruction.strip():
            instruction_context = f"\n**USER INSTRUCTIONS** (Follow these carefully): {custom_instruction}"
        
        rename_instruction = ""
        rename_format = '"folder": "FolderName"'
        if suggest_rename:
            rename_instruction = "\n5. Also suggest a cleaner filename if the original is messy (e.g., 'IMG_001.jpg' -> 'Beach_Sunset.jpg')."
            rename_format = '"folder": "FolderName", "new_name": "CleanerName.ext" (or null if no rename needed)'

        prompt = f"""You are an intelligent file organizer assistant.
{instruction_context}
{folder_context}

**TASK**: Analyze these items and suggest organization.

**RULES**:
1. Return ONLY valid JSON. No markdown, no explanations.
2. Format: {{"OriginalName": {{{rename_format}}}, ...}}
3. **CRITICAL FOR FOLDERS**: 
   - If a [FOLDER] is already a good category (e.g., 'Finance', 'Images', 'Work'), DO NOT move it. Return "SKIP" as the folder.
   - Only suggest moving a [FOLDER] if it clearly belongs inside another (e.g., [FOLDER] '2023_Receipts' -> 'Finance').
   - NEVER suggest moving a folder into itself.
4. **FOR FILES**:
   - Group logical sets.
   - If unclear/misc, use "Misc".
   - If the file is already in a correct folder logic, you can return "SKIP".
{rename_instruction}

**ITEMS TO ORGANIZE**:
{file_list_str}"""

        try:
            text = self.provider_manager.generate(prompt)
            text = text.strip()
            
            # Clean markdown code blocks if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            suggestions = json.loads(text)
            
            # Apply suggestions to files
            for file in files:
                if file["name"] in suggestions:
                    suggestion = suggestions[file["name"]]
                    
                    # Handle dictionary response
                    if isinstance(suggestion, dict):
                        category = suggestion.get("folder", "Misc")
                        new_name = suggestion.get("new_name")
                    else:
                        # Legacy format: just folder name
                        category = suggestion
                        new_name = None
                    
                    # Check for SKIP command
                    if category == "SKIP" or category == file["name"]:
                        file["action"] = "skip"
                        file["category"] = None
                    else:
                        file["category"] = category
                        file["new_name"] = new_name
                        file["action"] = "move"
                        
                else:
                    # Fallback: Files go to Misc, Folders are SKIPPED (safest default)
                    if file.get("isFolder"):
                        file["action"] = "skip"
                        file["category"] = None
                    else:
                        file["category"] = "Misc"
                        file["action"] = "move"
            
            return files
            
        except Exception as e:
            print(f"AI Error: {e}")
            # Fallback: assign Misc to all
            for file in files:
                file["category"] = "Misc"
            return files
    
    # Log schema (current format). Older logs used only the last three columns.
    LOG_HEADER = ["BatchId", "Date", "Source", "Destination", "Status"]

    def _read_log(self) -> list[dict]:
        """Read the organization log, normalizing legacy (3-column) rows.

        Returns a list of dicts with keys: BatchId, Date, Source, Destination,
        Status. Legacy rows (without BatchId/Status) are assigned to a single
        'legacy' batch with Status 'moved'.
        """
        if not self.log_file or not self.log_file.exists():
            return []

        with open(self.log_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            is_legacy = "BatchId" not in fieldnames

            rows = []
            for row in reader:
                if is_legacy:
                    rows.append({
                        "BatchId": "legacy",
                        "Date": row.get("Date", ""),
                        "Source": row.get("Source", ""),
                        "Destination": row.get("Destination", ""),
                        "Status": "moved",
                    })
                else:
                    rows.append({
                        "BatchId": row.get("BatchId", "legacy"),
                        "Date": row.get("Date", ""),
                        "Source": row.get("Source", ""),
                        "Destination": row.get("Destination", ""),
                        "Status": row.get("Status", "moved"),
                    })
            return rows

    def _write_log(self, rows: list[dict]):
        """Write the full log back in the current schema."""
        with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.LOG_HEADER)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in self.LOG_HEADER})

    def _new_batch_id(self) -> str:
        """Generate a unique batch id for one organize operation."""
        return datetime.now().strftime("%Y%m%d%H%M%S%f")

    def organize_files(self, files: list[dict]) -> dict:
        """Move files to their designated categories, optionally renaming them."""
        batch_id = self._new_batch_id()
        results = {
            "success": [],
            "skipped": [],
            "errors": [],
            "batch_id": batch_id,
        }

        # Read existing log (migrates legacy format in memory) and append new rows.
        log_rows = self._read_log()

        for file in files:
            if file.get("action") == "skip":
                results["skipped"].append(file["name"])
                continue

            source = Path(file["path"])
            category = self._sanitize_folder_name(file.get("category", "Misc"))
            target_folder = self.target_dir / category

            # Use new_name if provided, otherwise keep original name
            final_name = file.get("new_name") or file["name"]
            final_name = self._sanitize_filename(final_name)
            destination = target_folder / final_name

            try:
                # Create folder if needed
                target_folder.mkdir(exist_ok=True)

                # Handle collision
                destination = self._get_unique_path(destination)

                # Move file (and rename if new_name was provided)
                shutil.move(str(source), str(destination))

                # Record operation
                log_rows.append({
                    "BatchId": batch_id,
                    "Date": datetime.now().isoformat(),
                    "Source": str(source),
                    "Destination": str(destination),
                    "Status": "moved",
                })

                result_entry = {
                    "name": file["name"],
                    "category": category,
                    "destination": str(destination)
                }
                if file.get("new_name"):
                    result_entry["renamed_to"] = final_name

                results["success"].append(result_entry)

            except Exception as e:
                results["errors"].append({
                    "name": file["name"],
                    "error": str(e)
                })

        # Persist the log (rewrites in current schema, migrating legacy rows).
        self._write_log(log_rows)

        return results

    def get_history(self) -> list[dict]:
        """Return organization history grouped by batch, newest batch first."""
        rows = self._read_log()
        if not rows:
            return []

        batches = {}
        order = []
        for row in rows:
            bid = row["BatchId"]
            if bid not in batches:
                batches[bid] = {
                    "batch_id": bid,
                    "date": row["Date"],
                    "operations": [],
                }
                order.append(bid)
            batches[bid]["operations"].append({
                "source": row["Source"],
                "destination": row["Destination"],
                "name": Path(row["Destination"]).name,
                "status": row["Status"],
            })

        result = []
        for bid in order:
            batch = batches[bid]
            ops = batch["operations"]
            batch["count"] = len(ops)
            batch["undone_count"] = sum(1 for o in ops if o["status"] == "undone")
            result.append(batch)

        # Newest first
        result.reverse()
        return result

    def undo_operations(self, destinations: list[str]) -> dict:
        """Undo specific operations identified by their destination paths.

        Moves each file back to its original source, marks the matching log row
        'undone', and removes folders left empty. Does not overwrite an existing
        file at the original source.
        """
        results = {
            "restored": [],
            "errors": [],
            "folders_removed": [],
        }

        if not self.log_file or not self.log_file.exists():
            return {"error": "No log file found"}

        rows = self._read_log()
        if not rows:
            return {"error": "No operations to undo"}

        targets = set(destinations)
        folders_to_check = set()

        for row in rows:
            if row["Destination"] not in targets or row["Status"] != "moved":
                continue

            source = Path(row["Source"])
            destination = Path(row["Destination"])

            if not destination.exists():
                results["errors"].append(f"File not found: {destination}")
                continue

            if source.exists():
                results["errors"].append(
                    f"Cannot restore {destination.name}: '{source}' already exists"
                )
                continue

            try:
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(source))
                row["Status"] = "undone"
                results["restored"].append(source.name)
                folders_to_check.add(destination.parent)
            except Exception as e:
                results["errors"].append(f"Failed to restore {destination.name}: {e}")

        # Remove empty folders left behind
        for folder in folders_to_check:
            if folder.exists() and folder != self.target_dir and not any(folder.iterdir()):
                try:
                    folder.rmdir()
                    results["folders_removed"].append(folder.name)
                except Exception:
                    pass

        # Persist updated statuses
        self._write_log(rows)

        return results

    def undo_batch(self, batch_id: str) -> dict:
        """Undo all still-active operations in a given batch."""
        rows = self._read_log()
        destinations = [
            r["Destination"] for r in rows
            if r["BatchId"] == batch_id and r["Status"] == "moved"
        ]
        if not destinations:
            return {"error": "No operations to undo in this batch"}
        return self.undo_operations(destinations)
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid characters from filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        return name.strip() or "unnamed"
    
    def undo_organization(self) -> dict:
        """Undo the most recent active batch of operations."""
        history = self.get_history()
        # get_history is newest-first; find the first batch with active operations
        for batch in history:
            if batch["count"] - batch["undone_count"] > 0:
                return self.undo_batch(batch["batch_id"])
        return {"error": "No operations to undo"}
    
    def _sanitize_folder_name(self, name: str) -> str:
        """Remove invalid characters from folder name."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        return name.strip() or "Misc"
    
    def _get_unique_path(self, path: Path) -> Path:
        """Get a unique path if file already exists."""
        if not path.exists():
            return path
        
        counter = 1
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    def chat(self, message: str, files: list[dict], existing_folders: list[str], 
             directory: str) -> str:
        """Chat with AI about file organization.
        
        Args:
            message: User's chat message
            files: List of file/folder dicts
            existing_folders: List of existing folder names
            directory: Current directory path
            
        Returns:
            AI response string
        """
        # Build context
        file_count = len([f for f in files if not f.get('isFolder')])
        folder_count = len([f for f in files if f.get('isFolder')])
        file_types = {}
        for f in files:
            if not f.get('isFolder'):
                ext = f.get('extension', 'unknown')
                file_types[ext] = file_types.get(ext, 0) + 1
        
        types_summary = ', '.join([f"{count} {ext}" for ext, count in 
                                   sorted(file_types.items(), key=lambda x: -x[1])[:5]])
        
        prompt = f"""You are an intelligent file organization assistant. Help the user with their question about organizing files.

**CURRENT CONTEXT:**
- Directory: {directory}
- Total files: {file_count}
- Total folders: {folder_count}
- File types: {types_summary}
- Existing folders: {', '.join(existing_folders[:10]) if existing_folders else 'None'}

**SAMPLE FILES (first 10):**
{chr(10).join([f"- {f['name']}" for f in files[:10]])}

**USER MESSAGE:**
{message}

**INSTRUCTIONS:**
- Be helpful and conversational
- Give specific, actionable advice
- Reference actual files/folders when possible
- Keep responses concise but informative
- Use markdown formatting for clarity
- If they ask to organize, suggest using the "Get AI Suggestions" button
"""
        
        try:
            return self.provider_manager.generate(prompt)
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
