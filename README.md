# comparingCulturesPolitenessLLM

Code and data for a cross-cultural (English / Japanese) study of politeness
markers, using LLM judgements and BERT-based probability estimates over
ConvoKit corpora and Wikipedia talk pages.

## Setup

### 1. Create a conda environment

Requires [conda](https://docs.conda.io/projects/miniconda/en/latest/)
(miniconda is enough).

```bash
git clone git@github.com:yukam997/comparingCulturesPolitenessLLM.git
cd comparingCulturesPolitenessLLM

conda env create -f environment.yml
conda activate politeness
```

That reads `environment.yml`, which pins Python 3.10 and pip-installs
everything in `requirements.txt`. To create it by hand instead:

```bash
conda create -n politeness python=3.10 -y
conda activate politeness
pip install -r requirements.txt
```

Python 3.10 is the version this project was developed and run on. Newer
versions may work, but `convokit` ships source-only (no wheels), so it is the
most likely thing to break on a newer interpreter.

Then install the spaCy language models (not installable by name from PyPI):

```bash
python -m spacy download en_core_web_sm
python -m spacy download ja_core_news_sm
python -m spacy download ja_core_news_lg
```

### 2. Set your API keys

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable         | Required | Where to get it                                  |
| ---------------- | -------- | ------------------------------------------------ |
| `google_api_key` | yes      | https://aistudio.google.com/apikey                |
| `hf_token`       | optional | https://huggingface.co/settings/tokens            |

`.env` is gitignored — do not commit it. Every script loads it via
`load_dotenv()`, so the keys are picked up automatically as long as you run
from inside the repo.

### 3. Check it works

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
import os
from google import genai
c = genai.Client(api_key=os.getenv('google_api_key'))
print(c.models.generate_content(model='gemini-3-flash-preview', contents='say hi').text)
"
```

If that prints a reply, your key is loading correctly.

## Layout

- `query.py` — minimal Gemini query example
- `finalized_pipeline/` — the main pipeline (`code/`, `data/`)
- `convoKit/` — modifier counting, clustering, and PCA over ConvoKit corpora
- `wiki_corpus/` — Wikipedia talk-page extraction and LLM judgements
- `*.csv`, `*.png` — intermediate results and figures

## Notes

- ConvoKit downloads corpora to `~/.convokit/saved-corpora` on first use.
- The BERT probability scripts in `finalized_pipeline/code/` are written to run
  as SLURM array jobs (`SLURM_ARRAY_TASK_ID` / `SLURM_ARRAY_TASK_COUNT`); they
  default to a single task when those variables are unset.
