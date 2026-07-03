"""A tiny local web page for adding companies by name.

Run it, open the printed URL, type a company name, click Add. It auto-detects
the job board (see resolve.py) and writes the entry into companies.yaml for you.

    python -m watcher.webapp

No external dependencies — uses Python's built-in HTTP server. It listens only on
localhost, so it's not reachable from other machines.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from .add import add_to_file
from .config import DEFAULT_CONFIG_PATH
from .resolve import resolve

HOST, PORT = "127.0.0.1", 8765

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>openings-bot — add a company</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 16px/1.5 system-ui, sans-serif; max-width: 640px; margin: 6vh auto;
         padding: 0 20px; }
  h1 { font-size: 1.4rem; }
  .row { display: flex; gap: 8px; margin: 20px 0; }
  input { flex: 1; padding: 12px; font-size: 1rem; border: 1px solid #8886;
          border-radius: 8px; background: transparent; color: inherit; }
  button { padding: 12px 18px; font-size: 1rem; border: 0; border-radius: 8px;
           background: #3b82f6; color: #fff; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  .card { display: flex; align-items: center; gap: 12px; padding: 12px 14px;
          border: 1px solid #8886; border-radius: 8px; margin: 8px 0; }
  .card .meta { flex: 1; }
  .card small { opacity: .7; }
  .add { background: #16a34a; padding: 8px 14px; }
  #msg { min-height: 1.5em; margin: 8px 0; }
  .err { color: #dc2626; } .ok { color: #16a34a; }
  ul { padding-left: 18px; } li { margin: 2px 0; }
  hr { border: 0; border-top: 1px solid #8884; margin: 28px 0; }
</style></head><body>
<h1>📬 Add a company to track</h1>
<p>Type a company name and press Enter. It figures out the job board for you.</p>
<div class="row">
  <input id="q" placeholder="e.g. Cloudflare" autofocus autocomplete="off">
  <button id="go">Search</button>
</div>
<div id="msg"></div>
<div id="results"></div>
<hr>
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
  <h2 style="font-size:1.1rem; margin:0;">Currently tracking</h2>
  <button id="copy-yaml" style="padding:6px 12px; font-size:0.9rem; background:#4b5563;">Copy for GitHub</button>
</div>
<ul id="tracked"></ul>
<script>
const $ = s => document.querySelector(s);
const msg = (t, cls="") => { $("#msg").textContent = t; $("#msg").className = cls; };

async function loadTracked() {
  const r = await fetch("/api/companies"); const d = await r.json();
  $("#tracked").innerHTML = d.companies.map(c =>
    `<li style="display:flex; justify-content:space-between; margin-bottom:6px; max-width: 400px; align-items:center;">
      <span>${c.name} <small>(${c.platform})</small></span>
      <button class="remove" data-name="${c.name}" style="padding:4px 8px; font-size:0.8rem; background:#dc2626; color:white; border:none; border-radius:4px; cursor:pointer;">Remove</button>
    </li>`).join("") || "<li>none yet</li>";
}

async function search() {
  const name = $("#q").value.trim(); if (!name) return;
  msg("Searching…"); $("#results").innerHTML = "";
  const r = await fetch("/api/resolve?name=" + encodeURIComponent(name));
  const d = await r.json();
  if (!d.matches.length) {
    msg("No auto-detectable board found. This company likely uses Workday or its "
      + "own careers site — add those by hand (see the README).", "err");
    return;
  }
  msg("");
  $("#results").innerHTML = d.matches.map(m => {
    let finalName = m.proper_name || name;
    if (!m.proper_name) finalName = finalName.charAt(0).toUpperCase() + finalName.slice(1).toLowerCase();
    return `
    <div class="card">
      <div class="meta"><b>${m.platform}</b> · <code>${m.token}</code>
        <br><small>${m.job_count} open postings</small></div>
      <button class="add" data-name="${finalName}" data-platform="${m.platform}"
        data-token="${m.token}">Add</button>
    </div>`;
  }).join("");
}

$("#tracked").addEventListener("click", async e => {
  const b = e.target.closest(".remove"); if (!b) return;
  if (!confirm(`Remove ${b.dataset.name}?`)) return;
  b.disabled = true; b.textContent = "...";
  const r = await fetch("/api/remove", { method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ name: b.dataset.name }) });
  const d = await r.json();
  if (d.ok) { msg(`Removed ${b.dataset.name}.`, "ok"); loadTracked(); }
  else { msg(d.error || "Failed to remove.", "err"); b.disabled = false; b.textContent = "Remove"; }
});

$("#results").addEventListener("click", async e => {
  const b = e.target.closest(".add"); if (!b) return;
  b.disabled = true;
  const r = await fetch("/api/add", { method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ name: b.dataset.name, platform: b.dataset.platform, token: b.dataset.token }) });
  const d = await r.json();
  if (d.ok) { msg(`Added ${b.dataset.name}. Remember to update your COMPANIES_YAML secret.`, "ok");
              loadTracked(); }
  else { msg(d.error || "Failed to add.", "err"); b.disabled = false; }
});

$("#copy-yaml").onclick = async e => {
  const b = e.target;
  const orig = b.textContent;
  b.textContent = "Copying..."; b.disabled = true;
  try {
    const r = await fetch("/api/yaml"); const d = await r.json();
    await navigator.clipboard.writeText(d.yaml);
    b.textContent = "Copied!";
  } catch (err) {
    b.textContent = "Failed";
  }
  setTimeout(() => { b.textContent = orig; b.disabled = false; }, 2000);
};

$("#go").onclick = search;
$("#q").addEventListener("keydown", e => { if (e.key === "Enter") search(); });
loadTracked();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    config_path = DEFAULT_CONFIG_PATH

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self) -> None:
        parts = urlparse(self.path)
        if parts.path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif parts.path == "/api/resolve":
            name = (parse_qs(parts.query).get("name") or [""])[0]
            matches = resolve(name) if name.strip() else []
            self._json(200, {"matches": [vars(m) for m in matches]})
        elif parts.path == "/api/companies":
            self._json(200, {"companies": self._current_companies()})
        elif parts.path == "/api/yaml":
            content = self.config_path.read_text(encoding="utf-8") if self.config_path.exists() else ""
            self._json(200, {"yaml": content})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/remove":
            length = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(length) or b"{}")
                name_to_remove = req["name"]
            except (ValueError, KeyError):
                self._json(400, {"error": "bad request"})
                return
            if not self.config_path.exists():
                self._json(200, {"ok": True})
                return
            with self.config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            companies = data.get("companies", [])
            data["companies"] = [c for c in companies if c.get("name") != name_to_remove]
            with self.config_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
            self._json(200, {"ok": True})
            return

        if path != "/api/add":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
            entry = {"name": req["name"], "platform": req["platform"], "token": req["token"]}
        except (ValueError, KeyError):
            self._json(400, {"error": "bad request"})
            return
        try:
            add_to_file(entry, self.config_path)
        except SystemExit as e:  # add_to_file raises SystemExit on duplicates
            self._json(409, {"error": str(e)})
            return
        self._json(200, {"ok": True})

    def _current_companies(self) -> list[dict]:
        if not self.config_path.exists():
            return []
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        return [
            {"name": c.get("name", "?"), "platform": c.get("platform", "?")}
            for c in data.get("companies", [])
        ]

    def log_message(self, *_args) -> None:  # quiet the default request logging
        pass


def main() -> int:
    Handler.config_path = Path(DEFAULT_CONFIG_PATH)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"openings-bot is running at  http://{HOST}:{PORT}")
    print("Open that in your browser. Press Ctrl+C here to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
