"""
Label masked wiki-talk sentences with the writer's attitude, using Claude.

Categories mirror the behavioral experiment's attitude manipulation
(en/stimuli.js): warning, non-committal, acknowledging, encouraging, annoyed,
neutral-positive, neutral-negative, plus "other". The target modifier is
masked (see prepare_attitude_sample.py), so labels are independent of
modifier choice. The prompt is prompts/attitude_context_prompt.txt.

Modes:
  --mode context   (default) the target sentence shown inside the writer's
                   full comment, plus the previous comment in the same
                   section and the section heading when available. Needs
                   attitude_sample_context.csv from add_context.py.
  --mode sentence  the same prompt with only the target sentence, as a
                   no-context comparison.

Backends (picked automatically):
  - anthropic SDK, if ANTHROPIC_API_KEY is set
  - `claude -p --model opus` (Claude Code headless mode) otherwise

Opus is the default labeler. On a 200-sentence check, a second Opus run
agreed with the first 92% of the time (kappa .91), Haiku 5.5 74%, and
Sonnet 5.5 66%, with Sonnet much worse in English than Japanese.

Usage:
  python wiki_corpus/label_attitudes.py                 # full context run (resumes)
  python wiki_corpus/label_attitudes.py --limit 40      # smoke test
  python wiki_corpus/label_attitudes.py --mode sentence --ids ids.txt

Each batch is appended to attitude_results/attitude_labels_{mode}[_{model}].jsonl
as it finishes (model is omitted for opus), so runs are safe to interrupt and
resume. The merged result is the matching attitude_labeled_*.csv.
"""

import argparse
import json
import os
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.sax.saxutils import escape

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "attitude_results")
PROMPT_FILE = os.path.join(HERE, "prompts", "attitude_context_prompt.txt")

WORKERS = 4
BATCH_SIZE = {"context": 8, "sentence": 20}
# CLI alias -> SDK model id
MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5",
          "haiku": "claude-haiku-5-5"}

ATTITUDES = ["warning", "non-committal", "acknowledging", "encouraging",
             "annoyed", "neutral-positive", "neutral-negative", "other"]
MASK = {"en": "___", "jp": "◯◯"}


def paths(mode, model="opus"):
    sample = os.path.join(OUT_DIR, "attitude_sample_context.csv"
                          if mode == "context" else "attitude_sample.csv")
    suffix = mode + ("" if model == "opus" else f"_{model}")
    return (sample,
            os.path.join(OUT_DIR, f"attitude_labels_{suffix}.jsonl"),
            os.path.join(OUT_DIR, f"attitude_labeled_{suffix}.csv"))


def render_item(r, mode) -> str:
    parts = [f'<item id="{r.id}">']
    if mode == "context":
        if r.section:
            parts.append(f"<section>{escape(r.section)}</section>")
        if r.prev_comment:
            parts.append(f"<previous_comment>{escape(r.prev_comment)}</previous_comment>")
        # comment already contains the literal <target> tags; escape the rest
        body = escape(r.comment).replace("&lt;target&gt;", "<target>") \
                                .replace("&lt;/target&gt;", "</target>")
        parts.append(f"<comment>{body}</comment>")
    else:
        parts.append(f"<comment><target>{escape(r.masked_sentence)}</target></comment>")
    parts.append("</item>")
    return "\n".join(parts)


def build_prompt(batch: pd.DataFrame, mode: str, template: str) -> str:
    header = template.replace("{mask}", MASK[batch.iloc[0]["lang"]])
    return header + "\n\n".join(render_item(r, mode) for r in batch.itertuples())


LINE_RE = re.compile(
    r"^\s*([a-z]{2}-[0-9a-f]{10})\s*\t\s*([a-z-]+)\s*(?:\t\s*([123]))?\s*$")


def parse_response(text: str, valid_ids: set) -> dict:
    out = {}
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if m and m.group(1) in valid_ids and m.group(2) in ATTITUDES:
            out[m.group(1)] = (m.group(2), int(m.group(3)) if m.group(3) else None)
    return out


# --- backends ---------------------------------------------------------------

def make_cli_caller(model: str):
    def call(prompt: str) -> str:
        res = subprocess.run(
            ["claude", "-p", "--model", model],
            input=prompt, capture_output=True, text=True, timeout=900)
        if res.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {res.stderr[:500]}")
        return res.stdout
    return call


