#!/usr/bin/env python3
"""
云 IDE 代码同步智能体 (修复版 v3 - 自动查找云 IDE 标签页)
系统：Ubuntu 20.04
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError as e:
    print("❌ Playwright 未安装，请执行:")
    print("   python3 -m pip install playwright")
    print("   python3 -m playwright install chromium")
    sys.exit(1)


class CloudIDESyncAgent:
    def __init__(
        self,
        cdp_url: str = "http://localhost:9222",
        output_dir: str = "~/synced_from_ide"
    ):
        self.cdp_url = cdp_url
        self.output_dir = Path(output_dir).expanduser()
        self.browser = None
        self.playwright = None
        self.page = None

    async def find_ide_page(self):
        """
        遍历所有标签页，找到包含云 IDE 的页面
        """
        print("\n🔍 正在查找云 IDE 标签页...")

        contexts = self.browser.contexts
        all_pages = []

        for ctx in contexts:
            for page in ctx.pages:
                all_pages.append(page)

        print(f"   共发现 {len(all_pages)} 个标签页")

        # 逐个检查，找到包含 Monaco 或 VS Code 的页面
        for i, page in enumerate(all_pages):
            try:
                url = page.url
                title = await page.title()
                print(f"   [{i+1}] {url} | {title[:40]}")

                # 跳过 chrome 内部页面
                if url.startswith('chrome://') or url.startswith('about:'):
                    continue

                # 检测是否是 IDE
                has_ide = await page.evaluate("""() => {
                    return {
                        hasMonaco: typeof window.monaco !== 'undefined',
                        hasVSCode: !!document.querySelector('.monaco-workbench'),
                        hasCodeMirror: !!document.querySelector('.CodeMirror'),
                        hostname: location.hostname
                    };
                }""")

                if has_ide.get('hasMonaco') or has_ide.get('hasVSCode'):
                    print(f"   ✅ 找到云 IDE 页面: {url}")
                    return page

            except Exception as e:
                print(f"   ⚠️ 检查页面失败: {e}")
                continue

        # 如果没找到 IDE，返回第一个非 chrome 页面
        for page in all_pages:
            if not page.url.startswith('chrome://') and not page.url.startswith('about:'):
                print(f"   ⚠️ 未检测到 IDE，使用页面: {page.url}")
                return page

        # 最后 fallback 到第一个可用页面
        if all_pages:
            return all_pages[0]

        return None

    async def connect(self):
        """通过 CDP 连接已运行的 Chrome"""
        print(f"\n🔗 连接 Chrome CDP: {self.cdp_url}")
        self.playwright = await async_playwright().start()

        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
        except Exception as e:
            print(f"\n❌ 连接失败: {e}")
            print("\n请确保 Chrome 已以调试模式运行:")
            print('   google-chrome-stable --remote-debugging-port=9222 \\')
            print('       --user-data-dir="$HOME/.chrome-debug-profile"')
            raise

        # 查找云 IDE 页面
        self.page = await self.find_ide_page()

        if not self.page:
            raise RuntimeError("未找到任何可用页面，请先在 Chrome 中打开云 IDE")

        print(f"\n✅ 已连接")
        print(f"   URL: {self.page.url}")
        print(f"   标题: {await self.page.title()}")
        return self.page

    async def analyze_page(self):
        result = await self.page.evaluate("""() => {
            return {
                hasMonaco: typeof window.monaco !== 'undefined',
                hasVSCode: !!document.querySelector('.monaco-workbench'),
                url: location.href,
                title: document.title
            };
        }""")
        print(f"\n🔍 页面分析:")
        print(f"   Monaco Editor: {result['hasMonaco']}")
        print(f"   VS Code Workbench: {result['hasVSCode']}")
        return result

    async def extract_from_monaco(self):
        print("\n📥 正在通过 Monaco Editor API 提取代码...")

        result = await self.page.evaluate("""() => {
            if (!window.monaco || !window.monaco.editor) {
                return { success: false, error: "Monaco Editor 未暴露到全局" };
            }

            const models = window.monaco.editor.getModels();
            const files = [];

            for (const model of models) {
                const uri = model.uri;
                if (!uri || !uri.path) continue;

                const path = uri.path;
                const skipPatterns = [
                    'node_modules', '.git/', 'extension://', 'vscode://',
                    'inmemory://', 'output://', 'debug://', 'vscode-terminal',
                    'file:///tmp/', 'file:///usr/', 'file:///etc/'
                ];
                if (skipPatterns.some(p => path.includes(p))) continue;

                const codeExts = [
                    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
                    '.go', '.rs', '.rb', '.php', '.html', '.css', '.scss', '.sass',
                    '.json', '.yaml', '.yml', '.toml', '.md', '.txt', '.sh', '.bash',
                    '.vue', '.svelte', '.sql', '.swift', '.kt', '.m', '.r', '.pl'
                ];

                const isCodeFile = codeExts.some(ext => path.toLowerCase().endsWith(ext));
                const hasPath = path.includes('/') && path.length > 1;

                if (!isCodeFile && !hasPath) continue;

                files.push({
                    path: path,
                    content: model.getValue(),
                    language: model.getLanguageId(),
                    lines: model.getLineCount()
                });
            }

            return { success: true, files: files, count: files.length };
        }""")

        return result

    async def extract_from_dom(self):
        print("\n📥 尝试 DOM 提取...")

        result = await self.page.evaluate("""() => {
            const selectors = [
                '.monaco-editor .view-lines',
                '.CodeMirror-code',
                '.ace_content'
            ];

            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText.length > 20) {
                    return { found: true, text: el.innerText };
                }
            }
            return { found: false };
        }""")

        if result.get('found'):
            fname = await self.page.title()
            safe_name = fname.replace(' ', '_').replace('/', '_')[:50] + '.txt'
            return {
                'success': True,
                'files': [{'path': '/' + safe_name, 'content': result['text']}],
                'count': 1
            }
        return {'success': False, 'error': 'DOM 提取失败'}

    def save_files(self, files_data):
        if not files_data.get('success') or not files_data.get('files'):
            print("⚠️ 没有提取到文件")
            return []

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = self.output_dir / f"sync_{timestamp}"
        save_dir.mkdir(parents=True, exist_ok=True)

        saved = []

        for f in files_data['files']:
            raw_path = f['path'].lstrip('/')
            if '..' in raw_path:
                raw_path = Path(raw_path).name

            local_path = save_dir / raw_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                subprocess.run(['touch', str(local_path)], check=True)

                with open(local_path, 'w', encoding='utf-8') as file:
                    file.write(f.get('content', ''))

                saved.append(local_path)
                print(f"   ✅ {f['path']} ({f.get('lines', '?')} 行) → {local_path}")

            except Exception as e:
                print(f"   ❌ 失败 {f['path']}: {e}")

        return saved

    async def run(self):
        print("=" * 55)
        print("🤖 云 IDE 代码同步智能体")
        print("=" * 55)

        try:
            await self.connect()
            analysis = await self.analyze_page()

            if analysis.get('hasMonaco'):
                files_data = await self.extract_from_monaco()
            else:
                files_data = await self.extract_from_dom()

            if not files_data.get('success'):
                print(f"\n⚠️ {files_data.get('error', '提取失败')}，尝试后备方案...")
                files_data = await self.extract_from_dom()

            if files_data.get('success'):
                print(f"\n💾 正在保存 {files_data.get('count', 0)} 个文件...")
                saved = self.save_files(files_data)
                print(f"\n🎉 完成！共保存 {len(saved)} 个文件")
                print(f"📁 目录: {self.output_dir}")
            else:
                print(f"\n❌ 无法提取: {files_data.get('error')}")

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()


async def main():
    agent = CloudIDESyncAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
