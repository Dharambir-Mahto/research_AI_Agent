from playwright.async_api import async_playwright
from langchain_core.tools import tool
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from urllib.parse import urlparse
import ipaddress
import socket
import re
import os
from pathlib import Path
from dotenv import load_dotenv

from ddgs import DDGS

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


# =================================
# BROWSER MANAGER (used only for reading pages)
# =================================
class BrowserAgent:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
        )
        await self.context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        self.page = await self.context.new_page()
        print("[BROWSER] Started successfully")

    async def validate_url(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP and HTTPS URLs are allowed")
        if not parsed.hostname:
            raise ValueError("Invalid URL")
        host = parsed.hostname.lower()
        if host == "localhost" or host.endswith(".local"):
            raise ValueError("Local addresses are blocked")
        try:
            addresses = socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise ValueError(f"Could not resolve host: {e}")
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or not ip.is_global):
                raise ValueError(f"Blocked non-public address: {ip}")

    async def read_webpage(self, url: str):
        print(f"[BROWSER] Reading: {url}")
        await self.validate_url(url)
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self.validate_url(self.page.url)
        content = await self.page.evaluate(
            """() => {
                document.querySelectorAll('script,style,noscript,nav,footer,header,aside').forEach(e => e.remove());
                return document.body ? document.body.innerText : '';
            }"""
        )
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        return {"url": self.page.url, "content": content[:15000]}

    async def close(self):
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
        print("[BROWSER] Closed")


# =================================
# LANGCHAIN TOOLS
# =================================
def get_browser_tools(browser: BrowserAgent):

    @tool
    def search_web(query: str) -> str:
        """
        Search the internet for a query and return up to 8 results.
        Each result contains a title, URL, and snippet.
        Use this tool first, then use read_webpage on the URLs you want to read.
        """
        try:
            results = DDGS().text(query, max_results=8)
            if not results:
                return "SEARCH_FAILED: no results returned"
            # Return a compact string the LLM can parse
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(
                    f"{i}. {r.get('title', 'Untitled')}\n"
                    f"   URL: {r.get('href', '')}\n"
                    f"   {r.get('body', '')}"
                )
            return "\n\n".join(lines)
        except Exception as e:
            return f"SEARCH_FAILED: {e}"

    @tool
    async def read_webpage(url: str) -> str:
        """
        Visit a public webpage and return its readable text (first 15k chars).
        Use this after search_web returns URLs.
        """
        try:
            result = await browser.read_webpage(url)
            return str(result)
        except Exception as e:
            return f"READ_FAILED: {e}"

    return [search_web, read_webpage]

def get_document_tools(base_dir: str):
    """
    Create document generation tools that save files into base_dir.
    The agent chooses subdirectories and filenames itself.
    """
    from langchain_core.tools import tool

    @tool
    def save_as_markdown(content: str, relative_path: str) -> str:
        """
        Save text content as a Markdown (.md) file.
        relative_path is relative to the research directory, e.g. 'reports/python/latest.md'.
        The tool will create any missing parent directories automatically.
        """
        try:
            full_path = os.path.join(base_dir, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"SAVED: {full_path}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"SAVE_FAILED: {type(e).__name__}: {e}"

    @tool
    def save_as_docx(content: str, relative_path: str) -> str:
        """
        Save text content as a Word (.docx) file.
        relative_path is relative to the research directory, e.g. 'reports/python/latest.docx'.
        The tool will create any missing parent directories automatically.
        """
        try:
            full_path = os.path.join(base_dir, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            doc = Document()
            for line in content.split("\n"):
                if line.startswith("# "):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith("## "):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith("### "):
                    doc.add_heading(line[4:], level=3)
                else:
                    doc.add_paragraph(line)
            doc.save(full_path)
            return f"SAVED: {full_path}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"SAVE_FAILED: {type(e).__name__}: {e}"

    @tool
    def save_as_pdf(content: str, relative_path: str) -> str:
        """
        Save text content as a PDF file.
        relative_path is relative to the research directory, e.g. 'reports/python/latest.pdf'.
        The tool will create any missing parent directories automatically.
        Use this whenever the user asks for a PDF.
        """
        try:
            full_path = os.path.join(base_dir, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            doc = SimpleDocTemplate(full_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            for raw in content.split("\n"):
                line = raw.rstrip()
                if not line.strip():
                    story.append(Spacer(1, 8))
                    continue
                # Strip Markdown markers so they don't render literally
                if line.startswith("### "):
                    story.append(Paragraph(line[4:], styles["Heading3"]))
                elif line.startswith("## "):
                    story.append(Paragraph(line[3:], styles["Heading2"]))
                elif line.startswith("# "):
                    story.append(Paragraph(line[2:], styles["Heading1"]))
                else:
                    safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(safe, styles["Normal"]))
                story.append(Spacer(1, 4))

            doc.build(story)
            return f"SAVED: {full_path}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"SAVE_FAILED: {type(e).__name__}: {e}"
    return [save_as_markdown, save_as_docx, save_as_pdf]