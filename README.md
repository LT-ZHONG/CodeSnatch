# CodeSnatch

[中文](README_CN.md)

## 🤖 Cloud IDE Code Sync Agent

An intelligent Python tool designed to automatically extract and synchronize code files from browser-based cloud IDEs (such as CodeSandbox, Gitpod, StackBlitz, etc.) to your local machine. When you have written a large amount of code in a web-based IDE but struggle to save it conveniently, this tool is your solution.

It connects to Chrome's debugging port through Playwright, intelligently detects code editors on the page (such as Monaco Editor), calls their APIs to retrieve the contents of all open files, and finally saves them to your local disk.

## ✨ Core Features

* **Smart Detection**: Automatically detects popular editors such as Monaco Editor, VS Code Workbench, and CodeMirror.
* **API-First Extraction**: Prioritizes native editor APIs (such as `monaco.editor.getModels()`) to retrieve the most complete and accurate source code instead of relying on simple DOM scraping.
* **Multi-File Synchronization**: Extracts and saves all eligible code files at once while preserving the original directory structure.
* **Smart Filtering**: Automatically skips non-source-code directories and temporary files such as `node_modules` and `.git`.
* **Fallback Mechanism**: When API-based extraction fails, it attempts to use DOM extraction as a fallback method to maximize compatibility.

## 🛠️ Quick Start

### 1. Environment Setup

Make sure your system has Python 3.7+ installed.

### 2. Install Dependencies

After cloning this repository, install the required Python packages:

```bash
git clone git@github.com:LT-ZHONG/CodeSnatch.git
cd CodeSnatch

pip install playwright

playwright install chromium
```

### 3. Launch Chrome in Debug Mode

This is the most important step. You need to close all currently running Chrome instances, then launch Chrome with remote debugging enabled using the following command.

**Linux / macOS:**

```bash
google-chrome-stable --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug-profile"
```

> **Note**: The `--user-data-dir` parameter is used to create an isolated user profile, preventing interference with your regular Chrome browser profile.

### 4. Run the Synchronization Tool

1. In the Chrome window launched in debug mode, open your cloud IDE and load the project page containing your code.
2. Run the synchronization script in the terminal:

```bash
python ide_sync_agent.py
```

The script will automatically connect to Chrome, locate the IDE tab, extract the code, and save it locally to the `~/synced_from_ide` directory.

## ⚙️ How It Works

1. **Connection**:
   The script connects to Chrome's debugging port at `localhost:9222` using `playwright.chromium.connect_over_cdp`.

2. **Discovery**:
   It scans all open tabs and identifies cloud IDE pages by executing JavaScript checks for global variables (such as `window.monaco`) or specific DOM elements (such as `.monaco-workbench`).

3. **Extraction**:

   * **Preferred Method**:
     Executes JavaScript within the page context and calls `monaco.editor.getModels()` to retrieve all editor models (i.e., files), then reads their `uri` and `value` (content).

   * **Fallback Method**:
     If the API is unavailable, it attempts to locate DOM elements containing source code using `document.querySelector` and extracts their text content.

4. **Saving**:
   Writes the extracted file contents to the local disk according to their original path structure.

