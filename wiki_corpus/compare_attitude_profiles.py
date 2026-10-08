"""
Do modifiers lean toward the same attitudes in the experiment and on
Wikipedia, even though overall modifier frequencies differ?

For each source, a modifier's lean toward an attitude is
    lean(a, m) = P(m | a) - P(m)
i.e. how much more (or less) often m is chosen under attitude a than
overall. Differences in overall frequency (P(m)) are removed, so the two
sources can be compared even though the experiment's predicates and
register differ from Wikipedia's.

Reports, per language, the correlation of leans across (attitude, modifier)
cells, restricted to modifiers with at least MIN_MASS overall share in both
sources, with a null from shuffling the wiki attitude labels; then the
same correlation within each attitude.

Output: printed summary and attitude_results/attitude_profile_agreement.csv
"""

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compare_human_wiki import ATTITUDES, OUT_DIR, load_human, load_wiki  # noqa: E402
from extract_experiment_modifiers import EN_MODIFIERS, JP_MODIFIERS  # noqa: E402

MIN_MASS = 0.01
N_PERM = 1000
SEED = 0


def counts(df, mods):
    t = (df.pivot_table(index="attitude", columns="modifier", values="w",
                        aggfunc="sum", fill_value=0.0)
           .reindex(index=ATTITUDES, columns=mods, fill_value=0.0))
    return t.to_numpy()


def lean(c):
    cond = c / c.sum(axis=1, keepdims=True)
    # marginal with attitudes weighted equally, matching the JSD analysis
    marg = cond.mean(axis=0)
    return cond - marg, marg


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for lang, mods in [("en", EN_MODIFIERS), ("jp", JP_MODIFIERS)]:
        human, wiki = load_human(lang), load_wiki(lang)
        lh, mh = lean(counts(human, mods))
        lw, mw = lean(counts(wiki, mods))
        keep = (mh >= MIN_MASS) & (mw >= MIN_MASS)
        kept = [m for m, k in zip(mods, keep) if k]
        r = np.corrcoef(lh[:, keep].ravel(), lw[:, keep].ravel())[0, 1]
        # Pearson on raw leans is dominated by the most frequent modifiers;
        # the rank correlation weights every cell alike
        rho = spearmanr(lh[:, keep].ravel(), lw[:, keep].ravel())[0]

        null = np.empty(N_PERM)
        att = wiki["attitude"].to_numpy()
        for i in range(N_PERM):
            shuf = wiki.assign(attitude=rng.permutation(att))
            ls, _ = lean(counts(shuf, mods))
            null[i] = np.corrcoef(lh[:, keep].ravel(), ls[:, keep].ravel())[0, 1]
        p = (np.sum(null >= r) + 1) / (N_PERM + 1)
        print(f"\n{lang.upper()}: {keep.sum()} modifiers with >= {MIN_MASS:.0%} "
              f"share in both sources: {', '.join(kept)}")
        print(f"  correlation of attitude leans, experiment vs wiki: r = {r:.2f} "
              f"(shuffled-wiki null {null.mean():.2f} +/- {null.std():.2f}, "
              f"p = {p:.4f}); rank correlation {rho:.2f}")
        rows.append(dict(lang=lang, attitude="all", r=r, rho=rho,
                         null_mean=null.mean(), p=p, n_modifiers=int(keep.sum())))
        for i, a in enumerate(ATTITUDES):
            ra = np.corrcoef(lh[i, keep], lw[i, keep])[0, 1]
            top_h = [kept[j] for j in np.argsort(-lh[i, keep])[:3]]
            top_w = [kept[j] for j in np.argsort(-lw[i, keep])[:3]]
            print(f"    {a:<17} r = {ra:+.2f}   most over-used: experiment "
                  f"{', '.join(top_h)} | wiki {', '.join(top_w)}")
            rows.append(dict(lang=lang, attitude=a, r=ra, null_mean=np.nan,
                             p=np.nan, n_modifiers=int(keep.sum())))
    out = os.path.join(OUT_DIR, "attitude_profile_agreement.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
