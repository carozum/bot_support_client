# pour isoler la logique liée à OpenAI et pouvoir changer de  modèle plus facilement
import os
import openai

def ask_openai(question: str) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY", "fake-key-for-tests")

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui aide à comprendre une documation en ligne"},
            {"role": "user", "content": question}
        ]
    )

    return response.choices[0].message.content
