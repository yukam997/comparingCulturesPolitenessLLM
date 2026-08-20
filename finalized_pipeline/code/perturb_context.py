"""
Standalone script version of perturbContext.ipynb, for SLURM dispatch.

Reads two input CSVs (one English, one Japanese scenario file, each with a
"Scenario Sentence" column containing a __MOD__ placeholder) into
en_sentence_templates / jp_sentence_templates, scores every candidate
modifier against every template, and writes two output CSVs in the same
format as the notebook's existing Aug11perturb_context_results.csv:
index = candidate, columns = the full sentence template text, cells = the
PLL-word-l2r marginal log-probability.

This intentionally reuses perturbContext.ipynb's own logic (DP-based
WordPiece segmentation enumeration + multiword handling + orthographic
variant marginalization for Japanese; single canonical tokenization for
English, per the segmentation-explosion fix from earlier debugging) rather
than get_bert_probs.py's simpler batching engine.

Usage (single job, processes everything, writes both output files):
    python perturb_context.py \\
        --en-csv data/politeness_imposition_scenarios_en.csv \\
        --jp-csv data/politeness_imposition_scenarios_ja.csv \\
        --en-out data/en_perturb_context_results.csv \\
        --jp-out data/jp_perturb_context_results.csv

Optional SLURM array sharding (each task scores a slice of the templates and
writes a "_partN" file instead of the final file -- merge afterward):
    SCENARIO_NUM_TASKS=8 SLURM_ARRAY_TASK_ID=<n> python perturb_context.py ...
"""
import argparse
import itertools
import os

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM

from relevant_dicts import JP_MODIFIER_EXPLANATIONS, EN_MODIFIER_EXPLANATIONS

PLACEHOLDER = "__MOD__"

MODEL_NAMES = {
    "en": "bert-base-uncased",              # matches perturbContext.ipynb (NOT get_bert_probs.py's xlm-roberta-base)
    "jp": "cl-tohoku/bert-base-japanese",   # matches perturbContext.ipynb as-is (unversioned model)
}


# ---------------------------------------------------------------------------
# Segmentation enumeration (unchanged from the notebook / our debugging)
# ---------------------------------------------------------------------------

def enumerate_wordpiece_segmentations(word, tokenizer, max_pieces=4):
    """DP over all ways to split `word` into vocab-valid WordPiece pieces."""
    n = len(word)
    dp = [[] for _ in range(n + 1)]
    dp[0] = [[]]
    for i in range(n):
        if not dp[i]:
            continue
        for j in range(i + 1, n + 1):
            if j - i > 20:
                break
            piece = word[i:j]
            candidate = piece if i == 0 else "##" + piece
            tok_id = tokenizer.vocab.get(candidate) if hasattr(tokenizer, "vocab") else None
            if tok_id is None:
                tok_id = tokenizer.convert_tokens_to_ids(candidate)
                if tok_id == tokenizer.unk_token_id:
                    continue
            for prefix_seq in dp[i]:
                if len(prefix_seq) < max_pieces:
                    dp[j].append(prefix_seq + [tok_id])
    return dp[n]


def enumerate_wordpiece_segmentations_multiword(phrase, tokenizer, max_pieces=4):
    """
    Handles multi-word phrases (e.g. 'a little') by splitting on whitespace
    first -- WordPiece never lets a ## continuation piece cross a space --
    then enumerating segmentations per word and taking the cartesian product.
    """
    words = phrase.split()
    if len(words) == 1:
        return enumerate_wordpiece_segmentations(phrase, tokenizer, max_pieces=max_pieces)
    per_word_segs = [enumerate_wordpiece_segmentations(w, tokenizer, max_pieces=max_pieces) for w in words]
    if any(not segs for segs in per_word_segs):
        return []
    combined = []
    for combo in itertools.product(*per_word_segs):
        merged = [tok_id for seg in combo for tok_id in seg]
        if len(merged) <= max_pieces * len(words):
            combined.append(merged)
    return combined


def enumerate_variant_segmentations(candidate_str, tokenizer, max_pieces=4, sep="・"):
    """
    candidate_str may contain multiple orthographic variants of the same
    word, e.g. 'すこし・少し'. Splits on `sep`, enumerates valid WordPiece
    segmentations for each variant, and pools them (deduplicated) into one
    list, since they're just different spellings of the same modifier.
    """
    variants = [v for v in candidate_str.split(sep) if v]
    seen, segmentations = set(), []
    for variant in variants:
        for seg in enumerate_wordpiece_segmentations_multiword(variant, tokenizer, max_pieces=max_pieces):
            key = tuple(seg)
            if key not in seen:
                seen.add(key)
                segmentations.append(seg)
    return segmentations


def build_segmentations(candidates, tokenizer, lang):
    if lang == "en":
        # English: use the tokenizer's own canonical tokenization directly.
        # The exhaustive DP explores far too many spurious alternate splits
        # for English's large/permissive vocab (this caused a 40s-vs-15min
        # slowdown when first discovered) -- real segmentation ambiguity is
        # a Japanese-specific problem, not an English one.
        return {cand: [tokenizer.encode(cand, add_special_tokens=False)] for cand in candidates}
    return {cand: enumerate_variant_segmentations(cand, tokenizer, max_pieces=4) for cand in candidates}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def encode_template(sentence_template, tokenizer):
    idx = sentence_template.find(PLACEHOLDER)
    if idx == -1:
        raise ValueError(f"{PLACEHOLDER!r} not found in template: {sentence_template!r}")
    prefix = sentence_template[:idx]
    suffix = sentence_template[idx + len(PLACEHOLDER):]
    prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_ids = tokenizer.encode(suffix, add_special_tokens=False)
    return prefix_ids, suffix_ids


