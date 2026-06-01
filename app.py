"""
AI File Organizer - Flask Web Application
Provides a modern UI for reviewing and organizing files.
"""

import os
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, jsonify
from pathlib import Path

from organizer_lib import FileOrganizer

app = Flask(__name__)
organizer = FileOrganizer()

# Default to script directory
DEFAULT_DIR = str(Path(__file__).parent.resolve())


@app.route('/')
def index():
    """Serve the main UI."""
    return render_template('index.html')


@app.route('/api/scan', methods=['POST'])
def scan_files():
    """Scan a directory for files and optionally folders."""
    data = request.get_json()
    directory = data.get('directory', DEFAULT_DIR)
    recursive = data.get('recursive', False)
    include_folders = data.get('include_folders', False)
    folders_only = data.get('folders_only', False)
    
    try:
        organizer.set_target_directory(directory)
        result = organizer.scan_files(recursive=recursive, include_folders=include_folders, folders_only=folders_only)
        return jsonify({
            "success": True, 
            "files": result["files"], 
            "folders_to_organize": result.get("folders_to_organize", []),
            "existing_folders": result["folders"],
            "directory": str(organizer.target_dir)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/suggest', methods=['POST'])
def get_suggestions():
    """Get AI suggestions for file categories."""
    data = request.get_json()
    files = data.get('files', [])
    existing_folders = data.get('folders', [])
    custom_instruction = data.get('instruction', '')
    suggest_rename = data.get('rename', False)
    
    try:
        files_with_suggestions = organizer.get_ai_suggestions(
            files, 
            existing_folders=existing_folders,
            custom_instruction=custom_instruction,
            suggest_rename=suggest_rename
        )
        return jsonify({"success": True, "files": files_with_suggestions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/organize', methods=['POST'])
def organize_files():
    """Move files to their categories."""
    data = request.get_json()
    files = data.get('files', [])
    
    try:
        results = organizer.organize_files(files)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/undo', methods=['POST'])
def undo_organization():
    """Undo the last organization."""
    try:
        results = organizer.undo_organization()
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    """Chat with AI about file organization."""
    data = request.get_json()
    message = data.get('message', '')
    files = data.get('files', [])
    existing_folders = data.get('existing_folders', [])
    directory = data.get('directory', '')
    
    try:
        response = organizer.chat(message, files, existing_folders, directory)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/browse-folder', methods=['POST'])
def browse_folder():
    """Open native Windows folder picker dialog."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Create a hidden root window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Bring dialog to front
        
        # Open folder dialog
        folder_path = filedialog.askdirectory(
            title="Select Folder to Organize",
            initialdir=DEFAULT_DIR
        )
        
        root.destroy()
        
        if folder_path:
            return jsonify({"success": True, "path": folder_path})
        else:
            return jsonify({"success": False, "error": "No folder selected"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/default-directory')
def get_default_directory():
    """Return the default directory path."""
    return jsonify({"directory": DEFAULT_DIR})


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current AI provider settings."""
    try:
        pm = organizer.get_provider_manager()
        return jsonify({"success": True, "settings": pm.get_current_settings()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update AI provider settings."""
    data = request.get_json()
    
    try:
        pm = organizer.get_provider_manager()
        result = pm.update_settings(
            provider=data.get('provider'),
            model=data.get('model'),
            api_key=data.get('api_key'),
            custom_base_url=data.get('custom_base_url')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/providers')
def get_providers():
    """Get list of available AI providers."""
    try:
        pm = organizer.get_provider_manager()
        return jsonify({"success": True, "providers": pm.get_providers()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/models/<provider_id>')
def get_models(provider_id):
    """Get models for a specific provider (fetched dynamically from API)."""
    try:
        pm = organizer.get_provider_manager()
        # Get API key from query params if provided (for fetching before saving)
        api_key = request.args.get('api_key')
        models = pm.get_models(provider_id, api_key=api_key)
        return jsonify({"success": True, "models": models})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test the current AI provider connection."""
    try:
        pm = organizer.get_provider_manager()
        result = pm.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


def open_browser():
    """Open browser after server starts."""
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    # Open browser after a short delay
    Timer(1.5, open_browser).start()
    print("\n" + "="*50)
    print("   AI File Sorter - Web UI")
    print("="*50)
    print(f"\n   Opening browser at: http://127.0.0.1:5000")
    print(f"   Default directory: {DEFAULT_DIR}")
    print("\n   Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    app.run(debug=False, port=5000)
