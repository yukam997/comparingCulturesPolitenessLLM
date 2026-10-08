"""
Extract talk-page sentences in which one of the behavioral experiment's
degree modifiers directly modifies an adjective, processing English and
Japanese the same way.

Input: raw/{en,jp}_talk_pages.jsonl from fetch_talk_pages.py (random article
talk, ns 1, and user talk, ns 3, pages).

Each page is split into signed comments: a comment ends at a line carrying a
signature timestamp, and a section heading starts a new section. The
signature (user links and timestamp) is cut off, the comment is cleaned of
wiki markup, and split into sentences.

A hit is kept only when the modifier modifies an adjective, the
construction in the experiment's sentences ("It was ___ funny"). Two
routes, either of which keeps a hit:
  adjacency: the modifier is directly followed by the adjective.
    EN (spaCy tags): single-word modifiers must be tagged as adverbs and be
    followed by a gradable adjective, so determiner and complementizer
    "that" ("that small town", "I assume that ...") are out.
    JP (fugashi + UniDic): the modifier must cover whole tokens and be
    followed by an adjective (形容詞, other than ない) or an adjectival noun
    (形状詞), which excludes compounds and other senses (超能力, ややこしい,
    大分県, に対して) and verb uses (ちょっと待って).
  dependency: spaCy's parser (en_core_web_sm, ja_core_news_sm) attaches the
    modifier to an adjective predicate that follows it, which catches
    modifiers separated from their adjective, common in Japanese
    (あまり日本の映画は面白くない). Checked against the parsers, adjacency
    alone caught 78% of English but only 55% of Japanese uses.
In both routes "that" and "so" must be predicative (not followed by a
noun), "kind of" can't follow a determiner ("some kind of"), and "at all"
needs a negated adjective just before it.

Every occurrence of the modifier in the sentence is masked (EN "___",
JP "◯◯"), so the attitude labeler can't see it.

Output: {en,jp}_experiment_modifier_sentences.csv with columns
  lang, page, ns, section, comment_ix, sentence, masked_sentence, modifier,
  matched, adjective, negated, predicative

Usage (needs spaCy + en_core_web_sm and fugashi + unidic-lite):
  python wiki_corpus/extract_experiment_modifiers.py [en|jp|both]
"""

import json
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

EN_MODIFIERS = [
    "a bit", "a little bit", "a little", "a tad", "absolutely", "amazingly",
    "at all", "clearly", "completely", "damn", "exceptionally", "extremely",
    "incredibly", "kind of", "kinda", "majorly", "mildly", "moderately",
    "pretty", "quite", "really", "semi", "slightly", "so", "somewhat",
    "sorta", "that", "too", "totally", "very",
]
JP_MODIFIERS = [
    "あまり", "いまいち", "かなり", "すごく", "そこまで", "それほど", "そんなに",
    "たいして", "だいぶ", "ちっとも", "ちょっと", "とても", "なかなか", "ひどく",
    "まあまあ", "めっちゃ", "やや", "マジで", "全く", "全然", "少しも", "少し",
    "微妙に", "普通に", "本当に", "相当", "結構", "若干", "超", "非常に",
]

# orthographic variants normalized to the canonical candidate form, applied
# to both the corpus extraction and participants' free responses
JP_VARIANTS = {
    "まったく": "全く", "ぜんぜん": "全然", "けっこう": "結構",
    "凄く": "すごく", "あんまり": "あまり", "すこし": "少し",
    "ほんとうに": "本当に", "ほんとに": "本当に", "ホントに": "本当に",
    "まじで": "マジで",
}

MASK = {"en": "___", "jp": "◯◯"}

# --------------------------------------------------- page -> comments ---

