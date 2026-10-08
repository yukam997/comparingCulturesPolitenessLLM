"""
Fetch random Wikipedia talk pages of at least --min-bytes (default 6,000) via the
MediaWiki API, balanced across article talk (namespace 1) and user talk (namespace 3).

Most random talk pages are short or template-only, so each request asks for
500 random titles with their sizes only, keeps non-redirect pages of at
least --min-bytes, and then fetches the content of those pages 50 at a
time. This yields about ten times more usable sentences per page than
taking random pages as they come. The same byte threshold is used for both
languages: Japanese takes about 3 bytes per character and carries more per
character, so a given byte count is roughly the same amount of discussion
in either. Requests alternate between the namespaces, about one per second.

Output is wiki_corpus/raw/{en,jp}_talk_pages.jsonl, one
{"title", "ns", "length", "text"} per line. It appends, so the script can be
rerun to grow the sample; per-namespace targets count pages already there.

Usage:
  python wiki_corpus/fetch_talk_pages.py --lang en --ns1 1500 --ns3 3500
  python wiki_corpus/fetch_talk_pages.py --lang ja --ns1 3700 --ns3 8700
"""

import argparse
import collections
import json
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("crossCulturalPolitenessResearch/0.1 "
      "(academic research; github.com/yukam997/crossCulturalPolitenessOfModifiers)")
FILE_LANG = {"en": "en", "ja": "jp"}
REDIRECT = ("#redirect", "#転送")


def out_path(lang):
    return os.path.join(HERE, "raw", f"{FILE_LANG[lang]}_talk_pages.jsonl")


def get(sess, api, params):
    """GET with retries; returns the parsed JSON or None."""
    params = {"action": "query", "format": "json", "formatversion": "2",
              "maxlag": "5", **params}
    try:
        data = sess.get(api, params=params, timeout=60).json()
    except Exception as e:
        print(f"request failed ({e}); sleeping 10s", flush=True)
        time.sleep(10)
        return None
    if "error" in data:                    # maxlag etc.
        time.sleep(5)
        return None
    return data


def page_records(data, seen):
    for page in data.get("query", {}).get("pages", []):
        revs = page.get("revisions")
        title = page.get("title", "")
        if not revs or title in seen:
            continue
        text = revs[0].get("slots", {}).get("main", {}).get("content", "")
        if not text or text.lstrip().lower().startswith(REDIRECT):
            continue
        yield {"title": title, "ns": page.get("ns"),
               "length": len(text.encode("utf-8")), "text": text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=list(FILE_LANG), required=True)
    ap.add_argument("--per-ns", type=int, default=10000,
                    help="target number of pages per namespace")
    ap.add_argument("--ns1", type=int, default=None,
                    help="override the article-talk target")
    ap.add_argument("--ns3", type=int, default=None,
                    help="override the user-talk target")
    ap.add_argument("--min-bytes", type=int, default=6000,
                    help="only fetch pages at least this large; 0 takes "
                         "random pages as they come")
    args = ap.parse_args()
    target = {1: args.ns1 or args.per_ns, 3: args.ns3 or args.per_ns}

    out = out_path(args.lang)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    have = collections.Counter()
    seen = set()
    if os.path.exists(out):
        for line in open(out, encoding="utf-8"):
            rec = json.loads(line)
            seen.add(rec["title"])
            have[rec["ns"]] += 1
    print(f"starting with {dict(have)}; targets {target}", flush=True)

    api = f"https://{args.lang}.wikipedia.org/w/api.php"
    sess = requests.Session()
    sess.headers["User-Agent"] = UA
    ns_cycle = [1, 3]
    queue = {1: [], 3: []}                 # size-filtered titles awaiting content
    scanned = collections.Counter()
    turn = 0
    with open(out, "a", encoding="utf-8") as f:
        while any(have[ns] < target[ns] for ns in ns_cycle):
            ns = ns_cycle[turn % 2]
            turn += 1
            if have[ns] >= target[ns]:
                continue
            if not args.min_bytes:
                data = get(sess, api, {
                    "generator": "random", "grnnamespace": str(ns),
                    "grnlimit": "50", "prop": "revisions", "rvprop": "content",
                    "rvslots": "main"})
                recs = list(page_records(data, seen)) if data else []
            elif len(queue[ns]) < 50:
                data = get(sess, api, {
                    "generator": "random", "grnnamespace": str(ns),
                    "grnlimit": "500", "prop": "info"})
                for page in (data or {}).get("query", {}).get("pages", []):
                    scanned[ns] += 1
                    if not page.get("redirect") and \
                            page.get("length", 0) >= args.min_bytes and \
                            page["title"] not in seen and \
                            page["title"] not in queue[ns]:
                        queue[ns].append(page["title"])
                recs = []
            else:
                batch, queue[ns] = queue[ns][:50], queue[ns][50:]
                data = get(sess, api, {
                    "titles": "|".join(batch), "prop": "revisions",
                    "rvprop": "content", "rvslots": "main"})
                recs = list(page_records(data, seen)) if data else []
                if data is None:
                    queue[ns] = batch + queue[ns]
            for rec in recs:
                if have[rec["ns"]] >= target[rec["ns"]]:
                    continue
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                seen.add(rec["title"])
                have[rec["ns"]] += 1
            f.flush()
            if turn % 40 == 0:
                extra = (f"; scanned {dict(scanned)}" if args.min_bytes else "")
                print(f"{dict(have)}{extra}", flush=True)
            time.sleep(1.0)
    print(f"done: {dict(have)} -> {out}", flush=True)


if __name__ == "__main__":
    main()
