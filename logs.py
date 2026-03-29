#!/usr/bin/env python3
"""
Quick CLI to tail / query Elasticsearch logs.

Usage:
  python logs.py                  # last 20 logs
  python logs.py --type error     # only errors
  python logs.py --type http      # HTTP requests
  python logs.py --type slow      # slow queries
  python logs.py --type lifecycle # startup/shutdown
  python logs.py --n 50           # last 50 logs
  python logs.py --today          # only today's index
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import os
import ssl
import urllib.request
from base64 import b64encode
from datetime import datetime, timezone

ES_HOST        = os.getenv("ES_HOST",        "http://localhost:9200")
ES_USER        = os.getenv("ES_USER",        "elastic")
ES_PASSWORD    = os.getenv("ES_PASSWORD",    "changeme")
ES_VERIFY_SSL  = os.getenv("ES_VERIFY_SSL",  "1") == "1"
AUTH           = b64encode(f"{ES_USER}:{ES_PASSWORD}".encode()).decode()

def _ssl_ctx():
    if ES_VERIFY_SSL:
        return None   # use default (full verification)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

TYPE_MAP = {
    "error":     "app_error",
    "http":      "http_request",
    "slow":      "slow_query",
    "lifecycle": "lifecycle",
    "log":       "python_log",
}

COLORS = {
    "ERROR":   "\033[91m",   # red
    "WARNING": "\033[93m",   # yellow
    "INFO":    "\033[92m",   # green
    "RESET":   "\033[0m",
}


def search(query: dict, index: str = "budget-logs-*") -> list:
    url  = f"{ES_HOST}/{index}/_search"
    body = json.dumps(query).encode()
    req  = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Basic {AUTH}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5, context=_ssl_ctx()) as res:
            data = json.loads(res.read())
            return data.get("hits", {}).get("hits", [])
    except Exception as e:
        print(f"\033[91mCannot connect to Elasticsearch: {e}\033[0m")
        print(f"Make sure ES is running at {ES_HOST}")
        return []


def fmt_hit(hit: dict) -> str:
    s   = hit["_source"]
    ts  = s.get("@timestamp", "")[:19].replace("T", " ")
    lvl = s.get("level", "INFO")
    t   = s.get("type", "")
    col = COLORS.get(lvl, "")
    rst = COLORS["RESET"]

    if t == "http_request":
        status = s.get("status", "")
        dur    = s.get("duration_ms", "")
        return f"{col}[{ts}] {lvl:7} HTTP {s.get('method',''):6} {s.get('path',''):40} {status}  {dur}ms{rst}"

    elif t == "app_error":
        tb = s.get("traceback", "").strip().split("\n")[-1]
        return (f"{col}[{ts}] {lvl:7} ERROR {s.get('error','')} — {s.get('message','')}\n"
                f"           {tb}{rst}")

    elif t == "slow_query":
        sql = s.get("sql", "")[:80]
        return f"{col}[{ts}] {lvl:7} SLOW QUERY ({s.get('duration_ms','')}ms) {sql}{rst}"

    elif t == "lifecycle":
        return f"{col}[{ts}] {lvl:7} ⚡ {s.get('event','').upper()} — {s.get('detail','')}{rst}"

    else:
        return f"{col}[{ts}] {lvl:7} [{t}] {s.get('message', json.dumps(s))}{rst}"


def main():
    parser = argparse.ArgumentParser(description="Query budget-app ES logs")
    parser.add_argument("--type",  choices=list(TYPE_MAP.keys()), help="Filter by log type")
    parser.add_argument("--n",     type=int, default=20,          help="Number of results (default 20)")
    parser.add_argument("--today", action="store_true",           help="Query only today's index")
    parser.add_argument("--level", choices=["INFO","WARNING","ERROR"], help="Filter by log level")
    args = parser.parse_args()

    query: dict = {"query": {"bool": {"must": []}}, "sort": [{"@timestamp": "desc"}], "size": args.n}

    if args.type:
        query["query"]["bool"]["must"].append({"term": {"type": TYPE_MAP[args.type]}})
    if args.level:
        query["query"]["bool"]["must"].append({"term": {"level": args.level}})
    if not query["query"]["bool"]["must"]:
        query["query"] = {"match_all": {}}

    index = f"budget-logs-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}" if args.today else "budget-logs-*"

    print(f"\n{'─'*70}")
    print(f"  ES: {ES_HOST}   index: {index}   showing: {args.n}")
    print(f"{'─'*70}\n")

    hits = search(query, index)
    if not hits:
        print("  No logs found.")
    else:
        for hit in reversed(hits):    # show oldest first
            print(fmt_hit(hit))

    print()


if __name__ == "__main__":
    main()