TIMESTAMP = {
    "en": re.compile(r"\d{1,2}:\d{2}, \d{1,2} [A-Z][a-z]+ \d{4} \(UTC\)"),
    "jp": re.compile(r"\d{4}年\d{1,2}月\d{1,2}日 \([日月火水木金土]\) "
                     r"\d{1,2}:\d{2} \(UTC\)"),
}
# where a signature starts on its line: a user/contributions link or an
# unsigned template; failing that, the timestamp itself
SIG_START = re.compile(
    r"(?:-{1,2}|—|–|―)?\s*(?:\[\[(?:User|User talk|Special:Contributions|"
    r"利用者|利用者‐会話|利用者・トーク|利用者‐ノート|特別:投稿記録)[:：]"
    r"|\{\{\s*(?:unsigned|Unsigned|unsigned2|署名なし))")
HEADING = re.compile(r"^\s*(={2,})\s*(.+?)\s*\1\s*$")


def split_comments(raw: str, lang: str):
    """Yield (section, comment_ix, raw_comment_text) for a page."""
    ts = TIMESTAMP[lang]
    section, buf, ix = "", [], 0
    for line in raw.splitlines():
        h = HEADING.match(line)
        if h:
            if any(l.strip() for l in buf):
                yield section, ix, "\n".join(buf)
                ix += 1
            section, buf = clean(h.group(2)), []
            continue
        m = ts.search(line)
        if m:
            s = SIG_START.search(line[:m.start()])
            buf.append(line[:s.start() if s else m.start()])
            yield section, ix, "\n".join(buf)
            ix += 1
            buf = []
        else:
            buf.append(line)
    if any(l.strip() for l in buf):
        yield section, ix, "\n".join(buf)


