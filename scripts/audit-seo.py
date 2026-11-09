#!/usr/bin/env python3
"""Read-only SEO checklist for every repository HTML file; prints failures."""
from pathlib import Path
from html.parser import HTMLParser
import re
ROOT=Path(__file__).resolve().parent.parent
BASE="https://aussieprimaryacademy.github.io/aussie-primary-academy/"
class Audit(HTMLParser):
 def __init__(self):
  super().__init__(); self.titles=[];self.desc=[];self.canon=[];self.h1=0;self.lang=None;self.viewport=0;self.ga=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="html": self.lang=a.get("lang")
  if tag=="title": self.in_title=True;self.title=""
  if tag=="h1": self.h1+=1
  if tag=="meta":
   if a.get("name","").lower()=="description":self.desc.append(a.get("content",""))
   if a.get("name","").lower()=="viewport":self.viewport+=1
  if tag=="link" and a.get("rel","").lower()=="canonical":self.canon.append(a.get("href",""))
  if tag=="script" and ("G-41Q0QR6ZHD" in a.get("src","")):self.ga+=1
  if tag=="script":self.script=True
 def handle_endtag(self,tag):
  if tag=="title" and getattr(self,"in_title",False):self.titles.append(getattr(self,"title",""));self.in_title=False
 def handle_data(self,data):
  if getattr(self,"in_title",False):self.title+=data
def main():
 failures=[]
 for p in sorted(ROOT.rglob("*.html")):
  if ".git" in p.parts or ".github" in p.parts or p.name=="google99305cdd54a8d1be.html":continue
  a=Audit();a.feed(p.read_text(encoding="utf-8",errors="ignore")); rel=p.relative_to(ROOT)
  checks=[
   (len(a.canon)==1 and a.canon[0].startswith("https://") and "?" not in a.canon[0] and "index.html" not in a.canon[0],"canonical"),
   (len(a.titles)==1 and 0<len(a.titles[0])<60,"title (<60 chars, unique tag)"),
   (len(a.desc)==1 and 0<len(a.desc[0])<160,"meta description (<160 chars)"),
   (a.h1==1,"one H1"),(a.lang=="en-AU",'lang="en-AU"'),
   (a.viewport==1,"viewport"),(a.ga>0 or "G-41Q0QR6ZHD" in p.read_text(errors="ignore"),"GA4")
  ]
  for ok,label in checks:
   if not ok:failures.append(f"{rel}: {label}")
 print("\\n".join(failures) if failures else "All audited HTML checks passed.")
 print(f"Failures: {len(failures)}")
if __name__=="__main__":main()
