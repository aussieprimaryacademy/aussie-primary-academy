#!/usr/bin/env python3
"""Generate a conservative sitemap from public, substantive HTML pages.

lastmod is the latest Git commit date for each page (not the build date).
Pages with fewer than MIN_WORDS visible-text words, noindex, or duplicate
visible text are omitted. Review exclusions before publishing.
"""
from pathlib import Path
from datetime import date
from html.parser import HTMLParser
from subprocess import run, DEVNULL
from xml.sax.saxutils import escape
import re

BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
ROOT = Path(__file__).resolve().parent.parent
MIN_WORDS = 80
EXCLUDED_NAMES = {"404.html", "email-thank-you.html", "google99305cdd54a8d1be.html"}
EXCLUDED_DIRS = {".git", ".github", "scripts", "assets", "css", "js"}

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in {"script","style","noscript"}: self.skip += 1
    def handle_endtag(self, tag):
        if tag in {"script","style","noscript"} and self.skip: self.skip -= 1
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)

def visible_text(html):
    p=TextExtractor(); p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.parts)).strip()

def git_lastmod(path):
    try:
        value=run(["git","log","-1","--format=%cs","--",str(path.relative_to(ROOT))],
                  cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
        date.fromisoformat(value)
        return value
    except Exception:
        return None

def collect_pages():
    candidates=[]
    for path in ROOT.rglob("*.html"):
        rel=path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts) or path.name in EXCLUDED_NAMES:
            continue
        if " " in path.name or path.name == "index.html" and path.parent == ROOT:
            # Homepage is represented by the folder URL, not /index.html.
            if path.name == "index.html" and path.parent == ROOT: pass
            else: continue
        html=path.read_text(encoding="utf-8",errors="ignore")
        if re.search(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*noindex',html,re.I):
            continue
        text=visible_text(html)
        words=re.findall(r"\b[\w'-]+\b",text)
        if len(words)<MIN_WORDS: continue
        normalized=re.sub(r"[^a-z0-9]+"," ",text.lower()).strip()
        if not normalized: continue
        candidates.append((path,normalized))
    # Deduplicate exact visible-text duplicates deterministically; keep shortest URL.
    seen=set(); pages=[]
    for path,normalized in sorted(candidates,key=lambda x:(len(x[0].relative_to(ROOT).as_posix()),x[0].as_posix())):
        if normalized in seen: continue
        seen.add(normalized); pages.append(path)
    return pages

def write_sitemap(pages):
    lines=['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in sorted(pages,key=lambda p:(p==ROOT/"index.html",p.as_posix())):
        rel=path.relative_to(ROOT).as_posix()
        loc=BASE if rel=="index.html" else BASE+rel
        lastmod=git_lastmod(path)
        lines += ["  <url>",f"    <loc>{escape(loc)}</loc>"]
        if lastmod: lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (ROOT/"sitemap.xml").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return len(pages)

if __name__=="__main__":
    pages=collect_pages(); count=write_sitemap(pages)
    print(f"Generated sitemap.xml with {count} substantive URLs (git lastmod where available)")
    import xml.etree.ElementTree as ET
    ET.parse(ROOT/"sitemap.xml")
    print("XML validation passed")