def make_sdk_caller(model: str):
    import anthropic
    client = anthropic.Anthropic()
    model_id = MODELS[model]

    def call(prompt: str) -> str:
        if model == "haiku":   # plain request; no effort or fallback options
            resp = client.messages.create(
                model=model_id, max_tokens=4000,
                messages=[{"role": "user", "content": prompt}])
        else:
            resp = client.beta.messages.create(
                model=model_id, max_tokens=4000,
                output_config={"effort": "high"},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                messages=[{"role": "user", "content": prompt}])
        if resp.stop_reason == "refusal":
            raise RuntimeError("model refused the batch")
        return "".join(b.text for b in resp.content if b.type == "text")
    return call


def pick_backend(model: str):
    if os.environ.get("ANTHROPIC_API_KEY"):
        print(f"backend: anthropic SDK ({MODELS[model]})")
        return make_sdk_caller(model)
    print(f"backend: claude CLI (headless, --model {model})")
    return make_cli_caller(model)


# --- driver ------------------------------------------------------------------

def load_done(labels_jsonl) -> dict:
    done = {}
    if os.path.exists(labels_jsonl):
        with open(labels_jsonl) as f:
            for line in f:
                rec = json.loads(line)
                done[rec["id"]] = (rec["attitude"], rec.get("confidence"))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["context", "sentence"], default="context")
    ap.add_argument("--limit", type=int, default=None,
                    help="label only about N unlabeled sentences (split across languages)")
    ap.add_argument("--ids", default=None,
                    help="file with one sentence id per line to restrict labeling to")
    ap.add_argument("--model", choices=list(MODELS), default="opus")
    ap.add_argument("--workers", type=int, default=WORKERS,
                    help="parallel requests")
    args = ap.parse_args()

    sample, labels_jsonl, labeled_csv = paths(args.mode, args.model)
    template = open(PROMPT_FILE, encoding="utf-8").read()
    df = pd.read_csv(sample, keep_default_na=False)
    if args.ids:
        keep = {l.strip() for l in open(args.ids) if l.strip()}
        df = df[df["id"].isin(keep)]
    done = load_done(labels_jsonl)
    # random order, so a partial run is a random subset rather than the
    # first modifiers alphabetically
    todo = df[~df["id"].isin(done)].sample(frac=1, random_state=0)
    if args.limit:
        todo = todo.groupby("lang", group_keys=False).head(args.limit // 2 + 1)
    print(f"mode={args.mode} model={args.model}: {len(done)} already labeled, "
          f"{len(todo)} to go")

    call = pick_backend(args.model)
    lock = threading.Lock()

    def process(batch: pd.DataFrame) -> dict:
        prompt = build_prompt(batch, args.mode, template)
        labels = parse_response(call(prompt), set(batch["id"]))
        with lock, open(labels_jsonl, "a") as f:
            for i, (a, c) in labels.items():
                f.write(json.dumps({"id": i, "attitude": a, "confidence": c}) + "\n")
        return labels

    size = BATCH_SIZE[args.mode]
    for attempt in range(3):           # re-queue ids that failed to parse
        if todo.empty:
            break
        # interleave languages so both progress together
        per_lang = [[grp.iloc[i:i + size] for i in range(0, len(grp), size)]
                    for _, grp in todo.groupby("lang")]
        batches = [b for tier in zip(*per_lang) for b in tier]
        longest = max(per_lang, key=len)
        batches += longest[len(batches) // len(per_lang):]
        print(f"pass {attempt + 1}: {len(batches)} batches of <= {size}")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(process, b) for b in batches]
            n = 0
            for fut in as_completed(futures):
                try:
                    got = fut.result()
                except Exception as e:
                    print(f"  batch failed: {e}")
                    got = {}
                n += len(got)
                print(f"  +{len(got)} ({n} this pass)", flush=True)
        done = load_done(labels_jsonl)
        todo = df[~df["id"].isin(done)]
        if args.limit:
            break

    done = load_done(labels_jsonl)
    df["attitude"] = df["id"].map(lambda i: done.get(i, (None, None))[0])
    df["confidence"] = df["id"].map(lambda i: done.get(i, (None, None))[1])
    # context columns stay in the (regenerable) sample file, not the results
    df.drop(columns=[c for c in ("comment", "prev_comment", "section")
                     if c in df.columns]).to_csv(labeled_csv, index=False)
    print(f"\nlabeled {df['attitude'].notna().sum()}/{len(df)} -> {labeled_csv}")
    print(df.groupby("lang")["attitude"].value_counts().to_string())


if __name__ == "__main__":
    main()
