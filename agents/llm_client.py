from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_gpt(prompt, system_role, model_name="gpt-5.4-mini", temperature=0.2):
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )

        return response.choices[0].message.content

    except Exception as e:
        print(" OpenAI Error:", e)
        return ""