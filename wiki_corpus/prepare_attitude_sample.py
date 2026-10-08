"""
Prepare the sample of extracted sentences for attitude labeling.

Input: {en,jp}_experiment_modifier_sentences.csv from
extract_experiment_modifiers.py (already masked; every hit is a modifier
directly modifying an adjective).

Cleaning, per language:
- template families are dropped: sentences of at least TEMPLATE_MIN_CHARS
  whose normalized text, or first or last 40 characters, recur on
  TEMPLATE_PAGES or more different pages (mass messages and welcome/warning
  templates, which differ only in a username or date);
- a masked sentence that still occurs more than once is kept once;
- at most PAGE_CAP sentences per page, so a few long, contentious pages
  can't dominate.

Sampling: within each venue (article talk, ns 1; user talk, ns 3) the same
number of sentences is labeled in both languages: the smaller language's
pool, up to PER_VENUE. When a pool is larger than that, it is sampled
stratified by modifier (each modifier gets at least FLOOR sentences, or all
it has, and the rest is allocated in proportion to frequency). The analysis
reweights each sentence by corpus_count / (number labeled for that modifier
in that venue), restoring corpus proportions within a venue.

Output: attitude_results/attitude_sample.csv

Usage: python wiki_corpus/prepare_attitude_sample.py [--per-venue 1500]
"""

import hashlib
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract_experiment_modifiers import EN_MODIFIERS, JP_MODIFIERS  # noqa: E402

OUT_DIR = os.path.join(HERE, "attitude_results")
TEMPLATE_MIN_CHARS = {"en": 40, "jp": 25}
TEMPLATE_PAGES = 3
PAGE_CAP = 25
PER_VENUE = 1500
FLOOR = 20
SEED = 0
VENUES = (1, 3)


def norm(s: str) -> str:
    s = re.sub(r"[0-9０-９]+", "", str(s).lower())
    return re.sub(r"\s+", " ", s).strip()


def clean_pool(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    # template detection runs before deduplication, so every copy of a
    # template counts toward the number of pages it appears on
    n0 = len(df)
    s = df["masked_sentence"].map(norm)
    long = s.str.len() >= TEMPLATE_MIN_CHARS[lang]
    templ = pd.Series(False, index=df.index)
    for key in (s, s.str[:40], s.str[-40:]):
        pages = df.loc[long].groupby(key[long])["page"].nunique()
        frequent = set(pages[pages >= TEMPLATE_PAGES].index)
        templ |= long & key.isin(frequent)
    df = df[~templ]
    n1 = len(df)
    df = df.drop_duplicates(subset=["masked_sentence"])
    n2 = len(df)
    df = (df.sample(frac=1, random_state=SEED)
            .groupby("page", group_keys=False).head(PAGE_CAP))
    print(f"{lang}: {n0} hits -> {n1} after dropping template families -> "
          f"{n2} after exact dedupe -> {len(df)} after capping {PAGE_CAP} "
          f"per page")
    return df


def allocate(counts: pd.Series, total: int) -> dict:
    """Per-modifier sample sizes: a floor each (FLOOR, lowered if the floors
    alone would exceed the total), the rest in proportion to frequency,
    never exceeding what is available."""
    floor = FLOOR
    while floor > 0 and counts.clip(upper=floor).sum() > total:
        floor -= 1
    n = counts.clip(upper=floor)
    budget = total - n.sum()
    while budget > 0:
        room = counts - n
        open_ = room > 0
        if not open_.any():
            break
        share = counts[open_] / counts[open_].sum()
        add = np.minimum(np.floor(share * budget).astype(int), room[open_])
        if add.sum() == 0:                       # hand out the remainder
            add = (room[open_] > 0).astype(int)
            add = add[add.cumsum() <= budget]
        n[add.index] += add
        budget = total - n.sum()
    return n.to_dict()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-venue", type=int, default=PER_VENUE,
                    help="max sentences per language per venue")
    per_venue = ap.parse_args().per_venue
    pools = {}
    for lang, mods in [("en", EN_MODIFIERS), ("jp", JP_MODIFIERS)]:
        df = pd.read_csv(os.path.join(HERE, f"{lang}_experiment_modifier_sentences.csv"))
        df = df[df["modifier"].isin(mods) & df["ns"].isin(VENUES)]
        pools[lang] = clean_pool(df, lang)

    parts = []
    for ns in VENUES:
        size = min(per_venue, *(len(p[p["ns"] == ns]) for p in pools.values()))
        for lang, pool in pools.items():
            v = pool[pool["ns"] == ns]
            counts = v["modifier"].value_counts()
            n = allocate(counts, size)
            take = (v.groupby("modifier", group_keys=False)[v.columns]
                      .apply(lambda g: g.sample(n[g.name], random_state=SEED)))
            take = take.assign(corpus_count=take["modifier"].map(counts))
            parts.append(take)
            print(f"  ns={ns} {lang}: pool {len(v)}, labeling {len(take)}")

    both = pd.concat(parts, ignore_index=True)
    both.insert(0, "id", [
        f"{l}-{hashlib.md5(s.encode()).hexdigest()[:10]}"
        for l, s in zip(both["lang"], both["masked_sentence"])])
    both = both.drop_duplicates(subset=["id"])
    cols = ["id", "lang", "ns", "page", "section", "comment_ix", "modifier",
            "adjective", "negated", "predicative", "corpus_count",
            "sentence", "masked_sentence"]
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "attitude_sample.csv")
    both[cols].to_csv(out, index=False)
    print(f"wrote {len(both)} rows -> {out}")


if __name__ == "__main__":
    main()
