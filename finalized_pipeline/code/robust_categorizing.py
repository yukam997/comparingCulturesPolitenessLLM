# use syntax parsers to do the categorization of self_neg_mitigate etc
import spacy
import pandas as pd

en_df = pd.read_csv("/Users/yuka/Documents/Academics/Stanford/Research/crossCulturalPoliteness/comparingCulturesPolitenessLLM/finalized_pipeline/data/results/en_data_logprob_combinedJul21.csv")
jp_df = pd.read_csv("/Users/yuka/Documents/Academics/Stanford/Research/crossCulturalPoliteness/comparingCulturesPolitenessLLM/finalized_pipeline/data/results/jp_data_logprob_combinedJul21.csv")

nlp_ja = spacy.load("ja_ginza")

NEGATION_LEMMAS = {"ない", "ません", "ぬ", "ん"}

def is_target_negated(doc, target_index):
    """Checks whether a negation auxiliary is a direct child of the target token."""
    target_token = doc[target_index]
    for child in target_token.children:
        if child.lemma_ in NEGATION_LEMMAS:
            return True
    return False

def extract_modifier_target_ja(sentence, modifier):
    doc = nlp_ja(sentence)
    tokens = [t.text for t in doc]
    modifier_tokens = [t.text for t in nlp_ja(modifier)]
    modifier_len = len(modifier_tokens)

    for i in range(len(tokens) - modifier_len + 1):
        if tokens[i:i + modifier_len] == modifier_tokens:
            first_token = doc[i]
            head = first_token.head
            if head.text in modifier_tokens:
                return None
            negated = is_target_negated(doc, head.i)
            return {
                "modifier": modifier,
                "modifier_pos": first_token.pos_,
                "dep_relation": first_token.dep_,
                "target": head.text,
                "target_pos": head.pos_,
                "target_lemma": head.lemma_,
                "negated": negated,
            }
    return None

# apply across the full dataframe
results = []
for modifier, sentence in jp_df[['modifier', 'sentence']].head(10).values:
    result = extract_modifier_target_ja(sentence, modifier)
    if result is None:
        result = {"modifier": modifier, "modifier_pos": None, "dep_relation": None,
                   "target": None, "target_pos": None, "target_lemma": None, "negated": None}
    print(result,sentence)
    results.append(result)

