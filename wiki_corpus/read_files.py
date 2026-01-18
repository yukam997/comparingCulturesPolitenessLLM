import pandas as pd

df = pd.read_json('user_talks_simple_ja.jsonl.bz2', lines=True)
# find sentences that contain the word "quite"
df_quite = df[df['text'].str.contains('少し', na=False)]
print(f"Total pages with 'quite': {len(df_quite)}")
# print two examples
for index, row in df_quite[-2:].iterrows():
    print(f"Title: {row['title']}")
    print(f"Text snippet: {row['text']}")
    print("-" * 80)