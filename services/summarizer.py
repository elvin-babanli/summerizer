# services/summarizer.py
# -*- coding: utf-8 -*-

from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

# Optional imports (fail-soft)
try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception:
    PdfReader = None  # type: ignore

try:
    import docx  # python-docx  # type: ignore
except Exception:
    docx = None  # type: ignore

# OpenAI (v1) fail-soft import
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore


# -----------------------------
# Constants & Config
# -----------------------------

ALLOWED_LANGUAGES: List[str] = [
    "English", "Polish", "Turkish", "Azerbaijani", "Russian", "German",
    "French", "Spanish", "Italian", "Portuguese", "Ukrainian", "Arabic",
    "Chinese", "Japanese", "Korean", "Hindi"
]

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

PROMPT_TEMPLATES: Dict[str, str] = {
    "summary": (
        "You are an expert academic summarizer. Write a concise, faithful, and well-structured **summary** "
        "of the provided sources in {language}, with a target length of ~{words} words (±10%). "
        "Preserve key terms, avoid hallucinations, and do not include content not supported by the sources.\n\n"
        "{notes_block}\n"
        "== SOURCES ==\n{sources}\n\n"
        "== OUTPUT RULES ==\n"
        "- Use clear headings.\n"
        "- Bullet points where useful.\n"
        "- No page markers. No citations unless explicitly present in the text.\n"
    ),
    "detailed": (
        "You are an expert technical writer. Produce a **detailed, structured report** in {language} "
        "based strictly on the provided sources, ~{words} words (±10%). "
        "Explain important concepts with brief, precise definitions and include a short executive summary at the top.\n\n"
        "{notes_block}\n"
        "== SOURCES ==\n{sources}\n\n"
        "== OUTPUT RULES ==\n"
        "- Use H2/H3 headings.\n"
        "- Include short executive summary, key insights, and practical recommendations.\n"
        "- Avoid fabrications. No page markers.\n"
    ),
    "study note": (
        "Create **exam-ready study notes** in {language}, ~{words} words (±10%), strictly from the sources.\n\n"
        "{notes_block}\n"
        "== SOURCES ==\n{sources}\n\n"
        "== OUTPUT RULES ==\n"
        "- Use concise bullet points.\n"
        "- Include formulas or definitions when present.\n"
        "- Add a quick self-check quiz (5 questions) at the end.\n"
        "- No page markers.\n"
    ),
    "presentation": (
        "Create a **presentation-style outline** in {language}, ~{words} words (±10%), based strictly on the sources.\n\n"
        "{notes_block}\n"
        "== SOURCES ==\n{sources}\n\n"
        "== OUTPUT RULES ==\n"
        "- Structure as slides with titles and 3–6 bullets each.\n"
        "- Start with Agenda. End with Key Takeaways.\n"
        "- Keep bullets crisp; no page markers.\n"
    ),
}

TASK_ALIASES = {
    "summary": "summary",
    "summarize": "summary",
    "detailed": "detailed",
    "report": "detailed",
    "study note": "study note",
    "studynote": "study note",
    "notes": "study note",
    "presentation": "presentation",
    "slides": "presentation",
}


# -----------------------------
# Data Models
# -----------------------------

@dataclass
class GenerateOptions:
    task: str = "summary"
    words: int = 800
    language: str = "English"
    notes: str = ""
    output: str = "txt"  # 'txt' | 'docx' | 'pdf'

    def normalized_task(self) -> str:
        t = self.task.strip().lower()
        return TASK_ALIASES.get(t, "summary")

    def clamped_words(self, min_w: int = 200, max_w: int = 20000) -> int:
        try:
            w = int(self.words)
        except Exception:
            w = 800
        return max(min_w, min(max_w, w))

    def normalized_language(self) -> str:
        lang = (self.language or "English").strip()
        # Prefer exact match; else title-case it
        if lang in ALLOWED_LANGUAGES:
            return lang
        lang_tc = lang[:1].upper() + lang[1:].lower()
        return lang_tc if lang_tc in ALLOWED_LANGUAGES else "English"

    def normalized_output(self) -> str:
        out = (self.output or "txt").strip().lower()
        return out if out in {"txt", "docx", "pdf"} else "txt"


