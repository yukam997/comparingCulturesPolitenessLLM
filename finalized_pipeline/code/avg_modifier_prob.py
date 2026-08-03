import pandas as pd
import json
import numpy as np


def average_probability_per_modifier(csv_path, log_all_col="log_all"):
    """
    Reads a combined *_data_logprob_combined.csv file (containing a JSON-encoded
    `log_all` column -- the relative log-probability every candidate modifier
    received at the masked position, for every row), and computes, for each
    candidate modifier, its average PROBABILITY (not log-probability) across
    every row in the dataset.

    This is NOT limited to rows where the modifier was the actual/correct one
    used in that sentence -- since `log_all` contains a score for every
    candidate at every row (the whole candidate set is scored against every
    masked position), this averages a modifier's assigned probability across
    ALL rows, regardless of whether it was the modifier the sentence actually
    used.

    Returns a pandas Series: index = modifier, value = average probability,
    sorted descending.
    """
    df = pd.read_csv(csv_path)

    # parse the JSON string in each row into a dict {modifier: log_relative}
    parsed = df[log_all_col].apply(json.loads)

    # convert to a DataFrame: one column per modifier, one row per sentence
    # (rows/columns not present for a given row -- e.g. if that row's
    # candidate set genuinely differs -- become NaN and are excluded from
    # the mean automatically)
    log_matrix = pd.DataFrame(list(parsed))

    # convert log-probabilities to actual probabilities
    prob_matrix = np.exp(log_matrix)

    # average probability per modifier across all rows, ignoring NaNs
    avg_probs = prob_matrix.mean(axis=0, skipna=True)

    return avg_probs.sort_values(ascending=False)
for lang in ["en", "jp"]:
    path = f"./data/results/{lang}_data_logprob_combinedJul21.csv"
    avg_probs = average_probability_per_modifier(path)

    print(f"\n=== {lang}: average probability per modifier (across all rows) ===")
    print(avg_probs)

    out_path = f"./data/results/{lang}_avg_modifier_probability.csv"
    avg_probs.to_csv(out_path, header=["avg_probability"], encoding="utf-8-sig")
    print(f"Saved to {out_path}")
