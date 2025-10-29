import os
from textwrap import dedent
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

SYSTEM_TEMPLATE = dedent("""
You are a precise academic assistant. You ONLY use the provided sources.
Write clear, structured, and faithful outputs. No hallucinations or extra facts.
""").strip()

def build_user_prompt(task: str, words: int, language: str, notes: str, corpus: str) -> str:
    task_map = {
        "summary": "Write a concise summary.",
        "detailed": "Write a detailed, well-structured summary.",
        "study": "Create study notes with bullet points and key takeaways.",
        "presentation": "Create presentation bullet points and sections."
    }
    task_line = task_map.get(task, task_map["summary"])

    return dedent(f"""
    Task: {task_line}
    Target length: ~{words} words (±10%)
    Language: {language}
    Extra user notes (follow strictly if present): {notes or "—"}
    Constraints:
    - Use ONLY the content from the corpus.
    - If information is missing in the corpus, say "Not in sources".
    - Keep formatting simple (no page markers).

    Corpus:
    {corpus[:120000]}  # safety cap
    """).strip()

def call_llm(task: str, words: int, language: str, notes: str, corpus: str) -> str:
    """
    Stable call via Responses API. Returns plain text.
    """
    prompt = build_user_prompt(task, words, language, notes, corpus)

    resp = client.responses.create(
        model=DEFAULT_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_TEMPLATE},
            {"role": "user", "content": prompt}
        ]
    )

    text = getattr(resp, "output_text", None)
    if not text:
        
        try:
            parts = []
            for item in resp.output:
                if hasattr(item, "content"):
                    for c in item.content:
                        if getattr(c, "type", None) == "output_text" and getattr(c, "text", None):
                            parts.append(c.text)
            text = "\n".join(parts).strip()
        except Exception:
            text = ""

    return text or "Not in sources"
