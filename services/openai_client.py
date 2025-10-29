import os
from textwrap import dedent
from openai import OpenAI

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

def _get_client() -> OpenAI:
    # Client-i yalnız ehtiyac olanda qur (startup-da crash olmasın)
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = dedent("""
You are a precise academic assistant. Only use the provided corpus. No hallucinations.
""").strip()

def _prompt(task, words, language, notes, corpus):
    task_map = {
        "summary": "Write a concise summary.",
        "detailed": "Write a detailed, well-structured summary.",
        "study": "Create study notes with bullet points and key takeaways.",
        "presentation": "Create presentation bullets with section headers."
    }
    return dedent(f"""
    Task: {task_map.get(task,'Write a concise summary.')}
    Target length: ~{words} words (±10%)
    Language: {language}
    Extra user notes: {notes or "—"}
    Constraints:
    - Use ONLY the corpus below.
    - If something is missing, say "Not in sources".

    Corpus:
    {corpus[:120000]}
    """).strip()

def call_llm(task, words, language, notes, corpus) -> str:
    client = _get_client()
    resp = client.responses.create(
        model=DEFAULT_MODEL,
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _prompt(task, words, language, notes, corpus)}
        ],
    )
    return getattr(resp, "output_text", "").strip()
