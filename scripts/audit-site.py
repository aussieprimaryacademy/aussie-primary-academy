#!/usr/bin/env python3
"""Read-only whole-repository audit for APA pages, links, metadata and worksheet assets."""
from __future__ import annotations
import csv,json,os,re,runpy
from collections import Counter,defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse,unquote
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent.parent
BASE="https://aussieprimaryacademy.github.io/aussie-primary-academy/"
HOST="aussieprimaryacademy.github.io"; PREFIX="/aussie-primary-academy/"
IGNORE={"404.html","email-thank-you.html","google99305cdd54a8d1be.html"}
issues=[]; counts=Counter(); titles=defaultdict(list); canonicals=defaultdict(list); parsers={}; linked_pdfs=set()
def add(kind,path,detail,severity="warning"):
 issues.append({"severity":severity,"kind":kind,"path":str(path),"detail":str(detail)})
class Parser(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.title=[]; self.in_title=False; self.h1=0; self.lang=None; self.meta=defaultdict(list); self.canon=[]; self.links=[]; self.ids=set(); self.imgs=[]; self.ld=[]; self.in_ld=False; self.ldbuf=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=="html": self.lang=a.get("lang")
  if t=="title": self.in_title=True
  if t=="h1": self.h1+=1
  if t in ("a","link","iframe","source","video","audio") and a.get("href"): self.links.append((a["href"],"href"))
  if t in ("img","iframe","source","video","audio") and a.get("src"): self.links.append((a["src"],"src"))
  if a.get("id"): self.ids.add(a["id"])
  if t=="a" and a.get("name"): self.ids.add(a["name"])
  if t=="img": self.imgs.append(a)
  if t=="meta":
   k=(a.get("name") or a.get("property") or "").lower()
   if k: self.meta[k].append(a.get("content",""))
  if t=="link" and "canonical" in (a.get("rel") or "").lower().split() and a.get("href"): self.canon.append(a["href"])
  if t=="script" and a.get("type","").lower()=="application/ld+json": self.in_ld=True; self.ldbuf=[]
 def handle_endtag(self,t):
  if t=="title": self.in_title=False
  if t=="script" and self.in_ld: self.ld.append("".join(self.ldbuf)); self.in_ld=False; self.ldbuf=[]
 def handle_data(self,d):
  if self.in_title: self.title.append(d)
  if self.in_ld: self.ldbuf.append(d)
def resolve(page,raw):
 raw=unquote((raw or "").strip())
 if not raw or raw.startswith(("#","mailto:","tel:","javascript:","data:","blob:")): return None,None
 u=urlparse(raw)
 if u.scheme and u.scheme not in ("http","https"): return None,None
 if u.netloc:
  if u.netloc.lower()!=HOST: return None,None
  p=u.path
  if p.startswith(PREFIX): p=p[len(PREFIX):]
  elif p in ("","/"): p=""
  else: return None,None
  target=ROOT/p.lstrip("/")
 elif raw.startswith("/"):
  p=u.path; p=p[len(PREFIX):] if p.startswith(PREFIX) else p.lstrip("/"); target=ROOT/p
 else: target=(page.parent/u.path).resolve()
 try: target.relative_to(ROOT.resolve())
 except ValueError: return None,None
 return target,u.fragment
html=sorted(p for p in ROOT.rglob("*.html") if not any(x.startswith(".") for x in p.relative_to(ROOT).parts))
pdfs=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower()==".pdf")
images=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in {".png",".jpg",".jpeg",".webp",".svg",".gif"})
counts.update(html_files=len(html),pdf_files=len(pdfs),image_files=len(images))
for p in html:
 rel=p.relative_to(ROOT).as_posix()
 try:
  raw=p.read_text(encoding="utf-8",errors="replace"); q=Parser(); q.feed(raw); parsers[p]=q
 except Exception as e: add("html_parse",rel,e,"error"); continue
 title=" ".join(" ".join(q.title).split()); desc=q.meta.get("description",[])
 if p.name not in IGNORE:
  if not title: add("missing_title",rel,"No title","error")
  if not desc or not any(x.strip() for x in desc): add("missing_description",rel,"No non-empty description")
  if not q.lang: add("missing_lang",rel,"No html lang")
  if q.h1==0: add("missing_h1",rel,"No H1","error")
  if q.h1>1: add("multiple_h1",rel,f"{q.h1} H1 headings")
  if len(q.canon)!=1: add("canonical_count",rel,f"Expected 1 canonical, found {len(q.canon)}")
  for img in q.imgs:
   if not img.get("alt","").strip(): add("image_alt_missing",rel,f'Image missing alt: {img.get("src","(no src)")}')
 if title: titles[title.lower()].append(rel)
 for c in q.canon: canonicals[c].append(rel)
 for block in q.ld:
  try: json.loads(block)
  except Exception as e: add("invalid_jsonld",rel,e,"error")
 for url,attr in q.links:
  if url.startswith("/") and not url.startswith(PREFIX):
   add("wrong_project_base_path",rel,f"{attr}={url}", "error")
   continue
  target,frag=resolve(p,url)
  if target is None: continue
  if target.exists() and target.suffix.lower()==".pdf": linked_pdfs.add(target.resolve())
  if not target.exists(): add("broken_local_link" if attr=="href" else "missing_local_asset",rel,f'{attr}="{url}" -> {target}',"error")
  elif frag and target.is_file() and target.suffix.lower()==".html":
   other=parsers.get(target)
   if other is None:
    try: other=Parser(); other.feed(target.read_text(encoding="utf-8",errors="replace")); parsers[target]=other
    except Exception: other=None
   if other and frag not in other.ids: add("broken_fragment",rel,f"{url} points to missing #{frag}")
