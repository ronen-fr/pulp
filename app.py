#!/usr/bin/env python3
import html
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen


APP_TITLE = "Pulpito Branch Board"
DEFAULT_URL_TEMPLATE = "https://pulpito-ng.ceph.com/runs?branch={branch}"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_ROW_HEIGHT = 720
DEFAULT_TIMEOUT = 20
DEFAULT_REFRESH_SECONDS = 0
USER_AGENT = "pulp-branch-board/1.0"


def env_int(name, default):
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def current_config():
    return {
        "branch_file": os.environ.get("PULP_BRANCH_FILE", "").strip(),
        "url_template": os.environ.get("PULP_URL_TEMPLATE", DEFAULT_URL_TEMPLATE).strip() or DEFAULT_URL_TEMPLATE,
        "host": os.environ.get("PULP_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST,
        "port": env_int("PULP_PORT", DEFAULT_PORT),
        "row_height": env_int("PULP_ROW_HEIGHT", DEFAULT_ROW_HEIGHT),
        "refresh_seconds": env_int("PULP_REFRESH_SECONDS", DEFAULT_REFRESH_SECONDS),
        "request_timeout": env_int("PULP_REQUEST_TIMEOUT", DEFAULT_TIMEOUT),
    }


def read_branches(branch_file):
    if not branch_file:
        raise ValueError("PULP_BRANCH_FILE is not set")
    if not os.path.exists(branch_file):
        raise FileNotFoundError(f"Branch file not found: {branch_file}")

    branches = []
    with open(branch_file, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            branches.append(line)
    return branches


def build_target_url(url_template, branch):
    return url_template.format(branch=quote(branch, safe=""))


def inject_base_tag(content_type, body, target_url):
    if "text/html" not in content_type.lower():
        return body

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body

    base_tag = f'<base href="{html.escape(target_url, quote=True)}">'
    lower_text = text.lower()
    head_index = lower_text.find("<head>")
    if head_index != -1:
        insertion_point = head_index + len("<head>")
        text = text[:insertion_point] + base_tag + text[insertion_point:]
    else:
        text = base_tag + text
    return text.encode("utf-8")


def fetch_remote(url, timeout):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "text/html; charset=utf-8")
        return response.status, content_type, inject_base_tag(content_type, body, url)


def page_template(body, refresh_seconds=0):
    refresh = ""
    if refresh_seconds > 0:
        refresh = f'<meta http-equiv="refresh" content="{refresh_seconds}">' 

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  {refresh}
  <title>{APP_TITLE}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe4;
      --panel: #fffdf8;
      --ink: #1d1b18;
      --muted: #6d675f;
      --line: #d8cfbf;
      --accent: #0d6c61;
      --accent-soft: #dff0ea;
      --shadow: rgba(43, 35, 21, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iosevka Aile", "IBM Plex Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff6d8 0, transparent 28%),
        linear-gradient(180deg, #efe5d2 0%, var(--bg) 24%, #ece8df 100%);
    }}
    .shell {{
      width: min(1600px, calc(100vw - 24px));
      margin: 12px auto 40px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(255,255,255,0.72), rgba(255,253,248,0.92));
      border: 1px solid rgba(216, 207, 191, 0.9);
      border-radius: 20px;
      box-shadow: 0 20px 60px var(--shadow);
      padding: 20px 24px;
      backdrop-filter: blur(10px);
    }}
    h1 {{
      margin: 0;
      font-family: "IBM Plex Serif", Georgia, serif;
      font-size: clamp(1.9rem, 3vw, 3.2rem);
      line-height: 1;
      letter-spacing: -0.04em;
    }}
    .subtitle {{
      margin: 10px 0 0;
      color: var(--muted);
      max-width: 70ch;
      line-height: 1.45;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .badge {{
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid rgba(13, 108, 97, 0.16);
      border-radius: 999px;
      padding: 7px 12px;
      font-size: 0.92rem;
    }}
    .notice {{
      margin-top: 16px;
      padding: 14px 16px;
      border-radius: 14px;
      border: 1px solid #efd0b1;
      background: #fff0df;
      color: #73420e;
    }}
    .rows {{
      display: grid;
      gap: 18px;
      margin-top: 18px;
    }}
    .row {{
      background: rgba(255, 253, 248, 0.92);
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: clip;
      box-shadow: 0 18px 50px var(--shadow);
    }}
    .row-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(247,242,233,0.92));
      border-bottom: 1px solid var(--line);
    }}
    .row-title {{
      font-size: 1.15rem;
      font-weight: 700;
      word-break: break-word;
    }}
    .row-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    a {{
      color: var(--accent);
      text-decoration-thickness: 0.08em;
      text-underline-offset: 0.16em;
    }}
    iframe {{
      display: block;
      width: 100%;
      height: var(--row-height, 720px);
      border: 0;
      background: white;
    }}
    .empty {{
      padding: 18px;
      color: var(--muted);
    }}
    @media (max-width: 800px) {{
      .shell {{ width: min(100vw - 10px, 1600px); margin-top: 6px; }}
      .hero {{ padding: 16px; border-radius: 16px; }}
      .row-head {{ align-items: flex-start; flex-direction: column; }}
      iframe {{ height: min(70vh, var(--row-height, 720px)); }}
    }}
  </style>
