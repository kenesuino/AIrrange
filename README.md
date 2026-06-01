# AIrrange — AI File Sorter

> An intelligent desktop file organizer with a local web UI. Point it at a messy
> folder, let an AI propose where each file should go (and optionally cleaner
> names), review the plan, and apply it — with full per-item undo.

AIrrange runs as a small Flask app on your own machine and opens in your browser.
Your files never leave your computer except for the file **names** sent to your
chosen AI provider for categorization.

---

## What it's for

- **Cleaning up a Downloads / Desktop dump** — sort hundreds of loose files into
  sensible folders (Documents, Images, Invoices, Code, …) in one pass.
- **Consistent naming** — let the AI rename messy files (`IMG_4821.jpg` →
  `Beach_Sunset.jpg`) while it sorts them.
- **Reorganizing into existing structure** — the AI prefers folders you already
  have instead of inventing new ones.
- **Rule-driven sorting** — give plain-English instructions like *"put anything
  with 'invoice' in the name into Finance"*.
- **Safe, reversible tidying** — every move is logged; undo a single mistake or a
  whole batch at any time.

---

## Features

- 🤖 **Multi-provider AI** — Google Gemini, OpenAI, OpenRouter, xAI (Grok), or any
  OpenAI-compatible endpoint. Models are fetched live from each provider.
- 📂 **Flexible scanning** — files only, include subfolders (recursive), organize
  folders themselves, or folders-only mode.
- 👁️ **Preview before you commit** — a tree view shows exactly where everything
  will land before any file is moved.
- ✏️ **Smart rename** — optional AI-suggested cleaner filenames.
- 🕘 **Operation history + selective undo** — a History panel lists every batch;
  undo one file, or an entire batch, long after the fact.
- 💬 **Built-in chat** — ask the AI questions about your files and how to organize
  them.
- 🌗 **Light / dark theme** — toggle in the header, remembered between sessions.
- ⚙️ **Manual overrides** — edit any destination, or flip an item between
  *Move* and *Skip* before organizing.

---

## How it works

```
Scan directory  →  Get AI suggestions  →  Review / edit  →  Preview  →  Organize
                                                                            │
                                                  every move recorded in    ▼
                                              organization_log.csv  →  History / Undo
```

1. **Scan** reads the target directory and lists files (and optionally folders).
2. **Get AI Suggestions** sends the file list (names only) to your provider, which
   returns a destination folder — and a new name if Smart Rename is on.
3. You **review** the table, tweak destinations, and toggle Move/Skip per item.
4. **Preview** groups the plan by destination folder.
5. **Organize** moves the files, creating folders as needed, and appends each move
   to `organization_log.csv`.
6. **History** reads that log so you can undo individual moves or whole batches.

---

## Requirements

- **Python 3.10+** (tested on 3.13)
- **Windows** is the primary target (the "Browse" button uses a native folder
  picker via Tkinter); it also runs on macOS/Linux, where you can type/paste the
  path instead.
- An **API key** for at least one supported AI provider.

---

## Installation

