import numpy as np
import pandas as pd
from transformers import AutoTokenizer, AutoModelForMaskedLM
import torch
import os
import re
import json

jp_data = pd.read_csv("/nlp/scr/ymachino/jp_data.csv") # replace this to where jp_data is stored
en_data = pd.read_csv("/nlp/scr/ymachino/en_data.csv")

en_data['masked_sentence'] = en_data.apply(
    lambda row: re.sub(r'\b' + re.escape(row['modifier']) + r'\b', '<mask>', row['sentence']),
    axis=1
)
jp_data['masked_sentence'] = jp_data.apply(
    lambda row: row['sentence'].replace(row['modifier'], '<mask>'),
    axis=1
)

# ignore row with multiple masks
en_data = en_data[en_data['masked_sentence'].str.count('<mask>') == 1]
jp_data = jp_data[jp_data['masked_sentence'].str.count('<mask>') == 1]

device = "cuda" if torch.cuda.is_available() else "cpu"

# English stays on XLM-R; Japanese uses the Tohoku BERT model, which uses
# proper Unidic-based morphological segmentation instead of XLM-R's
# statistical subword merges (see earlier tokenization comparison).
en_tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-base")
en_model = AutoModelForMaskedLM.from_pretrained("xlm-roberta-base")
en_model.eval().to(device)

jp_tokenizer = AutoTokenizer.from_pretrained("cl-tohoku/bert-base-japanese-v3")
jp_model = AutoModelForMaskedLM.from_pretrained("cl-tohoku/bert-base-japanese-v3")
jp_model.eval().to(device)


def score_candidates_at_mask(masked_sentence, candidates, tokenizer, model):
    """
    PLL-word-l2r scoring (Kauf & Ivanova, 2023), batched across candidates.

    Instead of looping through candidates one at a time -- each needing its own
    sequence of tiny batch-size-1 forward passes -- this groups ALL candidates
    that still need scoring at subword step i into a single batched forward pass.
    A candidate with k subword pieces needs k steps (i = 0..k-1); at each step i,
    every candidate whose k > i is included in that step's batch. Sequences are
    right-padded to the same length within each step's batch (with an
    attention_mask so padding doesn't affect real tokens), and since padding is
    added on the right, the target position (1 + prefix_len + i) stays valid for
    every row in the batch regardless of that row's total sequence length.

    This turns "roughly sum(k_c for c in candidates) tiny forward passes" into
    "max(k_c) batched forward passes" -- e.g. ~30-40 sequential calls collapsing
    into ~3 batched calls for a typical hedge-word candidate set.

    Returns: list of (candidate, log_prob_sum) tuples, one per candidate.
    """
    pad_id = tokenizer.pad_token_id
    # XLM-R (RoBERTa-style) uses bos/eos; the Tohoku BERT model uses cls/sep.
    # Fall back to whichever pair the tokenizer actually has.
    start_id = tokenizer.bos_token_id if tokenizer.bos_token_id is not None else tokenizer.cls_token_id
    end_id = tokenizer.eos_token_id if tokenizer.eos_token_id is not None else tokenizer.sep_token_id

    prefix, suffix = masked_sentence.split("<mask>", 1)

    prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_ids = tokenizer.encode(suffix, add_special_tokens=False)
    prefix_len = len(prefix_ids)

    cand_ids_list = [tokenizer.encode(c, add_special_tokens=False) for c in candidates]
    ks = [len(ids) for ids in cand_ids_list]

    # xlm-roberta-base supports sequences up to 512 tokens (including BOS/EOS).
    # A candidate whose full sequence (prefix + word pieces + suffix + 2 special
    # tokens) would exceed that limit causes an out-of-bounds position-embedding
    # lookup on GPU (CUDA "scatter gather kernel index out of bounds"), which
    # crashes the whole process rather than just failing that one row. Treat
    # any such candidate as unscoreable (same as k == 0) instead of sending it
    # to the model.
    max_len_allowed = tokenizer.model_max_length - 2  # reserve room for BOS/EOS
    for idx, k in enumerate(ks):
        if prefix_len + k + len(suffix_ids) > max_len_allowed:
            ks[idx] = 0

    max_k = max(ks) if ks else 0

    log_prob_sums = [0.0 if k > 0 else float("-inf") for k in ks]

    # Cap how many candidates get batched together in one forward pass. Without
    # this, a step with many active candidates (e.g. 30-50 modifiers) near the
    # max sequence length produces a (batch_size, seq_len, vocab_size) logits
    # tensor that can balloon to tens of GB -- xlm-roberta-base's vocab is
    # ~250K, so e.g. 50 rows x 500 tokens x 250K x 4 bytes ~= 25GB in one shot.
    # Sub-batching keeps most of the speedup from batching (still far better
    # than batch-size-1) while bounding peak memory regardless of how many
    # candidates are active at a given step.
    BATCH_CHUNK = 8

    with torch.inference_mode():
        for i in range(max_k):
            # candidates that still have a subword piece to score at this step
            active_idx = [idx for idx, k in enumerate(ks) if k > i]
            if not active_idx:
                continue

            for chunk_start in range(0, len(active_idx), BATCH_CHUNK):
                chunk_idx = active_idx[chunk_start:chunk_start + BATCH_CHUNK]

                sequences = []
                for idx in chunk_idx:
                    cand_ids = cand_ids_list[idx]
                    k = ks[idx]
                    # pieces 0..i-1 revealed (true tokens); piece i and all pieces
                    # after it are masked
                    word_ids = cand_ids[:i] + [tokenizer.mask_token_id] * (k - i)
                    full_ids = (
                        [start_id]
                        + prefix_ids
                        + word_ids
                        + suffix_ids
                        + [end_id]
                    )
                    sequences.append(full_ids)

                max_len = max(len(s) for s in sequences)
                batch_size = len(sequences)
                input_ids = torch.full((batch_size, max_len), pad_id, dtype=torch.long)
                attention_mask = torch.zeros((batch_size, max_len), dtype=torch.long)
                for row_i, seq in enumerate(sequences):
                    input_ids[row_i, :len(seq)] = torch.tensor(seq)
                    attention_mask[row_i, :len(seq)] = 1
                input_ids = input_ids.to(device)
                attention_mask = attention_mask.to(device)

                # right-padding means this position is valid for every row in the batch
                target_pos = 1 + prefix_len + i

                logits = model(input_ids, attention_mask=attention_mask).logits  # (batch, seq_len, vocab)
                log_probs = torch.log_softmax(logits[:, target_pos, :], dim=-1)  # (batch, vocab)

                for row_i, idx in enumerate(chunk_idx):
                    true_tok_id = cand_ids_list[idx][i]
                    log_prob_sums[idx] += log_probs[row_i, true_tok_id].item()

    return list(zip(candidates, log_prob_sums))