for t,ps in titles.items():
 if len(ps)>1: add("duplicate_title","; ".join(ps),t)
for c,ps in canonicals.items():
 if len(ps)>1: add("duplicate_canonical","; ".join(ps),c,"error" if len(ps)>2 else "warning")
try:
 compile((ROOT/"scripts/generate-worksheet-pages.py").read_text(encoding="utf-8"),"scripts/generate-worksheet-pages.py","exec")
except SyntaxError as e:
 add("generator_syntax_error","scripts/generate-worksheet-pages.py",f"Line {e.lineno}: {e.msg}","error")
missing_previews=[]
for pdf in pdfs:
 if "answer-key" in pdf.name.lower() or "answerkey" in pdf.name.lower(): continue
 rel=pdf.relative_to(ROOT).as_posix()
 if pdf.resolve() not in linked_pdfs: add("pdf_not_linked_from_html",rel,"PDF is not referenced by any parsed HTML link")
 folder=pdf.parent/"previews"; stem=pdf.stem.strip().lower()
 found=folder.exists() and any(x.is_file() and x.stem.strip().lower()==stem and x.suffix.lower() in {".png",".jpg",".jpeg",".webp"} for x in folder.iterdir())
 if not found: missing_previews.append(rel)
for pdf in missing_previews: add("missing_preview",pdf,"No same-stem image found in expected previews folder")
code_mismatch=0
for p,q in list(parsers.items()):
 raw=p.read_text(encoding="utf-8",errors="replace")
 codes=set(re.findall(r"\bAC9[A-Z][A-Z0-9]+\b",raw,re.I))
 if codes:
  for match in re.finditer(r'<a\b[^>]*href=["\']([^"\']+\.pdf(?:[?#][^"\']*)?)["\']',raw,re.I):
   target,_=resolve(p,match.group(1))
   if target and target.exists():
    fc=set(re.findall(r"\bAC9[A-Z][A-Z0-9]+\b",target.name,re.I))
    if fc and not codes.intersection(fc):
     code_mismatch+=1; add("page_pdf_curriculum_code_mismatch",p.relative_to(ROOT),f"page {sorted(codes)} vs PDF filename {sorted(fc)}")