def clean(t: str) -> str:
    t = t.replace('\\"', '"').replace("\\/", "/")
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    prev = None
    while prev != t:                                   # nested templates
        prev = t
        t = re.sub(r"\{\{[^{}]*\}\}", " ", t)
    t = re.sub(r"\{\|.*?\|\}", " ", t, flags=re.S)     # tables
    t = re.sub(r"\[\[(?:File|Image|ファイル|画像|Category|カテゴリ):[^\]]*\]\]",
               " ", t, flags=re.I)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+ ([^\]]+)\]", r"\1", t)
    t = re.sub(r"https?://\S+", "<url>", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"&\w+;", " ", t)
    t = re.sub(r"(?m)^[\s:*#;]+", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


SENT_SPLIT = {"en": re.compile(r"(?<=[.!?])\s+"),
              "jp": re.compile(r"(?<=[。！？!?])\s*")}
SENT_LEN = {"en": (25, 350), "jp": (8, 200)}


def page_sentences(page: dict, lang: str):
    """Yield (section, comment_ix, sentence) for every sentence on a page."""
    lo, hi = SENT_LEN[lang]
    for section, ix, text in split_comments(page.get("text", "") or "", lang):
        for sent in SENT_SPLIT[lang].split(clean(text)):
            sent = sent.strip()
            if lo <= len(sent) <= hi:
                yield section, ix, sent


def iter_pages(lang):
    path = os.path.join(HERE, "raw", f"{lang}_talk_pages.jsonl")
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


# ---------------------------------------------------------------- English ---

EN_CAND = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in
                      sorted(EN_MODIFIERS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE)
NON_GRADABLE = {"much", "many", "little", "few", "more", "less", "fewer",
                "other", "same", "such", "own", "only", "whole", "last",
                "next", "first"}
SINGLE = {m for m in EN_MODIFIERS if " " not in m}
NEGATORS = {"not", "n't", "never", "no", "nothing", "nobody", "none"}


def _adj(tok) -> bool:
    return tok.pos_ == "ADJ" and tok.is_alpha and tok.lower_ not in NON_GRADABLE


def _predicative(doc, adj) -> bool:
    nxt = doc[adj.i + 1] if adj.i + 1 < len(doc) else None
    return nxt is None or nxt.pos_ not in ("NOUN", "PROPN")


def _negated(doc, mod_start, adj) -> bool:
    if any(c.dep_ == "neg" for c in adj.children) or \
            any(c.dep_ == "neg" for c in adj.head.children):
        return True
    return any(t.lower_ in NEGATORS for t in doc[max(0, mod_start - 4):mod_start])


def en_hits(doc):
    """Yield (modifier, mod_start_tok, mod_end_tok, adjective_tok)."""
    for tok in doc:
        low, i = tok.lower_, tok.i
        nxt = doc[i + 1] if i + 1 < len(doc) else None
        prev = doc[i - 1] if i >= 1 else None
        if low in SINGLE and nxt is not None and _adj(nxt):
            if low in ("damn", "semi", "kinda", "sorta"):
                ok = True
            else:
                ok = tok.tag_ in ("RB", "RBR", "RBS")
            if low in ("that", "so") and not _predicative(doc, nxt):
                ok = False
            if ok:
                yield low, i, i, nxt
        elif low == "bit" and nxt is not None and _adj(nxt) and prev is not None:
            if prev.lower_ == "little" and i >= 2 and doc[i - 2].lower_ == "a":
                yield "a little bit", i - 2, i, nxt
            elif prev.lower_ == "a":
                yield "a bit", i - 1, i, nxt
        elif low in ("little", "tad") and prev is not None and prev.lower_ == "a" \
                and nxt is not None and _adj(nxt):
            yield ("a little" if low == "little" else "a tad"), i - 1, i, nxt
        elif low == "of" and prev is not None and prev.lower_ == "kind" \
                and nxt is not None and _adj(nxt):
            before = doc[i - 2] if i >= 2 else None
            if before is None or before.pos_ not in ("DET", "ADJ", "NUM", "PRON"):
                yield "kind of", i - 1, i, nxt
        elif low == "all" and prev is not None and prev.lower_ == "at":
            adj = next((w for w in reversed(doc[max(0, i - 5):i - 1]) if _adj(w)), None)
            if adj is not None and _negated(doc, adj.i, adj):
                yield "at all", i - 1, i, adj


def _resolve_adj(h):
    """The adjective a modifier's parse head stands for: the head itself, or
    the predicate adjective of a copula the parser attached it to."""
    if _adj(h):
        return h
    if h.lemma_ == "be" or h.pos_ == "AUX":
        return next((c for c in h.children if c.dep_ == "acomp" and _adj(c)), None)
    return None


def en_dep_hits(doc):
    """Hits the dependency parse attaches to an adjective, which catches
    modifiers that aren't directly before it. Same word-specific guards as
    en_hits; the modifier must precede its adjective."""
    for tok in doc:
        low, i = tok.lower_, tok.i
        prev = doc[i - 1] if i >= 1 else None
        nxt = doc[i + 1] if i + 1 < len(doc) else None
        span = None
        if low in SINGLE and tok.dep_ in ("advmod", "npadvmod"):
            if low in ("damn", "semi", "kinda", "sorta") or \
                    tok.tag_ in ("RB", "RBR", "RBS"):
                span = (low, i, i)
        elif low == "bit" and prev is not None:
            if prev.lower_ == "little" and i >= 2 and doc[i - 2].lower_ == "a":
                span = ("a little bit", i - 2, i)
            elif prev.lower_ == "a":
                span = ("a bit", i - 1, i)
        elif low in ("little", "tad") and prev is not None and prev.lower_ == "a" \
                and not (nxt is not None and nxt.lower_ == "bit"):
            span = ("a little" if low == "little" else "a tad", i - 1, i)
        elif low == "kind" and nxt is not None and nxt.lower_ == "of":
            if prev is None or prev.pos_ not in ("DET", "ADJ", "NUM", "PRON"):
                span = ("kind of", i, i + 1)
        if span is None:
            continue
        adj = _resolve_adj(tok.head)
        # English degree modifiers sit within a few words of their adjective;
        # sentence-initial or distant ones are discourse uses ("So it's true")
        if adj is None or adj.i <= span[2] or adj.i - span[2] > 3 \
                or span[1] == 0 or (doc[span[2] + 1].is_punct):
            continue
        # only adverbs (or "not") may intervene: "really mutually exclusive",
        # not ", so it is necessary" or "it really is frustrating"
        if any(t.pos_ != "ADV" and t.lower_ not in ("not", "n't")
               for t in doc[span[2] + 1:adj.i]):
            continue
        if span[0] in ("that", "so") and not _predicative(doc, adj):
            continue
        yield span[0], span[1], span[2], adj


def en_mask(sentence: str, modifier: str) -> str:
    pat = re.compile(r"\b" + re.escape(modifier) + r"\b", re.IGNORECASE)
    return pat.sub(MASK["en"], sentence)


def extract_en():
    import spacy
    nlp = spacy.load("en_core_web_sm", exclude=["ner", "lemmatizer"])
    meta, sents = [], []
    for page in iter_pages("en"):
        for section, ix, sent in page_sentences(page, "en"):
            if EN_CAND.search(sent):
                meta.append((page["title"], page["ns"], section, ix))
                sents.append(sent)
    print(f"EN: {len(sents)} candidate sentences; parsing...")
    rows = []
    for (title, ns, section, ix), doc in zip(meta, nlp.pipe(sents, batch_size=256)):
        seen = set()
        for mod, s, e, adj in list(en_hits(doc)) + list(en_dep_hits(doc)):
            if mod in seen:
                continue
            seen.add(mod)
            rows.append(dict(
                lang="en", page=title, ns=ns, section=section, comment_ix=ix,
                sentence=doc.text, masked_sentence=en_mask(doc.text, mod),
                modifier=mod, matched=doc[s:e + 1].text, adjective=adj.lower_,
                negated=_negated(doc, s, adj), predicative=_predicative(doc, adj)))
    write(rows, "en")


# --------------------------------------------------------------- Japanese ---

JP_FORMS = {m: m for m in JP_MODIFIERS}
JP_FORMS.update(JP_VARIANTS)
JP_CAND = re.compile("|".join(re.escape(f) for f in
                              sorted(JP_FORMS, key=len, reverse=True)))
JP_NEG = re.compile(r"^(?:く|じゃ|では|でも|で)?(?:は|も)?"
                    r"(?:ない|なく|なかっ|ありません|ません|ず)")


def jp_hits(sent, tagger):
    """Yield (canonical, matched_form, start, end, adj_surface, negated,
    predicative) for modifier hits that cover whole tokens and are
    immediately followed by an adjective or adjectival noun."""
    toks, pos = [], 0
    for w in tagger(sent):
        start = sent.find(w.surface, pos)
        toks.append((start, start + len(w.surface), w.surface, w.feature.pos1))
        pos = start + len(w.surface)
    starts = {t[0]: k for k, t in enumerate(toks)}
    ends = {t[1]: k for k, t in enumerate(toks)}
    for m in JP_CAND.finditer(sent):
        if m.start() not in starts or m.end() not in ends:
            continue
        k = ends[m.end()] + 1
        if k >= len(toks):
            continue
        a_start, a_end, a_surf, a_pos = toks[k]
        if a_pos not in ("形容詞", "形状詞") or a_surf in ("ない", "無い"):
            continue
        rest = sent[a_end:a_end + 8]
        after = toks[k + 1] if k + 1 < len(toks) else None
        attributive = after is not None and (
            after[3] == "名詞" or (after[2] == "な" and k + 2 < len(toks)
                                   and toks[k + 2][3] == "名詞"))
        yield (JP_FORMS[m.group(0)], m.group(0), m.start(), m.end(), a_surf,
               bool(JP_NEG.match(rest)), not attributive)


JP_NEG_FORMS = {"ない", "なく", "なかっ", "無い", "ず", "ぬ", "ません"}


def jp_dep_hits(doc):
    """Hits the dependency parse (spaCy ja_core_news_sm) attaches to an
    adjective predicate, which catches modifiers separated from their
    adjective (あまり日本の映画は面白くない). The parser heads a negated
    adjective on ない, so a negation or auxiliary head is resolved to the
    adjective just before it. The match must cover whole tokens and precede
    its adjective."""
    text = doc.text
    for m in JP_CAND.finditer(text):
        # あまりに/あまりの mean "excessively"/"excessive", not "not very"
        if JP_FORMS[m.group(0)] == "あまり" and text[m.end():m.end() + 1] in ("に", "の"):
            continue
        toks = [t for t in doc if t.idx < m.end() and t.idx + len(t.text) > m.start()]
        if not toks or toks[0].idx != m.start() or \
                toks[-1].idx + len(toks[-1].text) != m.end():
            continue
        ids = {t.i for t in toks}
        outside = [t for t in toks if t.head.i not in ids]
        if not outside:
            continue
        h = outside[-1].head
        if (h.text in JP_NEG_FORMS or h.pos_ == "AUX") and h.i > 0 \
                and doc[h.i - 1].pos_ == "ADJ":
            h = doc[h.i - 1]
        if h.pos_ != "ADJ" or h.text in ("ない", "無い") or h.idx < m.end():
            continue
        a_end = h.idx + len(h.text)
        after = doc[h.i + 1] if h.i + 1 < len(doc) else None
        if after is not None and after.text == "な" and h.i + 2 < len(doc):
            after = doc[h.i + 2]
        attributive = after is not None and after.pos_ in ("NOUN", "PROPN")
        yield (JP_FORMS[m.group(0)], m.group(0), m.start(), m.end(), h.text,
               bool(JP_NEG.match(text[a_end:a_end + 8])), not attributive)


def jp_mask(sentence: str, canonical: str, tagger) -> str:
    """Mask every whole-token occurrence of the modifier or its variants."""
    forms = [f for f, c in JP_FORMS.items() if c == canonical]
    toks, pos = [], 0
    for w in tagger(sentence):
        start = sentence.find(w.surface, pos)
        toks.append((start, start + len(w.surface)))
        pos = start + len(w.surface)
    starts = {s for s, _ in toks}
    ends = {e for _, e in toks}
    spans = [(m.start(), m.end()) for f in forms
             for m in re.finditer(re.escape(f), sentence)
             if m.start() in starts and m.end() in ends]
    out = sentence
    for s, e in sorted(spans, reverse=True):
        out = out[:s] + MASK["jp"] + out[e:]
    return out


def extract_jp():
    import fugashi
    import spacy
    tagger = fugashi.Tagger()
    nlp = spacy.load("ja_core_news_sm", exclude=["ner"])
    meta, sents = [], []
    for page in iter_pages("jp"):
        for section, ix, sent in page_sentences(page, "jp"):
            if JP_CAND.search(sent):
                meta.append((page["title"], page["ns"], section, ix))
                sents.append(sent)
    print(f"JP: {len(sents)} candidate sentences; parsing...")
    rows = []
    for (title, ns, section, ix), doc in zip(meta, nlp.pipe(sents, batch_size=256)):
        sent = doc.text
        seen = set()
        for canon, form, s, e, adj, neg, pred in \
                list(jp_hits(sent, tagger)) + list(jp_dep_hits(doc)):
            if canon in seen:
                continue
            seen.add(canon)
            rows.append(dict(
                lang="jp", page=title, ns=ns, section=section,
                comment_ix=ix, sentence=sent,
                masked_sentence=jp_mask(sent, canon, tagger),
                modifier=canon, matched=form, adjective=adj,
                negated=neg, predicative=pred))
    write(rows, "jp")


def write(rows, lang):
    df = pd.DataFrame(rows).drop_duplicates(subset=["page", "sentence", "modifier"])
    out = os.path.join(HERE, f"{lang}_experiment_modifier_sentences.csv")
    df.to_csv(out, index=False)
    print(f"{lang.upper()}: {len(df)} rows -> {out}")
    print(df.groupby("ns")["modifier"].value_counts().unstack(0)
            .fillna(0).astype(int).to_string())


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("en", "both"):
        extract_en()
    if which in ("jp", "both"):
        extract_jp()
