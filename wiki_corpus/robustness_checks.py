"""
Robustness of the English vs Japanese comparison to analysis choices.

Every row re-runs the floor-adjusted JSD estimator from plot_jsd_effect.py
(fewer shuffles and bootstrap draws, for speed) under one alternative:

Experiment
  main                 30 candidate modifiers; 1/k weights over all of a
                       trial's responses
  reweight after       1/k recomputed over the trial's candidate responses
  full vocabulary      every response type given at least 5 times
  top-30 per language  each language's 30 most frequent response types
Corpus
  main                 both venues, equal weight
  article talk only    namespace 1
  user talk only       namespace 3
  given negation       effect computed separately for negated and
                       affirmative uses, then averaged by weight, so the
                       link between negation and attitude can't contribute
  predicative only     adjective not followed by a noun
  confidence >= 2      labels Claude was at least reasonably sure of

Output: printed table and attitude_results/robustness.csv
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compare_human_wiki import MODS, OUT_DIR, load_human, load_wiki  # noqa: E402
from plot_jsd_effect import Data, analyze, fmt_p  # noqa: E402

N_PERM = 500
N_BOOT = 400
K_FLOOR = 5
SEED = 0


def run(df, mods, rng):
    return analyze(Data(df, mods, "doc_id", "trial"), rng,
                   n_perm=N_PERM, n_boot=N_BOOT, k_floor=K_FLOOR)


def stratified(df, mods, col, rng):
    """Weighted average of the effect within each level of `col`."""
    parts = [(g["w"].sum(), run(g, mods, rng)) for _, g in df.groupby(col)]
    tot = sum(w for w, _ in parts)
    return dict(effect=sum(w * s["effect"] for w, s in parts) / tot,
                adj_boot=sum(w * s["adj_boot"] for w, s in parts) / tot,
                n_rows=sum(s["n_rows"] for _, s in parts))


def human_variant(lang, variant):
    if variant == "main":
        return load_human(lang, quiet=True), MODS[lang]
    if variant == "reweight after":
        df = load_human(lang, quiet=True)
        df["w"] = 1.0 / df.groupby("trial")["modifier"].transform("count")
        return df, MODS[lang]
    df = load_human(lang, restrict=False, quiet=True)
    mass = df.groupby("modifier")["w"].sum().sort_values(ascending=False)
    if variant == "full vocabulary":
        counts = df["modifier"].value_counts()
        mods = list(counts[counts >= 5].index)
    else:                                   # top-30 per language
        mods = list(mass.index[:30])
    return df, mods


WIKI_VARIANTS = {
    "main": {},
    "article talk only": {"ns": 1},
    "user talk only": {"ns": 3},
    "predicative only": {"predicative": True},
    "confidence >= 2": {"min_conf": 2},
}


def main():
    rng = np.random.default_rng(SEED)
    rows = []

    def record(source, variant, res):
        d = res["jp"]["adj_boot"] - res["en"]["adj_boot"]
        lo, hi = np.percentile(d, [2.5, 97.5])
        row = dict(source=source, variant=variant,
                   en=res["en"]["effect"], jp=res["jp"]["effect"],
                   n_en=res["en"]["n_rows"], n_jp=res["jp"]["n_rows"],
                   diff=res["jp"]["effect"] - res["en"]["effect"],
                   diff_lo=lo, diff_hi=hi, p=float(np.mean(d <= 0)))
        rows.append(row)
        ratio = row["jp"] / row["en"] if row["en"] > 0 else float("inf")
        print(f"{source:<10} {variant:<20} EN {row['en']:.3f} (n={row['n_en']})  "
              f"JP {row['jp']:.3f} (n={row['n_jp']})  ratio {ratio:4.1f}x  "
              f"JP-EN {row['diff']:+.3f} [{lo:+.3f}, {hi:+.3f}]  "
              f"p {fmt_p(row['p'], N_BOOT)}", flush=True)

    for variant in ["main", "reweight after", "full vocabulary",
                    "top-30 per language"]:
        res = {}
        for lang in ["en", "jp"]:
            df, mods = human_variant(lang, variant)
            res[lang] = run(df, mods, rng)
        record("experiment", variant, res)

    for variant, kw in WIKI_VARIANTS.items():
        res = {lang: run(load_wiki(lang, **kw), MODS[lang], rng)
               for lang in ["en", "jp"]}
        record("corpus", variant, res)
    res = {lang: stratified(load_wiki(lang), MODS[lang], "negated", rng)
           for lang in ["en", "jp"]}
    record("corpus", "given negation", res)

    out = os.path.join(OUT_DIR, "robustness.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
