# query 
import pandas as pd
from dotenv import load_dotenv
import os
import json
import time
import random
load_dotenv()
from google import genai
client = genai.Client(
    api_key=os.getenv("google_api_key")
)
predicates = ['cold', 'loud', 'messy', 'long']
df = pd.read_csv('PolitenessScenario.csv')[['baseline', 'c1', 'predicate question']] # change this to predicate question for the how cold? questions
modifiers = ['slightly','kind of','quite', 'very', 'extremely']

list_outputs = []
starting_string = "Please rate the following scenarios on a scale from not cold/loud/messy/long at all (0) to as cold/loud/messy/long as possible (100)."
ending_string = """Output your response as list in this exact format:
[ <answer_to_scenario1>, <answer_to_scenario2>, <answer_to_scenario3>, <answer_to_scenario4>,....... ]

for example:
[ 11, 74, 32, 6, 90, ....]

Output nothing but the list."""
rows_list = []

for modifier in modifiers:
    for index, row in df.iterrows():
        rows_list.append([row["predicate question"], row["baseline"].replace('[modifier] ', '')])
        rows_list.append([row["predicate question"], row["baseline"].replace('[modifier]', modifier)])
        rows_list.append([row["predicate question"], row["c1"].replace('[modifier] ', '')])
        rows_list.append([row["predicate question"], row["c1"].replace('[modifier]', modifier)])

scenarios = pd.DataFrame(rows_list, columns=['question', 'scenario'])
scenario_values =[""]*scenarios.shape[0]
for attempt in range(3):
    shuffled_indices = list(range(scenarios.shape[0]))
    prompt = starting_string + "\n\n"
    for i in range(len(shuffled_indices)):
        prompt += f"Scenario {i+1}:\n{scenarios.iloc[shuffled_indices[i]]['scenario']}\nQuestion: {scenarios.iloc[shuffled_indices[i]]['question']}\n\n"
    prompt += ending_string
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    response_text = response.text.strip()
    try:
    # Find and extract just the list part
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        answer = json.loads(response_text[start:end])
        for i in range(len(scenario_values)):
            scenario_values[shuffled_indices[i]] += str(answer[i]) + ", "
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing JSON response: {response_text}")
        print(f"Error: {e}")
#     print("queried")
list_outputs = [
    [modifier[int(i/20)], scenarios.iloc[4*i]['question']] + scenario_values[4*i:4*i+4]
    for i in range(len(scenario_values)//4)
]

        # save as pandas dataframe
df_outputs = pd.DataFrame(list_outputs, columns=['modifier', 'question', 'baseline_unmodified', 'baseline_modified', 'c1_unmodified', 'c1_modified'])
df_outputs.to_csv('response_politeness.csv', index=False)