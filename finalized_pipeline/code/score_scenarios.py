"""
Score every candidate modifier against each of the 80 politeness-imposition
scenarios, for both English and Japanese. Designed to run as a SLURM array
job -- each task scores its own slice of the 80 scenarios (per language) and
writes its own output file, so tasks never collide.

Adapted from code/get_bert_probs.py's batching engine (batches across ALL
candidates at once, padded + attention-masked, chunked to bound memory)
rather than perturbContext.ipynb's per-candidate approach, since that's the
more mature, already-SLURM-aware version of this pipeline.

Usage (locally, single process, processes everything):
    python score_scenarios.py --csv-dir /path/to/data --out-dir /path/to/results

Usage (as a SLURM array task):
    SLURM sets SLURM_ARRAY_TASK_ID automatically. Pass the total task count
    explicitly via SCENARIO_NUM_TASKS (safer than relying on
    SLURM_ARRAY_TASK_COUNT, which isn't populated on all SLURM versions --
    see the .sbatch file).
"""
import argparse
import os
import sys
from collections import defaultdict

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # so `relevant_dicts` imports regardless of cwd
from relevant_dicts import JP_MODIFIER_EXPLANATIONS, EN_MODIFIER_EXPLANATIONS

PLACEHOLDER = "__MOD__"
BATCH_CHUNK = 8  # candidates per forward pass -- bounds peak memory regardless of candidate-list size

MODEL_NAMES = {
    "en": "xlm-roberta-base",              # matches get_bert_probs.py's established choice
    "jp": "cl-tohoku/bert-base-japanese-v3",
}

FORMALITY_KEY = {
    "senior": ["senior", "目上"],
    "peer": ["peer", "同格"],
    "close": ["close", "親しい"],
    "stranger": ["stranger", "見知らぬ"],
}


def formality_to_key(formality_str):
    for key, needles in FORMALITY_KEY.items():
        if any(n in formality_str for n in needles):
            return key
    return "unknown"


def build_variant_items(modifiers, tokenizer, sep="・"):
    """
    Expand each modifier label into one row per orthographic variant, e.g.
    'すこし・少し' -> [('すこし・少し', ids_for_すこし), ('すこし・少し', ids_for_少し)].
    Multiple rows can share the same label; score_variants_at_mask combines
    them back together via logsumexp at the end. English labels have no
    separator, so this is a no-op single-row expansion for them.
    """
    items = []
    for label in modifiers:
        for spelling in [s for s in label.split(sep) if s]:
            items.append((label, tokenizer.encode(spelling, add_special_tokens=False)))
    return items


def score_variants_at_mask(masked_sentence, variant_items, tokenizer, model, device):
    """
    PLL-word-l2r scoring (Kauf & Ivanova, 2023), batched across ALL variant
    rows at once (not per-candidate) -- ported from get_bert_probs.py's
    score_candidates_at_mask, generalized to accept pre-tokenized
    (label, token_ids) pairs so orthographic variants sharing a label can be
    combined afterward instead of scored as separate final candidates.
    """
    pad_id = tokenizer.pad_token_id
    start_id = tokenizer.bos_token_id if tokenizer.bos_token_id is not None else tokenizer.cls_token_id
    end_id = tokenizer.eos_token_id if tokenizer.eos_token_id is not None else tokenizer.sep_token_id

    prefix, suffix = masked_sentence.split(PLACEHOLDER, 1)
    prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_ids = tokenizer.encode(suffix, add_special_tokens=False)
    prefix_len = len(prefix_ids)

    labels = [label for label, _ in variant_items]
    cand_ids_list = [ids for _, ids in variant_items]
    ks = [len(ids) for ids in cand_ids_list]

    # guard against exceeding the model's max sequence length (crashes the whole
    # process on GPU otherwise, rather than failing just that one row)
    max_len_allowed = tokenizer.model_max_length - 2
    for idx, k in enumerate(ks):
        if prefix_len + k + len(suffix_ids) > max_len_allowed:
            ks[idx] = 0

    max_k = max(ks) if ks else 0
    log_prob_sums = [0.0 if k > 0 else float("-inf") for k in ks]

    with torch.inference_mode():
        for i in range(max_k):
            active_idx = [idx for idx, k in enumerate(ks) if k > i]
            if not active_idx:
                continue

            for chunk_start in range(0, len(active_idx), BATCH_CHUNK):
                chunk_idx = active_idx[chunk_start:chunk_start + BATCH_CHUNK]

                sequences = []
                for idx in chunk_idx:
                    cand_ids = cand_ids_list[idx]
                    k = ks[idx]
                    word_ids = cand_ids[:i] + [tokenizer.mask_token_id] * (k - i)
                    sequences.append([start_id] + prefix_ids + word_ids + suffix_ids + [end_id])

                max_len = max(len(s) for s in sequences)
                batch_size = len(sequences)
                input_ids = torch.full((batch_size, max_len), pad_id, dtype=torch.long)
                attention_mask = torch.zeros((batch_size, max_len), dtype=torch.long)
                for row_i, seq in enumerate(sequences):
                    input_ids[row_i, :len(seq)] = torch.tensor(seq)
                    attention_mask[row_i, :len(seq)] = 1
                input_ids = input_ids.to(device)
                attention_mask = attention_mask.to(device)

                target_pos = 1 + prefix_len + i  # right-padding keeps this valid for every row
                logits = model(input_ids, attention_mask=attention_mask).logits
                log_probs = torch.log_softmax(logits[:, target_pos, :], dim=-1)

                for row_i, idx in enumerate(chunk_idx):
                    true_tok_id = cand_ids_list[idx][i]
                    log_prob_sums[idx] += log_probs[row_i, true_tok_id].item()

    # marginalize orthographic variants sharing the same label (sum in probability space)
    by_label = defaultdict(list)
    for label, lp in zip(labels, log_prob_sums):
        by_label[label].append(lp)

    combined = {}
    for label, lps in by_label.items():
        t = torch.tensor(lps)
        combined[label] = torch.logsumexp(t, dim=0).item() if torch.isfinite(t).any() else float("-inf")
    return combined


