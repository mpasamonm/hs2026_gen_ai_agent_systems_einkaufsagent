"""Render a .bpmn with bpmn-js (NavigatedViewer) in headless Chromium and save PNG + SVG.
Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 render.py in.bpmn out.png [out.svg]
"""
import json, sys, pathlib
from playwright.sync_api import sync_playwright

src, png = sys.argv[1], sys.argv[2]
svg_out = sys.argv[3] if len(sys.argv) > 3 else None
xml = pathlib.Path(src).read_text(encoding="utf-8")
base = pathlib.Path(__file__).parent / "node_modules/bpmn-js/dist"
html = f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{base}/assets/bpmn-js.css">
<style>html,body{{margin:0;background:#fff}} #c{{width:100vw;height:100vh}}</style>
<script src="file://{base}/bpmn-navigated-viewer.production.min.js"></script></head>
<body><div id="c"></div></body></html>"""
page_file = pathlib.Path(__file__).parent / "render.html"
page_file.write_text(html, encoding="utf-8")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 3100, "height": 1000}, device_scale_factor=1.5)
    pg.goto(f"file://{page_file}")
    res = pg.evaluate("""async (xml) => {
        const v = new BpmnJS({ container: '#c' });
        const r = await v.importXML(xml);
        v.get('canvas').zoom('fit-viewport', 'auto');
        const { svg } = await v.saveSVG();
        return { warnings: r.warnings.map(w => w.message), svg };
    }""", xml)
    print("bpmn-js import warnings:", len(res["warnings"]))
    for w in res["warnings"]:
        print("  -", w)
    pg.screenshot(path=png, full_page=False)
    if svg_out:
        pathlib.Path(svg_out).write_text(res["svg"], encoding="utf-8")
    b.close()
print("saved", png)