</head>
<body>
  {body}
</body>
</html>
"""


class BranchBoardHandler(BaseHTTPRequestHandler):
    server_version = "BranchBoard/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.handle_index()
            return
        if parsed.path == "/proxy":
            self.handle_proxy(parsed.query)
            return
        self.send_error(404, "Not Found")

    def handle_index(self):
        config = current_config()
        try:
            branches = read_branches(config["branch_file"])
        except (ValueError, FileNotFoundError) as exc:
            body = f"""
            <main class=\"shell\">
              <section class=\"hero\">
                <h1>{APP_TITLE}</h1>
                <p class=\"subtitle\">Read branch names from a file and render one proxied Pulpito result per row.</p>
                <div class=\"notice\">{html.escape(str(exc))}</div>
              </section>
            </main>
            """
            self.respond_html(page_template(body, config["refresh_seconds"]))
            return

        row_height = max(240, config["row_height"])
        rows = []
        for branch in branches:
            target_url = build_target_url(config["url_template"], branch)
            proxy_query = urlencode({"branch": branch})
            rows.append(
                f"""
                <article class=\"row\" style=\"--row-height: {row_height}px\">
                  <div class=\"row-head\">
                    <div class=\"row-title\">{html.escape(branch)}</div>
                    <div class=\"row-actions\">
                      <span>{html.escape(target_url)}</span>
                      <a href=\"{html.escape(target_url, quote=True)}\" target=\"_blank\" rel=\"noreferrer\">open remote</a>
                    </div>
                  </div>
                  <iframe loading=\"lazy\" src=\"/proxy?{proxy_query}\" title=\"{html.escape(branch, quote=True)}\"></iframe>
                </article>
                """
            )

        rows_markup = "\n".join(rows) if rows else '<div class="row"><div class="empty">No branches found in the file.</div></div>'
        refresh_note = "manual refresh"
        if config["refresh_seconds"] > 0:
            refresh_note = f"auto refresh every {config['refresh_seconds']}s"
        body = f"""
        <main class=\"shell\">
          <section class=\"hero\">
            <h1>{APP_TITLE}</h1>
            <p class=\"subtitle\">Each row is built from the configured URL template with the branch name substituted into <code>{{branch}}</code>, then fetched by this local server so the page can stay on one browser tab.</p>
            <div class=\"meta\">
              <div class=\"badge\">branches: {len(branches)}</div>
              <div class=\"badge\">source: {html.escape(config['branch_file'])}</div>
              <div class=\"badge\">row height: {row_height}px</div>
              <div class=\"badge\">{html.escape(refresh_note)}</div>
            </div>
          </section>
          <section class=\"rows\">{rows_markup}</section>
        </main>
        """
        self.respond_html(page_template(body, config["refresh_seconds"]))

    def handle_proxy(self, query):
        params = parse_qs(query)
        branch = params.get("branch", [""])[0]
        config = current_config()
        try:
            branches = set(read_branches(config["branch_file"]))
        except (ValueError, FileNotFoundError) as exc:
            self.respond_text(str(exc), 500)
            return

        if not branch or branch not in branches:
            self.respond_text("Unknown branch", 404)
            return

        target_url = build_target_url(config["url_template"], branch)
        try:
            status, content_type, body = fetch_remote(target_url, config["request_timeout"])
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except HTTPError as exc:
            self.respond_text(f"Remote HTTP error for {branch}: {exc.code}", exc.code)
        except URLError as exc:
            self.respond_text(f"Remote fetch failed for {branch}: {exc.reason}", 502)

    def respond_html(self, payload, status=200):
        encoded = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def respond_text(self, payload, status=200):
        encoded = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format_string, *args):
        return


def main():
    config = current_config()
    server = ThreadingHTTPServer((config["host"], config["port"]), BranchBoardHandler)
    print(f"Serving {APP_TITLE} on http://{config['host']}:{config['port']}")
    server.serve_forever()


if __name__ == "__main__":
    main()