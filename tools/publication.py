"""Validate and publish this manual's explicit YAML blocks. Not a universal renderer."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {"heading", "prose", "lead", "list", "fields", "steps", "table", "code", "callout", "figure"}
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node):
    result = {}
    for key, value in node.value:
        name = loader.construct_object(key)
        if name in result:
            raise ValueError(f"duplicate YAML key {name}")
        result[name] = loader.construct_object(value)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def load(path):
    return yaml.load(path.read_text(), Loader=UniqueLoader)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in ("meta", "text") or value.get("type") != "code":
                yield from strings(item)


def scalar_rules(node, path=""):
    if isinstance(node, yaml.MappingNode):
        items = {k.value: v for k, v in node.value}
        kind = items.get("type")
        literal_allowed = kind and kind.value == "code"
        for key, value in items.items():
            if key == "meta":
                continue
            if isinstance(value, yaml.ScalarNode) and value.style == "|" and not literal_allowed:
                raise ValueError(f"literal narrative scalar at {path}/{key}")
            scalar_rules(value, path + "/" + key)
    elif isinstance(node, yaml.SequenceNode):
        for i, value in enumerate(node.value):
            scalar_rules(value, path + f"/{i}")


def read_book(root=ROOT):
    root = root.resolve()
    schema = load(root / "standards/yaml-markup-standard.yaml")["schema"]
    validator = Draft202012Validator(schema)
    manifest = load(root / "book/manifest.yaml")
    validator.validate(manifest)
    documents, seen = [], set()
    entries = [(entry, "front", None) for entry in manifest.get("front", [])]
    entries += [(entry, "chapter", i) for i, entry in enumerate(manifest["chapters"], 1)]
    entries += [(entry, "appendix", None) for entry in manifest.get("appendices", [])]
    for entry, kind, number in entries:
        entry = {"file": entry} if isinstance(entry, str) else entry
        if entry.get("visibility", "reader") != "reader":
            raise ValueError("this reader-only build requires manifest entries to be reader-visible")
        path = (root / "book" / entry["file"]).resolve()
        if not path.is_relative_to(root / "book"):
            raise ValueError("manifest path outside book")
        d = load(path)
        validator.validate(d)
        if "body" not in d or "profile" in d:
            raise ValueError("this publisher requires explicit body blocks without profiles")
        allowed = {"title", "updated", "subtitle", "status", "scope", "version", "tags", "authors",
                   "language", "description", "inline_markup", "standard", "id", "meta", "body"}
        if set(d) - allowed:
            raise ValueError(f"undeclared domain keys in {path.name}")
        scalar_rules(yaml.compose(path.read_text()))
        did = d["id"]
        if did in seen:
            raise ValueError(f"duplicate document id {did}")
        seen.add(did)
        ids = set()
        for b in d["body"]:
            if b["type"] not in SUPPORTED:
                raise ValueError(f"unsupported block {b['type']}; add support before publishing")
            if b.get("visibility", "reader") != "reader":
                continue
            if "id" in b:
                if b["id"] in ids:
                    raise ValueError(f"duplicate block id {did}#{b['id']}")
                ids.add(b["id"])
            if b["type"] == "heading" and not 2 <= b["level"] <= 4:
                raise ValueError("body headings must be levels 2 to 4")
            if b["type"] == "table" and any(len(row) != len(b["columns"]) for row in b["rows"]):
                raise ValueError("table row width mismatch")
            if b["type"] == "figure" and not (path.parent / b["src"]).is_file():
                raise ValueError(f"missing figure {b['src']}")
            if b["type"] == "figure":
                for source in b.get("sources", {}).values():
                    if not (path.parent / source).is_file():
                        raise ValueError(f"missing figure variant {source}")
        documents.append({"data": d, "path": path, "kind": kind, "number": number, "ids": ids})
    lookup = {x["data"]["id"]: x for x in documents}
    for doc in documents:
        for b in doc["data"]["body"]:
            if b.get("visibility", "reader") != "reader" or b["type"] == "code":
                continue
            for text in strings(b):
                for _, target in LINK.findall(text):
                    if target.startswith(("https://", "http://", "mailto:")):
                        continue
                    if "#" not in target:
                        raise ValueError(f"unsupported reference {target}")
                    did, bid = target.split("#", 1)
                    did = did or doc["data"]["id"]
                    if did not in lookup or bid not in lookup[did]["ids"]:
                        raise ValueError(f"unresolved reference {target}")
    listed = {x["path"] for x in documents}
    unlisted = [str(p.relative_to(root)) for p in (root / "book").rglob("*.yaml")
                if p.name != "manifest.yaml" and p.resolve() not in listed]
    if unlisted:
        raise ValueError(f"unlisted publication files: {unlisted}")
    return manifest, documents


def anchor(did, bid=""):
    return did + ("--" + bid if bid else "")


def inline(text, did, pdf=False, pages=None):
    """Small explicit inline subset used by this book; protect code before markup."""
    tokens = {}
    def reserve(value):
        key = f"TOKEN{len(tokens)}END"
        tokens[key] = value
        return key
    text = re.sub(r"`([^`]+)`", lambda m: reserve(("<font name='Courier'>" if pdf else "<code>")
                                                + html.escape(m[1]) + ("</font>" if pdf else "</code>")), str(text))
    def link(m):
        label, target = m.groups()
        if "#" in target and not target.startswith(("http://", "https://")):
            d, b = target.split("#", 1)
            aid = anchor(d or did, b)
            target = "#" + aid
            if pdf and pages and aid in pages:
                label += f" (page {pages[aid]})"
        return reserve(f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>')
    text = LINK.sub(link, text)
    text = html.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    for key, value in tokens.items():
        text = text.replace(key, value)
    return text


CSS = """
:root{font-family:Georgia,serif;color:#1b2937;background:#f4f3ef;line-height:1.65}
body{max-width:1000px;margin:auto;padding:36px}main{background:white;padding:40px}
h1,h2,h3,h4,nav{font-family:Arial,sans-serif}h1{font-size:2.8rem;line-height:1.15}
h2{margin-top:2.5rem;color:#153d50;border-bottom:2px solid #d5e5e5;padding-bottom:.4rem}
h3{margin-top:1.8rem;font-size:1.3rem;color:#17616b}.lead{font-size:1.2rem;color:#344b5d}
a{color:#0b6476}table{border-collapse:collapse;width:100%;font: .92rem Arial,sans-serif}
td,th{padding:12px;border:1px solid #cbd4d8;text-align:left;vertical-align:top}th{background:#e8f0f2}
.table-wrap{overflow-x:auto}caption{text-align:left;font-weight:bold;margin:12px 0}
.callout{padding:16px 22px;background:#edf4f4;border-left:4px solid #18808a;margin:20px 0}
dt{font:bold 1rem Arial,sans-serif;color:#174552;margin-top:15px}dd{margin:4px 0 12px 18px}
pre{overflow-x:auto;background:#152b38;color:#eef4f4;padding:16px;white-space:pre}
code{font-size:.9em}figure{margin:24px 0}figure img{max-width:100%}.chapter{margin-top:50px}
nav{padding:20px;background:#e8f0f2}nav ul{list-style:none;padding-left:20px}
@media(max-width:600px){body{padding:10px}main{padding:18px}h1{font-size:2rem}}
"""


def build_html(manifest, documents):
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'>",
             f"<title>{html.escape(manifest['title'])}</title><meta name='viewport' content='width=device-width,initial-scale=1'>",
             f"<style>{CSS}</style><main><h1>{html.escape(manifest['title'])}</h1>",
             f"<p class='lead'>{html.escape(manifest['subtitle'])}</p><p>Raghav Dinesh</p><nav aria-label='Contents'><b>Contents</b><ul>"]
    for doc in documents:
        d = doc["data"]
        prefix = f"Chapter {doc['number']}. " if doc["kind"] == "chapter" else ""
        parts.append(f'<li><a href="#{d["id"]}">{prefix}{html.escape(d["title"])}</a></li>')
    parts.append("</ul></nav>")
    for doc in documents:
        d, n = doc["data"], doc["number"]
        did = d["id"]
        prefix = f"Chapter {n}. " if n else ""
        parts.append(f'<section class="chapter" id="{did}"><h2>{prefix}{html.escape(d["title"])}</h2>')
        section, tables = 0, 0
        for b in d["body"]:
            if b.get("visibility", "reader") != "reader":
                continue
            t = b["type"]
            fmt = lambda text: inline(text, did)
            aid = f' id="{anchor(did,b["id"])}"' if b.get("id") else ""
            if t == "heading":
                section += 1
                label = f"{n}.{section} " if n and b.get("numbered", True) else ""
                parts.append(f'<h{b["level"]+1}{aid}>{label}{fmt(b["text"])}</h{b["level"]+1}>')
            elif t in ("prose", "lead"):
                parts += [f'<p class="{t}">{fmt(s)}</p>' for s in b["text"].strip().split("\n\n")]
            elif t == "list":
                tag = "ol" if b["style"] == "ordered" else "ul"
                parts.append(f"<{tag}>" + "".join(f"<li>{fmt(x)}</li>" for x in b["items"]) + f"</{tag}>")
            elif t == "fields":
                parts.append(f'<h4>{fmt(b["subject"])}</h4><dl>' + "".join(
                    f'<dt>{fmt(e["label"])}</dt><dd>{fmt(e["value"])}</dd>' for e in b["entries"]) + "</dl>")
            elif t == "steps":
                parts.append("<ol>" + "".join(f'<li><b>{fmt(e["title"])}</b><p>{fmt(e["detail"])}</p></li>' for e in b["items"]) + "</ol>")
            elif t == "callout":
                parts.append(f'<aside class="callout"><b>{fmt(b.get("title",b["variant"]))}</b><p>{fmt(b["text"])}</p></aside>')
            elif t == "code":
                parts.append(f'<pre><code>{html.escape(b["text"])}</code></pre><p>{fmt(b.get("caption",""))}</p>')
            elif t == "table":
                tables += 1
                caption = (f"Table {n}.{tables}. " if n else "") + b.get("caption", "")
                parts.append('<div class="table-wrap"><table><caption>'+fmt(caption)+"</caption><thead><tr>" + "".join(f"<th>{fmt(x)}</th>" for x in b["columns"]) + "</tr></thead><tbody>" + "".join("<tr>"+"".join(f"<td>{fmt(x)}</td>" for x in row)+"</tr>" for row in b["rows"]) + "</tbody></table></div>")
            elif t == "figure":
                src = (doc["path"].parent / b["src"]).resolve()
                import base64
                image = base64.b64encode(src.read_bytes()).decode()
                parts.append(f'<figure><img src="data:image/svg+xml;base64,{image}" alt="{html.escape(b["alt"],quote=True)}"><figcaption>{fmt(b.get("caption",""))}</figcaption></figure>')
        parts.append("</section>")
    parts.append("</main></html>")
    return "\n".join(parts)


def build_pdf(path, manifest, documents, pages=None):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                   PageBreak, Table, TableStyle, Preformatted, KeepTogether, Image)
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    font_dir = Path(os.environ.get("SOM_FONT_DIR", "/usr/share/fonts/truetype/dejavu"))
    for name, file in (("Helvetica", "DejaVuSans.ttf"), ("Helvetica-Bold", "DejaVuSans-Bold.ttf"),
                       ("Courier", "DejaVuSansMono.ttf")):
        if not (font_dir / file).is_file():
            raise ValueError("Install DejaVu fonts or set SOM_FONT_DIR to their directory for PDF output")
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    pdfmetrics.registerFontFamily("Helvetica", normal="Helvetica", bold="Helvetica-Bold")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyManual",fontName="Helvetica",fontSize=9.5,leading=14,spaceAfter=7,
                             textColor=colors.HexColor("#243442"),allowWidows=0,allowOrphans=0))
    styles.add(ParagraphStyle(name="LeadManual",parent=styles["BodyManual"],fontSize=12,leading=18,spaceAfter=18))
    styles.add(ParagraphStyle(name="ChapterManual",fontName="Helvetica-Bold",fontSize=23,leading=28,
                             textColor=colors.HexColor("#153d50"),spaceAfter=20,keepWithNext=True))
    styles.add(ParagraphStyle(name="SectionManual",fontName="Helvetica-Bold",fontSize=13,leading=17,
                             textColor=colors.HexColor("#17616b"),spaceBefore=14,spaceAfter=8,keepWithNext=True))
    styles.add(ParagraphStyle(name="LabelManual",fontName="Helvetica-Bold",fontSize=10,leading=14,
                             textColor=colors.HexColor("#174552"),spaceBefore=6,spaceAfter=3,keepWithNext=True))
    styles.add(ParagraphStyle(name="CellManual",fontName="Helvetica",fontSize=8,leading=11,spaceAfter=0))
    styles.add(ParagraphStyle(name="CodeManual",fontName="Courier",fontSize=8,leading=11,spaceAfter=8))
    styles.add(ParagraphStyle(name="SmallManual",fontName="Helvetica",fontSize=8,leading=11,spaceAfter=8))
    styles.add(ParagraphStyle(name="TitleManual",fontName="Helvetica-Bold",fontSize=35,leading=40,
                             textColor=colors.HexColor("#153d50"),spaceAfter=24))
    pages = {} if pages is None else pages
    class Book(BaseDocTemplate):
        def afterFlowable(self, flowable):
            if getattr(flowable, "bookmark", None):
                key, level, title = flowable.bookmark
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(title, key, level, False)
                pages[key] = self.page
                self.notify("TOCEntry", (level, html.escape(title), self.page, key))
    doc = Book(str(path),pagesize=(595.28,841.89),leftMargin=48,rightMargin=48,
               topMargin=48,bottomMargin=48,title=manifest["title"],author="Raghav Dinesh")
    def footer(canvas, d):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor("#cedadd"))
        canvas.line(48,36,547,36);canvas.setFont("Helvetica",8)
        canvas.setFillColor(colors.HexColor("#526775"))
        canvas.drawString(48,24,"SECURITY OPERATING MANUAL")
        canvas.drawRightString(547,24,str(d.page));canvas.restoreState()
    doc.addPageTemplates(PageTemplate(id="book",frames=[Frame(48,48,499.28,745.89,id="body",leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=footer))
    story = [Spacer(1,95),Paragraph("REFERENCE EDITION",styles["LabelManual"]),
             Paragraph(manifest["title"],styles["TitleManual"]),
             Paragraph(manifest["subtitle"],styles["LeadManual"]),Spacer(1,26),
             Paragraph("Raghav Dinesh",styles["SectionManual"]),
             Paragraph("Curated handbook and offline reference workflow",styles["BodyManual"]),
             Paragraph("Review edition | 31 October 2026",styles["SmallManual"]),PageBreak(),
             Paragraph("Contents",styles["ChapterManual"])]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle(name="TOC0",fontName="Helvetica-Bold",fontSize=10,leading=15,spaceBefore=8),ParagraphStyle(name="TOC1",fontName="Helvetica",fontSize=9,leading=13,leftIndent=14)]
    story += [toc, PageBreak()]
    for idx, item in enumerate(documents):
        d,n = item["data"],item["number"];did=d["id"]
        if idx:story.append(PageBreak())
        title=(f"Chapter {n}. " if n else "")+d["title"]
        para=Paragraph(html.escape(title),styles["ChapterManual"]);para.bookmark=(did,0,title);story.append(para)
        section,tables=0,0
        fmt=lambda text:inline(text,did,pdf=True,pages=pages)
        body=lambda text:Paragraph(fmt(text),styles["BodyManual"])
        for b in d["body"]:
            if b.get("visibility","reader")!="reader":continue
            t=b["type"]
            if t=="heading":
                section+=1;label=(f"{n}.{section} " if n and b.get("numbered",True) else "")+b["text"]
                para=Paragraph(fmt(label),styles["SectionManual"])
                if b.get("id"):para.bookmark=(anchor(did,b["id"]),1,label)
                story.append(para)
            elif t in ("prose","lead"):
                story += [Paragraph(fmt(s),styles["LeadManual"] if t=="lead" else styles["BodyManual"]) for s in b["text"].strip().split("\n\n")]
            elif t=="list":
                for i,x in enumerate(b["items"],1):story.append(body((f"{i}. " if b["style"]=="ordered" else "- ")+x))
            elif t=="fields":
                story.append(Paragraph(fmt(b["subject"]),styles["LabelManual"]))
                for e in b["entries"]:
                    story += [Paragraph(fmt(e["label"]),styles["LabelManual"]),body(e["value"])]
            elif t=="steps":
                for i,e in enumerate(b["items"],1):
                    story += [Paragraph(fmt(f'{i}. {e["title"]}'),styles["LabelManual"]),body(e["detail"])]
            elif t=="callout":
                story.append(KeepTogether([Paragraph(fmt(b.get("title",b["variant"])),styles["LabelManual"]),body(b["text"])]))
            elif t=="code":
                # The authored commands fit the print width; no silent wrapping.
                from reportlab.pdfbase.pdfmetrics import stringWidth
                if any(stringWidth(line,"Courier",8)>499 for line in b["text"].splitlines()):
                    raise ValueError("code wider than print frame; implement continuation marks")
                story.append(Preformatted(b["text"],styles["CodeManual"]))
                if b.get("caption"):story.append(Paragraph(fmt(b["caption"]),styles["SmallManual"]))
            elif t=="table":
                tables+=1;caption=(f"Table {n}.{tables}. " if n else "")+b.get("caption","")
                story.append(Paragraph(fmt(caption),styles["LabelManual"]))
                data=[[Paragraph(fmt(x),styles["CellManual"]) for x in row] for row in [b["columns"],*b["rows"]]]
                widths=b.get("widths",[1]*len(b["columns"]));total=sum(widths)
                tb=Table(data,colWidths=[499*w/total for w in widths],repeatRows=1,hAlign=TA_LEFT)
                tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e8f0f2")),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#becdd1")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
                story += [tb,Spacer(1,12)]
            elif t=="figure":
                # This book uses one pre-rendered architecture PNG for PDF.
                png=(item["path"].parent/b["sources"]["png"]).resolve()
                story += [Image(str(png),width=499,height=290),Paragraph(fmt(b.get("caption","")),styles["SmallManual"])]
    doc.multiBuild(story)
    return pages


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf",action="store_true")
    args=parser.parse_args()
    manifest,documents=read_book()
    out=ROOT/"docs";out.mkdir(exist_ok=True)
    (out/"manual.html").write_text(build_html(manifest,documents))
    if args.pdf:
        pages=build_pdf(out/"security-operating-manual.pdf",manifest,documents)
        # Rebuild the authored paragraphs with the resolved page labels.
        previous=dict(pages)
        expected=dict(previous)
        pages=build_pdf(out/"security-operating-manual.pdf",manifest,documents,previous)
        if pages != expected:
            raise ValueError("cross-reference pagination did not stabilize")
    report={"standard_version":"1.1.0","documents":len(documents),
            "reader_blocks":sum(sum(b.get("visibility","reader")=="reader" for b in d["data"]["body"]) for d in documents),
            "warnings":[],"degraded_blocks":[],"skipped_content":[],
            "scope":"Explicit blocks used by this manual; not a full multi-target standard implementation."}
    (out/"build-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__=="__main__":main()