def score_word_in_context(target_word, prefix_ids, suffix_ids, segmentations,
                           tokenizer, model, cls_id, sep_id, mask_id, device):
    """
    PLL-word-l2r (Kauf & Ivanova, 2023): batches all k reveal-positions of a
    segmentation variant into a single forward pass, then marginalizes across
    segmentation variants (sum in probability space, via logsumexp).
    """
    prefix_len = len(prefix_ids)
    target_ids_list = segmentations.get(target_word)
    if not target_ids_list:
        raise ValueError(f"No segmentation found for {target_word!r}")

    variant_log_sums = []
    with torch.inference_mode():
        for word_ids_full in target_ids_list:
            k = len(word_ids_full)
            rows = [
                [cls_id] + prefix_ids + word_ids_full[:i] + [mask_id] * (k - i) + suffix_ids + [sep_id]
                for i in range(k)
            ]
            input_ids = torch.tensor(rows, device=device)
            logits = model(input_ids).logits

            row_idx = torch.arange(k, device=device)
            target_positions = prefix_len + 1 + row_idx
            target_logits = logits[row_idx, target_positions]
            log_probs = torch.log_softmax(target_logits, dim=-1)

            true_ids = torch.tensor(word_ids_full, device=device)
            log_prob_sum = log_probs[row_idx, true_ids].sum().item()
            variant_log_sums.append(log_prob_sum)

    return torch.logsumexp(torch.tensor(variant_log_sums), dim=0).item()


def get_candidate_scores(sentence_template, candidates, segmentations,
                          tokenizer, model, cls_id, sep_id, mask_id, device):
    prefix_ids, suffix_ids = encode_template(sentence_template, tokenizer)
    scores = {}
    for word in candidates:
        scores[word] = score_word_in_context(
            word, prefix_ids, suffix_ids, segmentations,
            tokenizer, model, cls_id, sep_id, mask_id, device,
        )
    return scores


# ---------------------------------------------------------------------------
# Per-language driver
# ---------------------------------------------------------------------------

def run_language(lang, csv_path, out_path, device, task_id, num_tasks):
    modifier_dict = EN_MODIFIER_EXPLANATIONS if lang == "en" else JP_MODIFIER_EXPLANATIONS
    candidates = list(modifier_dict.keys())

    print(f"[{lang}] loading {MODEL_NAMES[lang]} ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAMES[lang])
    model = AutoModelForMaskedLM.from_pretrained(MODEL_NAMES[lang])
    model.eval().to(device)
    cls_id, sep_id, mask_id = tokenizer.cls_token_id, tokenizer.sep_token_id, tokenizer.mask_token_id

    segmentations = build_segmentations(candidates, tokenizer, lang)
    missing = [w for w, segs in segmentations.items() if not segs]
    if missing:
        print(f"[{lang}] WARNING: no valid segmentation for: {missing} -- these will error if scored")

    scenarios = pd.read_csv(csv_path)
    if "Scenario Sentence" not in scenarios.columns:
        raise ValueError(f"{csv_path!r} has no 'Scenario Sentence' column -- found: {list(scenarios.columns)}")
    templates = scenarios["Scenario Sentence"].tolist()

    # optional SLURM array sharding -- no-op (processes everything) if unset
    shard_templates = templates[task_id::num_tasks]
    if not shard_templates:
        print(f"[{lang}] task {task_id}/{num_tasks}: empty shard, nothing to do")
        return

    print(f"[{lang}] task {task_id}/{num_tasks}: scoring {len(shard_templates)}/{len(templates)} templates "
          f"against {len(candidates)} candidates")

    results = {}  # {sentence_template: {candidate: score}}
    for i, sentence_template in enumerate(shard_templates):
        print(f"[{lang}] ({i + 1}/{len(shard_templates)}): {sentence_template[:70]}...")
        results[sentence_template] = get_candidate_scores(
            sentence_template, candidates, segmentations,
            tokenizer, model, cls_id, sep_id, mask_id, device,
        )
        if (i + 1) % 5 == 0:  # periodic checkpoint so a long job doesn't lose all progress if it dies
            pd.DataFrame(results).rename_axis("candidate").to_csv(out_path)

    df = pd.DataFrame(results)
    df.index.name = "candidate"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    df.to_csv(out_path)
    print(f"[{lang}] done -> {out_path}  ({df.shape[0]} candidates x {df.shape[1]} templates)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--en-csv", default="data/politeness_imposition_scenarios_en.csv")
    parser.add_argument("--jp-csv", default="data/politeness_imposition_scenarios_ja.csv")
    parser.add_argument("--en-out", default="data/en_perturb_context_results.csv")
    parser.add_argument("--jp-out", default="data/jp_perturb_context_results.csv")
    args = parser.parse_args()

    # Set these via env vars to run as a SLURM array job (see module docstring).
    # Left at their defaults (0, 1), a single run processes every template and
    # writes the complete two output files, as requested.
    task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
    num_tasks = int(os.environ.get("SCENARIO_NUM_TASKS", os.environ.get("SLURM_ARRAY_TASK_COUNT", 1)))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}  task_id={task_id}  num_tasks={num_tasks}")

    en_out = args.en_out if num_tasks == 1 else _shard_path(args.en_out, task_id)
    jp_out = args.jp_out if num_tasks == 1 else _shard_path(args.jp_out, task_id)

    run_language("en", args.en_csv, en_out, device, task_id, num_tasks)
    run_language("jp", args.jp_csv, jp_out, device, task_id, num_tasks)


def _shard_path(path, task_id):
    root, ext = os.path.splitext(path)
    return f"{root}_part{task_id}{ext}"


if __name__ == "__main__":
    main()
