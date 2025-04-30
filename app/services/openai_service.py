# pour isoler la logique liée à OpenAI et pouvoir changer de  modèle plus facilement
import os
import openai

def ask_openai_simple(question: str) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY", "fake-key-for-tests")

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui aide à comprendre une documation en ligne"},
            {"role": "user", "content": question}
        ],
        temperature=0.3,
        top_p=0.5
    )

    return response.choices[0].message.content



def ask_openai(question: str) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY", "fake-key-for-tests")

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui aide à comprendre une documentation en ligne"},
            {"role": "user", "content": question}
        ],
        temperature=0.3,
        top_p=0.5,
        stream=True
    )

    for chunk in response:
        if "choices" in chunk and chunk["choices"][0].get("delta", {}).get("content"):
            yield chunk["choices"][0]["delta"]["content"]
