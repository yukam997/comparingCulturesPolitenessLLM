"""
Attach discussion context to each sampled sentence for attitude labeling.

For every row of attitude_results/attitude_sample.csv, rebuilds the page's
signed comments with the same splitter the extractor used
(extract_experiment_modifiers.split_comments), so both languages get
identical treatment, and adds:
  comment       the writer's comment, with the target sentence replaced by
                <target>{masked_sentence}</target>
  prev_comment  the previous comment in the same section, if any
  section       the section heading
Long comments are trimmed to a window around the target sentence.

Output: attitude_results/attitude_sample_context.csv
"""

import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract_experiment_modifiers import clean, split_comments  # noqa: E402

OUT_DIR = os.path.join(HERE, "attitude_results")
SAMPLE = os.path.join(OUT_DIR, "attitude_sample.csv")
OUT = os.path.join(OUT_DIR, "attitude_sample_context.csv")

COMMENT_CHARS = 1500     # window kept around the target in the writer's comment
PREV_CHARS = 800         # kept from the end of the previous comment


def window(text: str, start: int, end: int, size: int) -> str:
    if len(text) <= size:
        return text
    pad = max(0, (size - (end - start)) // 2)
    lo, hi = max(0, start - pad), min(len(text), end + pad)
    return ("… " if lo > 0 else "") + text[lo:hi] + (" …" if hi < len(text) else "")


def page_comments(lang: str, titles: set) -> dict:
    """title -> list of (section, ix, cleaned comment text)."""
    out = {}
    path = os.path.join(HERE, "raw", f"{lang}_talk_pages.jsonl")
    with open(path, encoding="utf-8") as f:
        for line in f:
            page = json.loads(line)
            if page["title"] in titles:
                out[page["title"]] = [(sec, ix, clean(txt)) for sec, ix, txt
                                      in split_comments(page.get("text", "") or "", lang)]
    return out


def context_for(row, comments):
    by_ix = {ix: (sec, txt) for sec, ix, txt in comments}
    sec, txt = by_ix.get(row.comment_ix, ("", ""))
    i = txt.find(row.sentence)
    if i < 0:
        comment = f"<target>{row.masked_sentence}</target>"
    else:
        tagged = f"<target>{row.masked_sentence}</target>"
        marked = txt[:i] + tagged + txt[i + len(row.sentence):]
        comment = window(marked, i, i + len(tagged), COMMENT_CHARS)
    prev_sec, prev = by_ix.get(row.comment_ix - 1, (None, ""))
    if prev_sec != sec:
        prev = ""
    if len(prev) > PREV_CHARS:
        prev = "… " + prev[-PREV_CHARS:]
    return comment, prev, sec, i >= 0


def main():
    df = pd.read_csv(SAMPLE, keep_default_na=False)
    cols = {"comment": [], "prev_comment": [], "section": [], "found": []}
    cache = {lang: page_comments(lang, set(g["page"]))
             for lang, g in df.groupby("lang")}
    for row in df.itertuples():
        c, p, s, found = context_for(row, cache[row.lang].get(row.page, []))
        for k, v in zip(cols, (c, p, s, found)):
            cols[k].append(v)
    for k, v in cols.items():
        df[k] = v
    df.drop(columns=["found"]).to_csv(OUT, index=False)
    print(f"wrote {OUT}")
    for (lang, ns), g in df.groupby(["lang", "ns"]):
        print(f"  {lang} ns={ns}: {len(g)} rows, target found in its comment "
              f"{g['found'].mean():.0%}, previous comment available "
              f"{(g['prev_comment'] != '').mean():.0%}")


if __name__ == "__main__":
    main()
