import bz2
import json
import re
import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
client = genai.Client(
    api_key=os.getenv("google_api_key")
)
def extract_sentence_with_context(record, phrase, context_sentences=3):
    """Extract sentence containing phrase with surrounding sentences from record"""
    
    text = record.get('text', '')
    
    if not text or phrase.lower() not in text.lower():
        return None
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?;])\s+', text)
    
    # Find target sentence
    target_idx = None
    target_sentence = None
    for i, sent in enumerate(sentences):
        if phrase.lower() in sent.lower():
            target_idx = i
            target_sentence = sent
            break
    
    if target_idx is None:
        return None
    
    # Get context
    start_idx = max(0, target_idx - context_sentences)
    end_idx = min(len(sentences), target_idx + context_sentences + 1)
    
    return {
        'page_id': record['page_id'],
        'title': record['title'],
        'timestamp': record['timestamp'],
        'last_editor': record['last_editor'],
        'phrase': phrase,
        'target_sentence': target_sentence,
        'before_context': ' '.join(sentences[start_idx:target_idx]),
        'after_context': ' '.join(sentences[target_idx + 1:end_idx]),
        'full_context': ' '.join(sentences[start_idx:end_idx]),
        'full_page_text': text,  # Keep full text available
        'sentence_position': f"{target_idx + 1}/{len(sentences)}"
    }

# Process all records
def analyze_with_sentence_context(input_file, phrase, output_file='analysis.jsonl'):
    """Extract sentence contexts and analyze"""
    
    contexts = []
    
    with bz2.open(input_file, 'rt', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            
            context = extract_sentence_with_context(record, phrase, context_sentences=3)
            if context:
                contexts.append(context)
            if len(contexts) > 5:
                break
    
    # Save contexts
    with open(output_file, 'w', encoding='utf-8') as f:
        for ctx in contexts:
            f.write(json.dumps(ctx, ensure_ascii=False) + '\n')
    
    print(f"Found {len(contexts)} instances of '{phrase}'")
    
    # Analyze each with LLM
    for ctx in contexts[:10]:  # First 10
        prompt = f"""Analyze "{ctx['phrase']}" in this Wikipedia discussion:

PAGE: {ctx['title']}

CONTEXT BEFORE:
{ctx['before_context']}

TARGET SENTENCE (contains "{ctx['phrase']}"):
{ctx['target_sentence']}

CONTEXT AFTER:
{ctx['after_context']}

Answer the following question:
- In one sentence, what is being discussed in this part of the talk page?
- Is "{ctx['phrase']}" used for politeness/hedging? Provide a one sentence explanation, and output a number from 1 (not used for politeness at all) to 5 (clearly used for politeness).
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        print(f"\n=== {ctx['title']} ===")
        print(response.text)
        print("-" * 80)
    
    return contexts

# Usage
contexts = analyze_with_sentence_context(
    'user_talks_simple.jsonl.bz2',
    'a bit'
)
print(f"{[c['target_sentence'] for c in contexts]}")