def score_language(lang, csv_path, out_dir, task_id, num_tasks, device):
    modifier_dict = EN_MODIFIER_EXPLANATIONS if lang == "en" else JP_MODIFIER_EXPLANATIONS
    modifiers = list(modifier_dict.keys())

    print(f"[{lang}] loading {MODEL_NAMES[lang]} ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAMES[lang])
    model = AutoModelForMaskedLM.from_pretrained(MODEL_NAMES[lang])
    model.eval().to(device)

    variant_items = build_variant_items(modifiers, tokenizer)

    scenarios = pd.read_csv(csv_path)
    scenarios["formality_key"] = scenarios["Formality"].apply(formality_to_key)
    scenarios["scenario_id"] = scenarios["ID"].astype(str) + "_" + scenarios["formality_key"]

    chunk = scenarios.iloc[task_id::num_tasks].copy()
    if chunk.empty:
        print(f"[{lang}] task {task_id}/{num_tasks}: no rows in this shard, skipping")
        return

    os.makedirs(out_dir, exist_ok=True)
    scores_path = os.path.join(out_dir, f"{lang}_scores_part{task_id}.csv")
    meta_path = os.path.join(out_dir, f"{lang}_meta_part{task_id}.csv")

    results = {}
    for i, (_, row) in enumerate(chunk.iterrows()):
        sentence_template = row["Scenario Sentence"]
        scenario_id = row["scenario_id"]
        print(f"[{lang}] task {task_id}/{num_tasks} ({i + 1}/{len(chunk)}): scoring {scenario_id}")
        results[scenario_id] = score_variants_at_mask(sentence_template, variant_items, tokenizer, model, device)

        if (i + 1) % 5 == 0:  # periodic checkpoint, same pattern as get_bert_probs.py
            pd.DataFrame(results).rename_axis("candidate").to_csv(scores_path)

    pd.DataFrame(results).rename_axis("candidate").to_csv(scores_path)
    meta_cols = ["scenario_id", "ID", "Formality", "Modifier", "Speaker's Attitude", "Scenario Sentence"]
    chunk[meta_cols].to_csv(meta_path, index=False)

    print(f"[{lang}] task {task_id}/{num_tasks}: done -> {scores_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", default="/nlp/scr/ymachino",
                         help="Directory containing politeness_imposition_scenarios_{en,ja}.csv")
    parser.add_argument("--out-dir", default="/nlp/scr/ymachino/scenario_scores")
    args = parser.parse_args()

    # SCENARIO_NUM_TASKS is set explicitly at submission time (see .sbatch) --
    # safer than relying on SLURM_ARRAY_TASK_COUNT, which not all SLURM
    # versions populate.
    task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
    num_tasks = int(os.environ.get("SCENARIO_NUM_TASKS", os.environ.get("SLURM_ARRAY_TASK_COUNT", 1)))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}  task_id={task_id}  num_tasks={num_tasks}")

    score_language("en", os.path.join(args.csv_dir, "politeness_imposition_scenarios_en.csv"),
                    args.out_dir, task_id, num_tasks, device)
    score_language("jp", os.path.join(args.csv_dir, "politeness_imposition_scenarios_ja.csv"),
                    args.out_dir, task_id, num_tasks, device)


if __name__ == "__main__":
    main()
