# CodeSnatch

## 🤖 Cloud IDE Code Sync Agent

一个智能的 Python 工具，用于从浏览器中的云 IDE（如 CodeSandbox, Gitpod, StackBlitz 等）自动提取并同步代码文件到本地。当你在网页上编写了大量代码，却苦于无法方便地保存时，这个工具就是你的救星。

它通过 Playwright 连接到 Chrome 的调试端口，智能识别页面上的代码编辑器（如 Monaco Editor），并调用其 API 获取所有打开的文件内容，最终保存到你的本地磁盘。

## ✨ 核心特性

*   **智能识别**: 自动检测页面中的 Monaco Editor、VS Code Workbench 或 CodeMirror 等主流编辑器。
*   **API 优先提取**: 优先使用编辑器原生 API（如 `monaco.editor.getModels()`）获取最完整、最准确的代码，而非简单的 DOM 抓取。
*   **多文件同步**: 一次性提取并保存所有符合条件的代码文件，并保持原有的目录结构。
*   **智能过滤**: 自动跳过 `node_modules`、`.git` 等非源代码目录和临时文件。
*   **后备方案**: 当 API 提取失败时，会尝试使用 DOM 提取作为后备方案，确保最大程度的兼容性。

## 🛠️ 快速开始

### 1. 环境准备

确保你的系统已安装 Python 3.7+。

### 2. 安装依赖

克隆本仓库后，安装所需的 Python 包：

```bash
git clone git@github.com:LT-ZHONG/CodeSnatch.git
cd CodeSnatch

pip install playwright

playwright install chromium
```

### 3. 启动 Chrome 调试模式

这是最关键的一步。你需要关闭所有正在运行的 Chrome 实例，然后使用以下命令启动一个允许远程调试的 Chrome 窗口。

**Linux / macOS:**
```bash
google-chrome-stable --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug-profile"
```

> **注意**: `--user-data-dir` 参数是为了使用一个独立的用户配置文件，避免影响你日常使用的 Chrome 浏览器。

### 4. 运行同步工具

1.  在刚刚启动的调试模式 Chrome 中，打开你的云 IDE 并加载包含代码的项目页面。
2.  在终端运行同步脚本：

```bash
python ide_sync_agent.py
```

脚本会自动连接到 Chrome，查找 IDE 标签页，提取代码并保存到本地的 `~/synced_from_ide` 目录中。

## ⚙️ 工作原理

1.  **连接**: 脚本通过 `playwright.chromium.connect_over_cdp` 连接到 `localhost:9222` 的 Chrome 调试端口。
2.  **发现**: 遍历所有打开的标签页，通过执行 JavaScript 检测全局变量（如 `window.monaco`）或特定 DOM 元素（如 `.monaco-workbench`）来识别云 IDE 页面。
3.  **提取**:
    *   **首选**: 在页面上下文中执行 JS，调用 `monaco.editor.getModels()` 获取所有编辑器模型（即文件），然后读取其 `uri` 和 `value`（内容）。
    *   **备选**: 如果 API 不可用，则尝试通过 `document.querySelector` 查找包含代码的 DOM 元素并提取文本。
4.  **保存**: 将提取到的文件内容，按照其路径结构写入到本地磁盘。