def compare_hedges(masked_sentence, candidates, tokenizer, model):
    """
    Scores every candidate hedge at the masked position and normalizes them
    against each other with log_softmax, so the result is interpretable as a
    relative preference among the candidate set.
    """
    results = score_candidates_at_mask(masked_sentence, candidates, tokenizer, model)
    log_prob_tensor = torch.tensor([lp for _, lp in results])
    log_relative = torch.log_softmax(log_prob_tensor, dim=0)
    return {cand: rel.item() for (cand, _), rel in zip(results, log_relative)}


# --- Optional row-chunking for SLURM array jobs -----------------------------
# If submitted as `#SBATCH --array=0-9`, SLURM sets SLURM_ARRAY_TASK_ID (this
# task's index) and you can pass the total chunk count via SLURM_ARRAY_TASK_COUNT
# (available on newer SLURM) or hardcode it below. Each array task processes
# only its slice of rows and writes to its own output file, so tasks never
# collide writing to the same CSV. Running the script with no array env vars
# set (e.g. testing locally) processes the full dataset as before.
TASK_ID = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
NUM_TASKS = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", 1))
# ------------------------------------------------------------------------------

for lang, data, tokenizer, model in [
    ("en", en_data, en_tokenizer, en_model),
    ("jp", jp_data, jp_tokenizer, jp_model),
]:
    modifier_counts = data['modifier'].value_counts()
    modifiers = modifier_counts[modifier_counts >= 10].index.values
    data = data[data['modifier'].isin(modifiers)].copy()

    modifier_to_index = {mod: idx for idx, mod in enumerate(modifiers)}
    # store the score for the row's actual modifier AND the full score
    # distribution across every candidate modifier (JSON-encoded, since a
    # dict can't go directly into a CSV cell and round-trip cleanly)
    data["log_relative"] = None
    data["log_all"] = None

    # slice out this array task's chunk of rows (no-op if NUM_TASKS == 1)
    chunk_data = data.iloc[TASK_ID::NUM_TASKS].copy()

    out_path = f"/nlp/scr/ymachino/{lang}_data_logprob_part{TASK_ID}.csv"

    for i, row in enumerate(chunk_data.itertuples()):
        rel_scores = compare_hedges(row.masked_sentence, modifiers, tokenizer, model)
        chunk_data.at[row.Index, "log_relative"] = rel_scores[row.modifier]
        chunk_data.at[row.Index, "log_all"] = json.dumps(rel_scores)
        if i % 400 == 0:
            chunk_data.to_csv(out_path, index=False, encoding="utf-8-sig")
    chunk_data.to_csv(out_path, index=False, encoding="utf-8-sig")
