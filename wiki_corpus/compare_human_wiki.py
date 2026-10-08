"""
Data loaders shared by the analyses, and the experiment-vs-corpus panels.

Human side: behavioral_data/{EN,JP}_trials.csv (free-response modifier
fill-ins). Each trial's responses get weight 1/k, where k counts all of the
trial's responses; responses outside the experiment's 30-modifier candidate
vocabulary are then dropped, so a trial keeps the share of its responses
that were candidate modifiers. (plot_jsd_effect.py also reports the result
without the vocabulary restriction.)

Wiki side: attitude_results/attitude_labeled_context.csv (attitudes labeled
by Claude with the modifier masked). Within each venue (article talk, ns 1;
user talk, ns 3), a sentence's weight is corpus_count / (number of labeled
sentences for that modifier in that venue, including ones labeled "other"),
which restores the corpus mix of modifiers; venues are then given equal
total weight. Pages are the bootstrap unit.

Running this script draws, for each language, the per-attitude modifier
distributions in the experiment (top row) and the corpus (bottom row):
  attitude_results/human_vs_wiki_distributions_{en,jp}.png
and writes attitude_results/human_attitude_modifier_probs.csv.
Statistics are computed by plot_jsd_effect.py and robustness_checks.py.

Usage: python wiki_corpus/compare_human_wiki.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract_experiment_modifiers import (  # noqa: E402
    EN_MODIFIERS, JP_MODIFIERS, JP_VARIANTS)
from jsd_utils import LANG_COLOR, LANG_NAME, plt  # noqa: E402

OUT_DIR = os.path.join(HERE, "attitude_results")
LABELED = os.path.join(OUT_DIR, "attitude_labeled_context.csv")
BEHAV_DIR = os.path.join(os.path.dirname(HERE), "behavioral_data")

ATTITUDES = ["neutral-positive", "neutral-negative", "non-committal",
             "encouraging", "acknowledge", "warning", "annoyed"]
WIKI_ATT_MAP = {"acknowledging": "acknowledge"}
MODS = {"en": EN_MODIFIERS, "jp": JP_MODIFIERS}


def table(df, mods):
    """Weighted attitude x modifier counts."""
    t = (df.pivot_table(index="attitude", columns="modifier", values="w",
                        aggfunc="sum", fill_value=0.0)
           .reindex(index=ATTITUDES, columns=mods, fill_value=0.0))
    return t.to_numpy()


# ------------------------------------------------------------------- data ---

def load_human(lang, restrict=True, quiet=False):
    """One row per response: doc_id (participant), trial, attitude,
    modifier, w. restrict=False keeps every response type."""
    df = pd.read_csv(os.path.join(BEHAV_DIR, f"{lang.upper()}_trials.csv"))
    df = df[(df["is_practice"] == False) & df["attitude"].notna()  # noqa: E712
            & df["modifier_response_list"].notna()].copy()
    df["trial"] = df["doc_id"] + ":" + df["trial_index"].astype(str)
    rows = df.assign(modifier=df["modifier_response_list"].str.split("; "))
    rows = rows.explode("modifier")
    rows["modifier"] = rows["modifier"].str.strip()
    if lang == "en":
        rows["modifier"] = rows["modifier"].str.lower()
    else:
        rows["modifier"] = rows["modifier"].replace(JP_VARIANTS)
    rows = rows[rows["modifier"] != ""]
    rows["w"] = 1.0 / rows.groupby("trial")["modifier"].transform("count")
    n_before = rows["w"].sum()
    if restrict:
        rows = rows[rows["modifier"].isin(MODS[lang])]
    if not quiet:
        print(f"{LANG_NAME[lang]} experiment: {df['doc_id'].nunique()} "
              f"participants, {df['trial'].nunique()} trials; "
              f"{rows['w'].sum() / n_before:.0%} of response mass kept")
    return rows[["doc_id", "trial", "attitude", "modifier", "w"]]


def load_wiki(lang, ns=None, min_conf=None, negated=None, predicative=None):
    """One row per labeled sentence in the 7 attitudes: doc_id (page),
    trial (sentence id), attitude, modifier, w, ns, negated, predicative.
    Optional filters restrict to a venue, a minimum label confidence, or
    negated/affirmative and predicative/attributive uses."""
    df = pd.read_csv(LABELED).dropna(subset=["attitude"])
    df = df[(df["lang"] == lang) & df["modifier"].isin(MODS[lang])].copy()
    # weights use every labeled sentence, including "other", so each
    # modifier's total weight in a venue equals its corpus count there
    n_all = df.groupby(["ns", "modifier"])["modifier"].transform("count")
    df["w"] = df["corpus_count"] / n_all
    df["w"] = df["w"] / df.groupby("ns")["w"].transform("sum")
    df["attitude"] = df["attitude"].replace(WIKI_ATT_MAP)
    df = df[df["attitude"].isin(ATTITUDES)]
    if ns is not None:
        df = df[df["ns"] == ns]
    if min_conf:
        df = df[pd.to_numeric(df["confidence"], errors="coerce") >= min_conf]
    if negated is not None:
        df = df[df["negated"] == negated]
    if predicative is not None:
        df = df[df["predicative"] == predicative]
    df["trial"] = df["id"]
    df["doc_id"] = df["page"]
    return df[["doc_id", "trial", "attitude", "modifier", "w", "ns",
               "negated", "predicative"]]


# ------------------------------------------------------------------ plots ---

def panel_fig(lang, human, wiki, mods, out):
    """Two rows (experiment / corpus) x (marginal + 7 attitudes) of
    P(modifier | attitude), modifiers in the same order in every panel."""
    hm = table(human, mods)
    wk = table(wiki, mods)
    h_marg = hm.sum(axis=0) / hm.sum()
    order = np.argsort(-h_marg)
    titles = ["marginal"] + ATTITUDES
    fig, axes = plt.subplots(2, len(titles), figsize=(2.5 * len(titles), 5.4),
                             sharey="row")
    for row, (src, label) in enumerate(
            [(hm, "experiment"), (wk, "Wikipedia")]):
        dists = [src.sum(axis=0) / max(src.sum(), 1)] + [
            src[i] / s if (s := src[i].sum()) > 0 else np.zeros(len(mods))
            for i in range(len(ATTITUDES))]
        ymax = max(np.max(d) for d in dists) * 1.18
        for col, (t, d) in enumerate(zip(titles, dists)):
            ax = axes[row, col]
            d = np.asarray(d)[order]
            ax.bar(range(len(mods)), d, width=0.72, edgecolor="none",
                   color="#868e96" if col == 0 else LANG_COLOR[lang],
                   alpha=1.0 if row == 0 else 0.75)
            for j in np.argsort(-d)[:3]:
                if d[j] > 0:
                    ax.text(j, d[j] + ymax * 0.02, np.array(mods)[order][j],
                            rotation=90, ha="center", va="bottom",
                            fontsize=6.5, color="#343a40")
            if row == 0:
                ax.set_title(t, fontsize=9)
            if col == 0:
                ax.set_ylabel(f"{label}\nP(modifier | attitude)", fontsize=8.5)
            ax.set_xticks([])
            ax.set_ylim(0, ymax)
            ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"{LANG_NAME[lang]}: modifier distributions by attitude, "
                 f"experiment (top) and Wikipedia talk pages (bottom)",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"wrote {out}")


def main():
    tidy = []
    for lang in ["en", "jp"]:
        mods = MODS[lang]
        human = load_human(lang)
        hm = table(human, mods)
        for i, a in enumerate(ATTITUDES):
            if hm[i].sum() > 0:
                for m, pm in zip(mods, hm[i] / hm[i].sum()):
                    tidy.append(dict(lang=lang, attitude=a, modifier=m,
                                     prob=pm, n_weighted=hm[i].sum()))
        panel_fig(lang, human, load_wiki(lang), mods, os.path.join(
            OUT_DIR, f"human_vs_wiki_distributions_{lang}.png"))
    pd.DataFrame(tidy).to_csv(
        os.path.join(OUT_DIR, "human_attitude_modifier_probs.csv"), index=False)


if __name__ == "__main__":
    main()
