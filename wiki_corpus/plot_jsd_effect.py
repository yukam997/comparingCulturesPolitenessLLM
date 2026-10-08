"""
Summary figure: attitude information in modifier choice, behavioral
experiment vs Wikipedia talk pages, English vs Japanese.

Main figure (jsd_bars_raw.png): observed JSD across attitude-conditioned
modifier distributions (bits) with bootstrapped 95% CIs, plus the
permutation floor (JSD with attitude labels shuffled) marked on each bar.
Raw JSD is non-negative, so the intervals cannot cross zero. The text above
each bar is the floor-adjusted effect (observed minus floor), the number
reported in the abstract.

Alternative (jsd_bars_adjusted.png): floor-adjusted effect with bootstrapped
CIs, where each bootstrap draw's floor is the mean of K_FLOOR shuffles of
that draw (one shuffle per draw makes the floor, and so the interval, noisy).

Bootstrap units: participants (experiment) and pages (corpus), since
sentences from the same page aren't independent. Shuffles: attitude labels
are permuted across trials (experiment) or sentences (corpus), keeping each
trial's responses together; copies of a unit duplicated by the bootstrap
share their shuffled attitudes. Also reported: mutual information (JSD with
attitudes weighted by frequency rather than equally).

The JP - EN p-value is the share of bootstrap draws in which the difference
is <= 0 (reported as < 1/N_BOOT when none are).

Usage: python wiki_corpus/plot_jsd_effect.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compare_human_wiki import (ATTITUDES, MODS, OUT_DIR,  # noqa: E402
                                load_human, load_wiki)
from jsd_utils import LANG_COLOR, LANG_NAME, jsd, plt  # noqa: E402

N_PERM = 2000
N_BOOT = 1000
K_FLOOR = 10
SEED = 0


def fmt_p(p, n):
    return f"< {1 / n:.3g}" if p == 0 else f"= {p:.3f}"


class Data:
    """Integer-coded rows for fast weighted attitude x modifier counting."""

    def __init__(self, df, mods, unit_col, cluster_col):
        self.n_mod = len(mods)
        mod_ix = {m: i for i, m in enumerate(mods)}
        att_ix = {a: i for i, a in enumerate(ATTITUDES)}
        df = df[df["modifier"].isin(mod_ix)].reset_index(drop=True)
        self.mod = df["modifier"].map(mod_ix).to_numpy()
        self.w = df["w"].to_numpy(float)
        # per-unit structure: row indices, local cluster per row, attitude per cluster
        self.units = []
        for _, g in df.groupby(unit_col, sort=False):
            clus, local = np.unique(g[cluster_col].to_numpy(), return_inverse=True)
            att = (g.groupby(cluster_col)["attitude"].first()
                    .reindex(clus).map(att_ix).to_numpy())
            self.units.append((g.index.to_numpy(), local, att))

    def assemble(self, unit_ids):
        """Rows for the given units (repeats allowed), each row's cluster
        position, each cluster's attitude, and each cluster's original id
        (so repeated copies of a cluster can be shuffled together)."""
        rows, row_clus, clus_att, clus_orig, off = [], [], [], [], 0
        for u in unit_ids:
            r, local, att = self.units[u]
            rows.append(r)
            row_clus.append(local + off)
            clus_att.append(att)
            clus_orig.append(u * 10_000 + np.arange(len(att)))
            off += len(att)
        return (np.concatenate(rows), np.concatenate(row_clus),
                np.concatenate(clus_att), np.concatenate(clus_orig))

    @staticmethod
    def shuffle(clus_att, clus_orig, rng):
        """Permute attitudes across distinct original clusters; repeated
        copies of a cluster keep sharing one (shuffled) attitude."""
        uniq, first, inv = np.unique(clus_orig, return_index=True,
                                     return_inverse=True)
        return rng.permutation(clus_att[first])[inv]

    def counts(self, rows, row_att):
        c = np.bincount(row_att * self.n_mod + self.mod[rows],
                        weights=self.w[rows],
                        minlength=len(ATTITUDES) * self.n_mod)
        return c.reshape(len(ATTITUDES), self.n_mod)

    def jsd_for(self, rows, row_att, mi=False):
        c = self.counts(rows, row_att)
        keep = c.sum(axis=1) > 0
        P = c[keep] / c[keep].sum(axis=1, keepdims=True)
        return jsd(P, weights=c[keep].sum(axis=1) if mi else None)


def analyze(data, rng, n_perm=N_PERM, n_boot=N_BOOT, k_floor=K_FLOOR):
    all_units = np.arange(len(data.units))
    rows, row_clus, clus_att, _ = data.assemble(all_units)
    obs = data.jsd_for(rows, clus_att[row_clus])
    null = np.array([data.jsd_for(rows, rng.permutation(clus_att)[row_clus])
                     for _ in range(n_perm)])
    mi = data.jsd_for(rows, clus_att[row_clus], mi=True)
    mi_null = np.mean([data.jsd_for(rows, rng.permutation(clus_att)[row_clus],
                                    mi=True) for _ in range(min(n_perm, 500))])
    raw_b, adj_b = np.empty(n_boot), np.empty(n_boot)
    for i in range(n_boot):
        r, rc, ca, co = data.assemble(rng.choice(all_units, len(all_units)))
        raw_b[i] = data.jsd_for(r, ca[rc])
        floor_i = np.mean([data.jsd_for(r, data.shuffle(ca, co, rng)[rc])
                           for _ in range(k_floor)])
        adj_b[i] = raw_b[i] - floor_i
    floor = null.mean()
    # resampling inflates plug-in JSD, so center the raw interval on the
    # observed value (the same correction as llm_jsd.boot_predicates)
    q_lo, q_hi = np.percentile(raw_b, [2.5, 97.5])
    med = np.median(raw_b)
    raw_ci = (max(0.0, obs - (med - q_lo)), obs + (q_hi - med))
    return dict(obs=obs, floor=floor, effect=obs - floor,
                p=(np.sum(null >= obs) + 1) / (n_perm + 1),
                mi_effect=mi - mi_null, n_units=len(all_units),
                n_rows=len(rows),
                raw_ci=raw_ci, adj_ci=tuple(np.percentile(adj_b, [2.5, 97.5])),
                adj_boot=adj_b)


def jp_minus_en(stats_en, stats_jp):
    """Point estimate, 95% CI and bootstrap p for the JP - EN difference."""
    d = stats_jp["adj_boot"] - stats_en["adj_boot"]
    return (stats_jp["effect"] - stats_en["effect"],
            tuple(np.percentile(d, [2.5, 97.5])), float(np.mean(d <= 0)), len(d))


def bar_positions():
    langs, srcs, width = ["en", "jp"], ["human", "wiki"], 0.36
    return [(l, s, li + (si - 0.5) * width, width * 0.92)
            for li, l in enumerate(langs) for si, s in enumerate(srcs)]


SRC_LABEL = {"human": "Behavioral experiment", "wiki": "Wikipedia talk pages"}


def style(ax, ylabel):
    ax.set_xticks([0, 1], [LANG_NAME["en"], LANG_NAME["jp"]], fontsize=11)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(bottom=0)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#555555", label=SRC_LABEL["human"]),
                       Patch(color="#555555", alpha=0.45, label=SRC_LABEL["wiki"])],
              frameon=False, fontsize=9, loc="upper left")


def plot_raw(stats, out):
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for lang, src, x, w in bar_positions():
        s = stats[lang][src]
        alpha = 1.0 if src == "human" else 0.45
        ax.bar(x, s["obs"], w, color=LANG_COLOR[lang], alpha=alpha,
               edgecolor="none")
        lo, hi = s["raw_ci"]
        ax.errorbar(x, s["obs"], yerr=[[s["obs"] - lo], [hi - s["obs"]]],
                    fmt="none", ecolor="#343a40", capsize=3.5, lw=1.1)
        ax.hlines(s["floor"], x - w / 2, x + w / 2, colors="#212529",
                  linestyles=(0, (2, 1.5)), lw=1.3)
        ax.text(x, hi + 0.012, f"+{s['effect']:.2f}", ha="center",
                va="bottom", fontsize=8.5, color="#343a40")
    style(ax, "Attitude information in modifier choice\n(JSD across attitudes, bits)")
    ax.plot([], [], color="#212529", ls=(0, (2, 1.5)), lw=1.3,
            label="chance (attitudes shuffled)")
    handles, labels = ax.get_legend_handles_labels()
    leg = ax.get_legend()
    ax.legend(handles=leg.legend_handles + handles,
              labels=[t.get_text() for t in leg.get_texts()] + labels,
              frameon=False, fontsize=9, loc="upper left")
    top = max(stats[l][s]["raw_ci"][1] for l in stats for s in stats[l])
    ax.set_ylim(0, top * 1.15)
    ax.set_title("Modifier choice carries more information about attitude "
                 "in Japanese", fontsize=11)
    fig.text(0.99, 0.01, "Bars: observed JSD with bootstrapped 95% CIs. "
             "Numbers: observed minus chance.", ha="right", fontsize=7.5,
             color="#868e96")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"wrote {out}")


def plot_adjusted(stats, out):
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for lang, src, x, w in bar_positions():
        s = stats[lang][src]
        alpha = 1.0 if src == "human" else 0.45
        ax.bar(x, s["effect"], w, color=LANG_COLOR[lang], alpha=alpha,
               edgecolor="none")
        lo, hi = s["adj_ci"]
        ax.errorbar(x, s["effect"], yerr=[[s["effect"] - lo], [hi - s["effect"]]],
                    fmt="none", ecolor="#343a40", capsize=3.5, lw=1.1)
    style(ax, "Attitude information in modifier choice\n"
              "(JSD above chance, bits)")
    ax.set_title("Modifier choice carries more information about attitude "
                 "in Japanese", fontsize=11)
    fig.text(0.99, 0.01, "Observed JSD minus shuffled-attitude chance level; "
             "bootstrapped 95% CIs.", ha="right", fontsize=7.5, color="#868e96")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"wrote {out}")


def describe(lang, src, s):
    return (f"  {lang} {src:<5} n={s['n_rows']} in {s['n_units']} units  "
            f"JSD {s['obs']:.3f} [{s['raw_ci'][0]:.3f}, {s['raw_ci'][1]:.3f}]  "
            f"floor {s['floor']:.3f}  effect {s['effect']:.3f} "
            f"[{s['adj_ci'][0]:.3f}, {s['adj_ci'][1]:.3f}]  "
            f"MI above chance {s['mi_effect']:.3f}  "
            f"permutation p {fmt_p(s['p'] - 1 / (N_PERM + 1), N_PERM)}")


def main():
    rng = np.random.default_rng(SEED)
    stats = {}
    for lang in ["en", "jp"]:
        stats[lang] = {
            "human": analyze(Data(load_human(lang), MODS[lang], "doc_id", "trial"), rng),
            "wiki": analyze(Data(load_wiki(lang), MODS[lang], "doc_id", "trial"), rng),
        }
        for src in ["human", "wiki"]:
            print(describe(lang, src, stats[lang][src]))
    for src in ["human", "wiki"]:
        point, (lo, hi), p, n = jp_minus_en(stats["en"][src], stats["jp"][src])
        ratio = stats["jp"][src]["effect"] / stats["en"][src]["effect"]
        print(f"  {src}: JP - EN effect {point:+.3f} [{lo:+.3f}, {hi:+.3f}], "
              f"ratio {ratio:.1f}x, bootstrap p {fmt_p(p, n)}")
    plot_raw(stats, os.path.join(OUT_DIR, "jsd_bars_raw.png"))
    plot_adjusted(stats, os.path.join(OUT_DIR, "jsd_bars_adjusted.png"))


if __name__ == "__main__":
    main()