# -----------------------------
# File Analyzer
# -----------------------------

class FileAnalyzer:
    @staticmethod
    def extract_corpus(app, max_chars: int = 120_000) -> Tuple[str, Dict[str, Any]]:
        """
        Scans UPLOAD_FOLDER in app.config, reads .pdf/.docx/.txt files,
        concatenates to a corpus capped by max_chars.
        Returns (corpus, metas)
        """
        uploads_dir = app.config.get("UPLOAD_FOLDER", "uploads")
        allowed_exts = {".pdf", ".docx", ".txt"}

        texts: List[str] = []
        metas: Dict[str, Any] = {"files": [], "total_chars": 0}

        if not os.path.isdir(uploads_dir):
            return "", metas

        for name in sorted(os.listdir(uploads_dir)):
            path = os.path.join(uploads_dir, name)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed_exts:
                continue

            content = ""
            try:
                if ext == ".txt":
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                elif ext == ".docx" and docx is not None:
                    doc = docx.Document(path)
                    content = "\n".join(p.text for p in doc.paragraphs)
                elif ext == ".pdf" and PdfReader is not None:
                    reader = PdfReader(path)
                    pages_text = []
                    for page in reader.pages:
                        try:
                            pages_text.append(page.extract_text() or "")
                        except Exception:
                            pages_text.append("")
                    content = "\n".join(pages_text)
            except Exception:
                content = ""

            content = FileAnalyzer._clean_text(content)
            if not content:
                continue

            # Add and clamp
            remaining = max_chars - sum(len(t) for t in texts)
            if remaining <= 0:
                break

            if len(content) > remaining:
                content = content[:remaining]

            texts.append(f"\n\n===== FILE: {name} =====\n{content}")
            metas["files"].append({"name": name, "chars": len(content)})
            metas["total_chars"] = sum(len(t) for t in texts)

            if metas["total_chars"] >= max_chars:
                break

        corpus = "\n".join(texts).strip()
        return corpus, metas

    @staticmethod
    def _clean_text(s: str) -> str:
        if not s:
            return ""
        s = s.replace("\x00", " ")
        s = re.sub(r"[ \t]+", " ", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()


# -----------------------------
# Prompt Builder & Service
# -----------------------------

class SummarizerService:
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        self.model = model or DEFAULT_MODEL
        self.api_key = (api_key if api_key is not None else OPENAI_API_KEY) or ""
        self._client = None
        if self.api_key and OpenAI is not None:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception:
                self._client = None

    @staticmethod
    def build_user_prompt(corpus: str, options: GenerateOptions) -> str:
        task = options.normalized_task()
        language = options.normalized_language()
        words = options.clamped_words()

        notes_block = ""
        if options.notes and options.notes.strip():
            notes_block = f"== USER NOTES ==\n{options.notes.strip()}\n"

        sources = corpus if corpus.strip() else "(No sources uploaded. If no sources, say so and provide only general structure.)"
        template = PROMPT_TEMPLATES.get(task, PROMPT_TEMPLATES["summary"])
        prompt = template.format(language=language, words=words, notes_block=notes_block, sources=sources)
        return prompt.strip()

    def generate(self, corpus: str, options: GenerateOptions) -> str:
        prompt = self.build_user_prompt(corpus, options)

        # If no API key or client, or call fails, fallback to mock
        if (not self._client) or (not self.api_key):
            return self.mock_generate_from_inputs(prompt, options)

        try:
            # OpenAI Responses API (v1)
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a careful assistant that strictly uses the provided sources."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            text = (resp.choices[0].message.content or "").strip()
            return self._post_process(text)
        except Exception:
            return self.mock_generate_from_inputs(prompt, options)

    @staticmethod
    def _post_process(text: str) -> str:
        if not text:
            return ""
        # Remove page markers if any pattern like [Page X], (Page X), --- Page X ---
        text = re.sub(r"\s*\[?Page\s+\d+\]?\s*", " ", text, flags=re.I)
        text = re.sub(r"-{2,}\s*Page\s+\d+\s*-{2,}", " ", text, flags=re.I)
        # Normalize newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def mock_generate_from_inputs(prompt: str, options: GenerateOptions) -> str:
        task = options.normalized_task()
        language = options.normalized_language()
        words = options.clamped_words()

        header_map = {
            "summary": "Executive Summary",
            "detailed": "Detailed Report",
            "study note": "Study Notes",
            "presentation": "Presentation Outline",
        }
        h = header_map.get(task, "Summary")

        # Lightweight deterministic mock respecting language & words intent
        # (We won't actually hit the exact word count; just provide a solid scaffold.)
        blocks = [
            f"# {h} ({language}, ~{words} words)",
        ]

        if task == "presentation":
            blocks += [
                "## Agenda",
                "- Problem Overview\n- Key Insights\n- Method/Approach\n- Results\n- Limitations\n- Key Takeaways",
                "## Slide 1 — Problem Overview",
                "- Brief context\n- Why it matters\n- Scope and objectives",
                "## Slide 2 — Key Insights",
                "- Insight 1\n- Insight 2\n- Insight 3",
                "## Slide 3 — Method/Approach",
                "- Data used\n- Steps\n- Constraints",
                "## Slide 4 — Results",
                "- Result A\n- Result B\n- Result C",
                "## Slide 5 — Limitations",
                "- Data quality\n- Assumptions\n- External factors",
                "## Key Takeaways",
                "- Takeaway 1\n- Takeaway 2\n- Takeaway 3",
            ]
        elif task == "study note":
            blocks += [
                "## Core Concepts",
                "- Term 1: short definition\n- Term 2: short definition\n- Term 3: short definition",
                "## Key Points",
                "- Point A\n- Point B\n- Point C",
                "## Examples",
                "- Example 1\n- Example 2",
                "## Quick Self-Check (5)",
                "1) Question 1?\n2) Question 2?\n3) Question 3?\n4) Question 4?\n5) Question 5?",
            ]
        elif task == "detailed":
            blocks += [
                "## Executive Summary",
                "- High-level overview with main findings.",
                "## Background",
                "- Context and definitions.",
                "## Analysis",
                "- Evidence-backed points derived from sources.",
                "## Recommendations",
                "- Actionable, prioritized steps.",
                "## Conclusion",
                "- Final synthesis.",
            ]
        else:  # summary
            blocks += [
                "## Overview",
                "- Main idea and scope.",
                "## Key Insights",
                "- Insight 1\n- Insight 2\n- Insight 3",
                "## Conclusion",
                "- Short wrap-up.",
            ]

        text = "\n\n".join(blocks)
        return SummarizerService._post_process(text)


# -----------------------------
# Helpers for filenames
# -----------------------------

def safe_lang_token(language: str) -> str:
    """
    Convert language to a clean token for filenames, e.g. 'Polish', 'English (UK)' -> 'Polish', 'EnglishUK'
    """
    token = re.sub(r"[^\w]+", "", language.strip(), flags=re.UNICODE)
    return token or "English"


def build_base_filename(options: GenerateOptions) -> str:
    """
    Returns Task_1500w_Language (e.g., Presentation_1500w_Polish)
    """
    task_token = options.normalized_task().title().replace(" ", "")
    words_token = f"{options.clamped_words()}w"
    lang_token = safe_lang_token(options.normalized_language())
    return f"{task_token}_{words_token}_{lang_token}"