```bash
# 1. Clone / download this repository, then from its folder:
cd AIrrange

# 2. (Recommended) create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

> `requirements.txt` covers Flask and the Gemini SDK. The other providers
> (OpenAI / OpenRouter / xAI / custom) use the `requests` library; if it isn't
> already present, run `pip install requests`. Image-based renaming with Gemini
> also needs Pillow (`pip install pillow`).

---

## Usage

```bash
python app.py
```

This starts the server on **http://127.0.0.1:5000** and opens your browser
automatically. Press **Ctrl+C** in the terminal to stop it.

### First-time setup (add an API key)

1. Click the **⚙️ Settings** icon in the header.
2. Choose a **Provider** (e.g. Google Gemini).
3. Paste your **API key**. The model list loads automatically once the key is
   entered.
4. Pick a **Model** (the 👁️ marker indicates a vision-capable model).
5. Click **Test Connection**, then **Save Settings**.

Where to get a key:

| Provider   | Get a key at |
|------------|--------------|
| Gemini     | https://aistudio.google.com/apikey |
| OpenAI     | https://platform.openai.com/api-keys |
| OpenRouter | https://openrouter.ai/keys |
| xAI (Grok) | https://console.x.ai |
| Custom     | Any OpenAI-compatible endpoint — set its Base URL in Settings |

### Organizing files

1. **Set the target directory** — type/paste a path or click **Browse** (Windows).
2. Choose any options (each chip has a tooltip):
   - **Use Existing Folders** — prefer folders you already have.
   - **Smart Rename** — let the AI suggest cleaner filenames.
   - **Include Subfolders** — scan recursively.
   - **Organize Folders** — treat folders as movable items.
   - **Folders Only** — ignore individual files.
3. *(Optional)* Type **Instructions for AI** (e.g. *"group by project name"*).
4. Click **Scan** → **Get AI Suggestions**.
5. Review the table — edit any **Destination**, or set a row to **Skip**. Use the
   search/filter/sort toolbar for large lists.
6. Click **Preview** to see the plan, then **Organize** to apply it.

### Undoing changes

- **Undo Last** (header) reverses the most recent batch only.
- Open the **History** tab (right panel) to:
  - **Undo all** in any past batch, or
  - Undo a **single file** with its ↩ button.
- Undo restores files to their original location and name, and removes any folders
  left empty. It won't overwrite a file that has since reappeared at the original
  path.

---

## Configuration

Settings are stored in `config.json` (created/updated via the Settings dialog):

```jsonc
{
  "provider": "gemini",              // active provider id
  "model": "gemini-2.0-flash-exp",   // active model id
  "api_keys": { "gemini": "..." },   // per-provider keys
  "custom_base_url": "",             // for the "custom" provider
  "batchSize": 30,
  "excludeExtensions": [".ps1", ".bat", ".ini", ".lnk", ".log", ".csv", ".json"],
  "dryRun": false
}
```

- **API keys via environment variables** are also supported (used when no key is
  saved in `config.json`): `GEMINI_API_KEY`, `OPENAI_API_KEY`,
  `OPENROUTER_API_KEY`, `XAI_API_KEY`.
- **`excludeExtensions`** files are never listed for organizing. The app also skips
  its own files (`app.py`, `config.json`, `organization_log.csv`, `static/`, etc.).

### 🔒 Security note

`config.json` holds your API keys in plain text. It is listed in `.gitignore` and
is **not** committed to git — keep it that way. Never share or commit this file. If
a key is ever exposed, rotate it with your provider.

---

## Operation log

`organization_log.csv` records every move so history/undo can work. Columns:

| BatchId | Date | Source | Destination | Status |
|---------|------|--------|-------------|--------|

- One **BatchId** per *Organize* click.
- **Status** is `moved` or `undone` (rows are marked, not deleted, so history is
  preserved).
- Older logs in the previous 3-column format (`Date, Source, Destination`) are read
  automatically and shown as a single *legacy* batch.

The log lives **inside each scanned directory**, so history reflects the folder you
last scanned.

---

## Project structure

```
AIrrange/
├── app.py               # Flask app + JSON API routes
├── organizer_lib.py     # Core: scanning, AI prompt, move/undo, history log
├── providers.py         # Multi-provider AI manager (Gemini/OpenAI/OpenRouter/xAI/custom)
├── config.json          # Your settings + API keys (git-ignored)
├── organization_log.csv # Move history (git-ignored)
├── requirements.txt
├── templates/
│   └── index.html       # Single-page UI
└── static/
    ├── css/style.css    # Theme tokens (light/dark), layout, components
    └── js/
        ├── icons.js     # Inline SVG icon set
        └── main.js      # UI logic, history panel, undo, settings, chat
```

### API endpoints (for reference)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/scan` | Scan a directory |
| POST | `/api/suggest` | Get AI category/rename suggestions |
| POST | `/api/organize` | Move files (records a batch) |
| GET  | `/api/history` | Get history grouped by batch |
| POST | `/api/undo-operation` | Undo specific moves by destination |
| POST | `/api/undo-batch` | Undo all active moves in a batch |
| POST | `/api/undo` | Undo the most recent batch |
| POST | `/api/chat` | Chat with the AI about your files |
| POST | `/api/browse-folder` | Native folder picker (Windows) |
| GET/POST | `/api/settings` | Read/update provider settings |
| GET | `/api/providers`, `/api/models/<id>`, `/api/test-connection` | Provider/model info |

---

## Troubleshooting

- **"No API Key" badge / no model list** — open Settings and enter a valid key;
  the model dropdown populates once the key is recognized.
- **Connection test fails** — verify the key, the selected model, and (for the
  custom provider) the Base URL. Check the terminal for the error detail.
- **Browse button does nothing** — Tkinter folder picker is Windows-oriented; on
  other platforms, paste the path into the directory field instead.
- **Files went somewhere unexpected** — open **History** and undo the batch or the
  specific file; nothing is permanent.
- **AI suggestions look generic** — add explicit **Instructions for AI**, enable
  **Use Existing Folders**, or pick a more capable model.

---

## How privacy works

Only file/folder **names** (plus any instructions you type) are sent to your chosen
provider to generate suggestions — file **contents** are not uploaded, and all
moving/renaming happens entirely on your machine. Choose a provider/model you trust
for the metadata you're sending.

---

## License

See [LICENSE](LICENSE).
