# 🧠 Summerizer — AI-Powered Document Summarizer (Flask · OpenAI · Deploy on Render)

**Summerizer** is a lightweight, production-ready web application that automatically summarizes long documents (PDF, DOCX, TXT) into clean and structured content.  
It was designed to simplify the process of generating summaries, study notes, or presentation materials for students, educators, and professionals dealing with large volumes of text.

---

## 🚀 Key Features

- **Multi-format support:** Upload `.pdf`, `.docx`, or `.txt` files — all processed securely on the backend.  
- **AI-based summarization:** Uses OpenAI API to generate context-aware summaries with adjustable word length and language options.  
- **Export flexibility:** Download your results as `.pdf`, `.docx`, or `.txt`.  
- **Session-based workflow:** Each user session is isolated, enabling multiple independent generations without overlap.  
- **Smart file analysis:** Automatic detection of file size, number of pages, and structure before processing.  
- **Responsive UI:** Simple, clean interface designed for clarity and productivity.  
- **Demo ready for deployment:** Hosted publicly on Render for demonstration purposes.

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-------------|
| **Backend** | Python · Flask · Flask-WTF · Flask-Limiter |
| **AI Integration** | OpenAI API (LLM-based summarization) |
| **File Processing** | PyPDF2 · python-docx · io streams |
| **Security** | CSRF protection · Rate limiting · Secure file upload |
| **Frontend** | HTML5 · CSS3 · Jinja templates |
| **Deployment** | Render (Flask server) |
| **Version Control** | Git + GitHub |

---

## 🧩 System Architecture





- **FileAnalyzer**: Extracts and preprocesses text content from different file formats.  
- **SummarizerService**: Sends structured prompts to OpenAI API and constructs summarized text.  
- **Exporter**: Converts generated summaries into downloadable documents.  

---

## 🧠 Design Philosophy

The goal behind *Summerizer* was not just to “make it work” — but to design it **as a complete, deployable solution** that demonstrates:

- Scalable Flask backend structure.  
- AI integration into a real-world workflow.  
- User-friendly experience with professional design.  
- Secure and maintainable architecture following Flask best practices.

---

## 🌐 Live Demo & Repository

- **Live Demo:** [https://summerizer-ubum.onrender.com](https://summerizer-ubum.onrender.com)  
- **GitHub Repository:** [https://github.com/elvin-babanli/summerizer](https://github.com/elvin-babanli/summerizer)

---

## 🧩 Example Use Case

> “If you have lengthy PDF or Word files — such as research papers, lecture notes, or technical documentation — simply upload them and receive a clean summary in seconds.”

This tool is particularly valuable for:
- Students summarizing study materials.  
- Researchers extracting key points from long articles.  
- Businesses creating internal summaries of large documents.

---

## 🧱 Future Improvements

- [ ] User authentication & history tracking  
- [ ] Multi-document merging and summary comparison  
- [ ] Enhanced multilingual support  
- [ ] Cloud file import (Google Drive, Dropbox)  
- [ ] AI-based presentation slide generation  

---

## 🧾 Summary

**Summerizer** represents the kind of project that solves a real problem using clear logic, clean architecture, and reliable technologies.  
It demonstrates:
- Full-stack development capability  
- Deployment & DevOps understanding  
- API integration & data processing  
- Attention to security, scalability, and usability  

---

### 👤 Developed by [Elvin Babanli](https://github.com/elvin-babanli)
> *Aspiring Software Engineer · AI Integration · Flask & FastAPI Enthusiast · Problem Solver*

---

![Summerizer App Screenshot](https://github.com/elvin-babanli/summerizer/blob/main/assets/Screenshot.png)


