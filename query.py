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
df = pd.read_csv('PolitenessScenario.csv')[['baseline', 'c1', 'politeness question']] # change this to predicate question for the how cold? questions
modifiers = ['slightly','kind of','quite', 'very', 'extremely']
def create_combined_prompt(c1,baseline,predicate, question, modifier):
    # create combined prompt with the **4** scenarios in random order
    # generate in random order, 4 combinations of modified and unmodified scenarios with c1 or baseline
    scenarios = [
        (baseline.replace('[modifier] ', ''), 0),
        (baseline.replace('[modifier]', modifier), 1),
        (c1.replace('[modifier] ', ''), 2),
        (c1.replace('[modifier]', modifier), 3),
    ]
    random.shuffle(scenarios)

    combined_prompt = f"""In this scenario, {question}

    Please rate the following four scenarios on a scale from not polite at all (0) to as polite as possible (100).

    Scenario 1: 
    {scenarios[0][0]}

    Scenario 2: 
    {scenarios[1][0]}

    Scenario 3: 
    {scenarios[2][0]}

    Scenario 4: 
    {scenarios[3][0]}

    Output your response as JSON in this exact format:
    {{"scenario1": <number>, "scenario2": <number>, "scenario3": <number>, "scenario4": <number>}}

    Output nothing but the JSON.
    """
    return combined_prompt,[s[1] for s in scenarios]

list_outputs = []
for modifier in modifiers:
    for index, row in df.iterrows():
        baseline = row['baseline']
        c1 = row['c1']
        question = row['politeness question']
        
        scenario_values = ["","","",""]
        for attempt in range(3):
            combined_prompt, scenario_indices = create_combined_prompt(c1,baseline,predicates[int(index/5)],question,modifier)
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=combined_prompt,
            )
            response_text = response.text.strip()
            try:
                # Remove code block markers if present
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                
                data = json.loads(response_text)
                scenario_values[scenario_indices[0]] = scenario_values[scenario_indices[0]] + str(data['scenario1']) + ", "
                scenario_values[scenario_indices[1]] = scenario_values[scenario_indices[1]] + str(data['scenario2']) + ", "
                scenario_values[scenario_indices[2]] = scenario_values[scenario_indices[2]] + str(data['scenario3']) + ", "
                scenario_values[scenario_indices[3]] = scenario_values[scenario_indices[3]] + str(data['scenario4']) + ", "
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing JSON response: {response_text}")
                print(f"Error: {e}")
            print("queried")
        if index==0:
            print(f"Modifier: {modifier}")
            print(f"Prompt: {combined_prompt}")
            print(f"Response: {response_text}")
            print(scenario_values)
        list_outputs.append([modifier,question] + scenario_values)

        # save as pandas dataframe
df_outputs = pd.DataFrame(list_outputs, columns=['modifier', 'question', 'baseline_unmodified', 'baseline_modified', 'c1_unmodified', 'c1_modified'])
df_outputs.to_csv('response_politeness.csv', index=False)