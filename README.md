<p align="center">
  <img src="assets/screenshot.png" alt="Summerizer Screenshot" width="900">
</p>

<h1 align="center">🧠 Summarizer — AI-Powered Document Summarizer</h1>

<p align="center">
  <b>Flask · OpenAI · PDF/Text Processing · Deployed on Render</b><br>
  Built to transform lengthy documents into clean, structured summaries — fast and smart.
</p>

---

## 🧩 Overview

**Summarizer** is a production-ready AI web application that automatically summarizes long-form documents (PDF, DOCX, TXT).  
Designed for simplicity and performance, it helps students, researchers, and professionals turn large materials into clear summaries, notes, or presentation outlines — within seconds.

---

## 🚀 Key Features

✅ **Multi-format support** — Upload `.pdf`, `.docx`, or `.txt` files processed securely on the backend.  
✅ **AI-based summarization** — Uses OpenAI API for context-aware summaries with adjustable length and language.  
✅ **Export flexibility** — Download results as `.pdf`, `.docx`, or `.txt`.  
✅ **Session-based workflow** — Each user session is isolated for safe, independent use.  
✅ **Smart file analysis** — Detects file size, page count, and structure before processing.  
✅ **Modern UI** — Clean, responsive interface focused on productivity.  
✅ **Live deployment** — Public demo hosted on Render.

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-------------|
| **Backend** | Python · Flask · Flask-WTF · Flask-Limiter |
| **AI Integration** | OpenAI API (LLM-based summarization) |
| **File Processing** | PyPDF2 · python-docx · io streams |
| **Security** | CSRF protection · Rate limiting · Secure file upload |
| **Frontend** | HTML5 · CSS3 · Jinja templates |
| **Deployment** | Render (Flask Server) |
| **Version Control** | Git + GitHub |

---

## 🧠 Architecture

- **FileAnalyzer:** Extracts and preprocesses text from uploaded documents.  
- **SummarizerService:** Communicates with OpenAI API to generate structured summaries.  
- **Exporter:** Converts generated content into downloadable formats.  

---

## 🎯 Design Philosophy

> “The goal was not just to make it work — but to make it scalable, secure, and usable.”

**Summerizer** was built with a professional software engineering mindset:
- Clean Flask architecture ready for scale.  
- Practical AI integration (OpenAI API).  
- Clear UX/UI flow with accessibility in mind.  
- Secure and modular backend aligned with best practices.

---

## 🌐 Live Demo & Repository

🔗 **Live Demo:** [https://summerizer-ubum.onrender.com](https://summerizer-ubum.onrender.com)  
💻 **GitHub Repository:** [https://github.com/elvin-babanli/summerizer](https://github.com/elvin-babanli/summerizer)

---

## 🧩 Example Use Cases

> “If you have lengthy PDF or Word files — such as research papers, lecture notes, or technical documentation — simply upload them and get a clean summary in seconds.”

Perfect for:
- 🎓 Students creating study notes  
- 🧑‍🔬 Researchers summarizing papers  
- 🏢 Professionals simplifying internal reports  

---

## 🔮 Future Improvements

- [ ] User authentication & history tracking  
- [ ] Multi-document comparison & merging  
- [ ] Enhanced multilingual summarization  
- [ ] Cloud integration (Google Drive, Dropbox)  
- [ ] AI-based slide deck generation  

---

## 🧾 Summary

**Summerizer** demonstrates:
- Full-stack development capability  
- API integration & backend architecture  
- Secure deployment using Flask  
- Real problem-solving with AI automation  

This project reflects a developer mindset focused on **clarity, scalability, and end-user experience**.

---

## 💬 Instructor Acknowledgment

> I would like to express my sincere gratitude to my instructor **Pushkar Sareen** for his continuous guidance and motivation.  
> He has been not only a great teacher but also a true mentor who inspired me to keep improving and building meaningful projects. 🙌  

---
<h3 align="center">👤 Developed by <a href="https://github.com/elvin-babanli">Elvin Babanli</a></h3>
<p align="center">
  <i>Computer Engineering Student · Learning Flask, FastAPI & AI Integration · Passionate about Building Real-World Projects</i>
</p>