counts["curriculum_filename_mismatches"]=code_mismatch
sitemap=ROOT/"sitemap.xml"; urls=[]
if sitemap.exists():
 counts["sitemap_bytes"]=sitemap.stat().st_size
 try:
  root=ET.parse(sitemap).getroot(); urls=[x.text.strip() for x in root.iter() if x.tag.endswith("loc") and x.text]
  counts["sitemap_urls"]=len(urls); counts["sitemap_unique_urls"]=len(set(urls))
  if len(urls)!=len(set(urls)): add("duplicate_sitemap_url","sitemap.xml","Duplicate URL","error")
  if sitemap.stat().st_size>50*1024*1024: add("sitemap_size","sitemap.xml","Exceeds 50 MB","error")
  if len(urls)>50000: add("sitemap_url_limit","sitemap.xml","Exceeds 50,000 URLs","error")
  for u in urls:
   uo=urlparse(u)
   if uo.netloc.lower()!=HOST or not uo.path.startswith(PREFIX): add("sitemap_wrong_host_or_path","sitemap.xml",u)
  expected=set()
  for p in html:
   if p.name in IGNORE or " " in p.name: continue
   relparts=p.relative_to(ROOT).parts
   if relparts[0] in {"blog","pages"}: expected.add(BASE+p.relative_to(ROOT).as_posix())
   elif len(relparts)==1 and p.name=="index.html": expected.add(BASE)
   elif len(relparts)==1: expected.add(BASE+p.relative_to(ROOT).as_posix())
  for u in sorted(expected-set(urls)): add("html_not_in_sitemap","sitemap.xml",u)
  for u in sorted(set(urls)-expected): add("sitemap_url_no_matching_html","sitemap.xml",u)
 except Exception as e: add("sitemap_xml","sitemap.xml",e,"error")
else: add("sitemap_missing","sitemap.xml","No sitemap.xml","error")
robots=ROOT/"robots.txt"
if not robots.exists(): add("robots_missing","robots.txt","No robots.txt","error")
else:
 r=robots.read_text(encoding="utf-8",errors="replace"); counts["robots_bytes"]=robots.stat().st_size
 for bot in ("OAI-SearchBot","Googlebot","bingbot","PerplexityBot","Claude-SearchBot"):
  if not re.search(r"(?im)^User-agent:\s*"+re.escape(bot)+r"\s*$",r): add("robots_bot_group_missing","robots.txt",bot)
 if BASE+"sitemap.xml" not in r: add("robots_sitemap_reference","robots.txt","No project sitemap reference")
by=Counter(i["kind"] for i in issues); counts["issue_count"]=len(issues); counts["error_count"]=sum(i["severity"]=="error" for i in issues); counts["warning_count"]=len(issues)-counts["error_count"]
report={"counts":dict(counts),"issues":issues,"scope":"Repository source only; does not prove live HTTP responses, Google indexing, AI visibility, or semantic ACARA correctness"}
(ROOT/"site-audit-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
with (ROOT/"site-audit-issues.csv").open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=["severity","kind","path","detail"]); w.writeheader(); w.writerows(issues)
lines=["# APA whole-site audit","","> Source-level audit. Live status, Google indexing, AI citations and semantic ACARA accuracy are not proven by this report.","","## Inventory"]
for k,v in counts.items(): lines.append(f"- **{k.replace('_',' ').title()}:** {v:,}")
lines += ["","## Issue categories"]
for k,n in by.most_common(): lines.append(f"- **{k}:** {n}")
lines += ["","## Errors"]
for i in issues:
 if i["severity"]=="error": lines.append(f"- **{i['kind']}** — {i['path']}: {i['detail']}")
lines += ["","Full issue list: site-audit-report.json and site-audit-issues.csv."]
md="\n".join(lines)+"\n"; dest=os.environ.get("GITHUB_STEP_SUMMARY")
if dest:
 with open(dest,"a",encoding="utf-8") as f: f.write(md)
print(md)
