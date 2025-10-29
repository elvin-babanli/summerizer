from pathlib import Path
from typing import List, Dict, Tuple
from PyPDF2 import PdfReader
import re

ALLOWED_LANGUAGES = [
    "English", "Azerbaijani", "Turkish", "Russian", "Polish",
    "German", "French", "Spanish", "Italian",
    "Arabic", "Chinese", "Japanese", "Korean", "Portuguese", "Dutch"
]

class FileAnalyzer:
    def analyze_file(self, path: Path, ext: str) -> Tuple[int, int]:
        ext = ext.lower()
        if ext == "pdf":
            try:
                reader = PdfReader(str(path))
                pages = len(reader.pages)
                return pages, 0
            except Exception:
                return 0, 0
        elif ext == "docx":
            try:
                from docx import Document
                text = "\n".join(p.text for p in Document(str(path)).paragraphs)
                words = self._count_words(text)
                pages = max(1, words // 300)
                return pages, words
            except Exception:
                return 0, 0
        elif ext == "txt":
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                words = self._count_words(text)
                pages = max(1, words // 500)
                return pages, words
            except Exception:
                return 0, 0
        return 0, 0

    def extract_text(self, path: Path, ext: str, max_chars: int = 60_000) -> str:
        ext = ext.lower()
        text = ""
        try:
            if ext == "pdf":
                reader = PdfReader(str(path))
                for i, page in enumerate(reader.pages, 1):
                    t = page.extract_text() or ""
                    text += f"\n\n[[Page {i}]]\n{t}"
            elif ext == "docx":
                from docx import Document
                doc = Document(str(path))
                text = "\n".join(p.text for p in doc.paragraphs)
            elif ext == "txt":
                text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        if len(text) > max_chars:
            return text[:max_chars] + "\n\n[...trimmed due to length...]"
        return text

    def extract_corpus(self, files: List[Dict], max_chars: int = 120_000) -> Dict[str, str]:
        corpus = {}
        remaining = max_chars
        per_file = max(10_000, remaining // max(1, len(files)))
        for f in files:
            portion = min(per_file, remaining)
            t = self.extract_text(Path(f["path"]), f["ext"], max_chars=portion)
            corpus[f["name"]] = t
            remaining -= len(t)
            if remaining <= 0:
                break
        return corpus

    @staticmethod
    def _count_words(text: str) -> int:
        return len([w for w in text.strip().split() if w])


class SummarizerService:
    def __init__(self):
        import os
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_from_sources(self, corpus: Dict[str, str], options: Dict) -> str:
        system_rules = self._system_prompt(options.get("language", "English"))
        user_prompt = self._build_user_prompt(corpus, options)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_rules},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
        }

        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.api_base}/chat/completions"
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(f"API {r.status_code}: {r.text[:200]}")
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        cleaned = self._postclean(content)
        return cleaned.strip()

    def mock_generate_from_inputs(self, files, options) -> str:
        lines = []
        lines.append("# Result (MOCK)\n")
        lines.append(f"Task: {options.get('task')}")
        lines.append(f"Words target: {options.get('words')}")
        lines.append(f"Language: {options.get('language')}")
        lines.append(f"Output: {options.get('output')}")
        notes = options.get("notes", "").strip()
        if notes:
            lines.append(f"User Notes: {notes}")
        lines.append("\n## Files received:")
        if not files:
            lines.append("No files uploaded.")
        else:
            for i, f in enumerate(files, 1):
                lines.append(f"{i}. {f['name']} — {f['pages']} pages, {round(f['size_bytes']/(1024*1024),2)} MB")
        return "\n".join(lines)

    def _system_prompt(self, language: str) -> str:
        # Dil və mənbə qaydaları + page marker qadağası
        return (
            f"You MUST write ONLY in {language}. No other language.\n"
            "- Use ONLY the provided sources. Don't invent facts.\n"
            "- If a question isn't covered, say: Not found in the provided sources.\n"
            "- Use clear sections, short paragraphs, and bullet points.\n"
            "- Do NOT include any page markers like [Page N] or [Pages a, b] in the output.\n"
            "- Do NOT include raw Markdown/code fences; simple headings (##, ###) and '-' bullets are fine.\n"
        )

    def _build_user_prompt(self, corpus: Dict[str, str], options: Dict) -> str:
        task = options.get("task", "summary")
        words = int(options.get("words", 1500))
        language = options.get("language", "English")
        notes = (options.get("notes") or "").strip()

        task_line = {
            "summary": "Write a concise summary with clear sections.",
            "detailed": "Write a detailed, structured summary.",
            "study": "Create study notes / cheat sheet with key facts, terms, and bullet points.",
            "presentation": "Create a presentation-style outline: slide titles + 3–6 bullets each."
        }.get(task, "Write a concise summary with clear sections.")

        length_hint = (
            f"Length: about {words} words (±10%). "
            f"If sources cannot fully cover that length, use all relevant information available without inventing."
        )

        formatting = (
            "Output format:\n"
            "- Headings with '##' and '###', bullets with '- '.\n"
            "- Do not output any page markers like [Page ...].\n"
        )

        src_chunks = []
        for fname, text in corpus.items():
            src_chunks.append(f"### Source: {fname}\n{text}\n")
        sources_block = "\n".join(src_chunks)

        user_prompt = (
            f"Language: {language}.\n"
            f"Task: {task_line}\n"
            f"{length_hint}\n"
            f"{formatting}\n"
        )
        if notes:
            user_prompt += f"User questions / constraints:\n{notes}\n"

        user_prompt += "\n----\nSOURCES BEGIN\n" + sources_block + "\nSOURCES END\n"
        return user_prompt

    def _postclean(self, text: str) -> str:
        # ehtiyat üçün, hər cür [Page ...] markers tam silinsin
        s = re.sub(r"\[(?:Page|Pages)\s+[^\]]+\]", "", text)
        # çoxlu boşluqları səliqəyə sal
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()
