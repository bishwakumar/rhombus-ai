#!/usr/bin/env python3
"""Serve the dashboard from the stored data.json.

The page reads dashboard/data.json, which is committed with the repo, so nothing is rebuilt by default.
Use --rebuild to regenerate data.json from results/ and outputs/ first (after new test runs).
"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rebuild():
    subprocess.check_call([sys.executable, str(HERE / "build.py")])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--rebuild", action="store_true",
                        help="regenerate data.json from results/ and outputs/ before serving")
    args = parser.parse_args()
    if args.rebuild:
        rebuild()
    elif not (HERE / "data.json").exists():
        sys.exit("dashboard/data.json not found. Run: python3 dashboard/build.py")

    os.chdir(HERE)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *rest):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % rest))

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
        url = f"http://{args.host}:{args.port}/"
        print(url)
        print("Serving dashboard. Ctrl+C to stop.")
        httpd.serve_forever()


if __name__ == "__main__":
    main()