# 🤖 Autonomous AI Job Application Agent (`aiagent`)

An autonomous Python agent built to automate the end-to-end job hunting and application process. It parses and analyzes your resume, hunts for relevant tech roles (Web Development & Data Science), tailors custom cover letters, and autonomously applies using browser automation (Playwright).

---

## 🚀 Features

- **Resume Analyzer**: Extracts key skills, experience, and domain strengths from PDF resumes (`PyPDF2`).
- **Targeted Job Search**: Searches for relevant openings across key domains:
  - **Web Development**: Frontend, Backend, Full Stack, React, Node.js, MERN Stack.
  - **Data Science**: Data Scientist, Data Analyst, Python Developer, Machine Learning, Generative AI.
- **Dynamic Cover Letter Generator**: Generates customized cover letters tailored to each job description and company.
- **Autonomous Job Applier**: Uses Playwright with stealth configurations (`playwright-stealth`) and persistent browser sessions to navigate and submit applications.
- **Proxy & Tor Integration**: Support for IP rotation and Tor socks proxies for stealthy browsing.
- **Automated Scheduler**: Runs autonomous application hunting rounds at scheduled intervals throughout the day.

---

## 📁 Project Structure

```text
aiagent/
├── job-agent/
│   ├── analyzer.py        # Resume parser & skill extractor
│   ├── app.py             # Main entrypoint & autonomous application loop
│   ├── applier.py         # Playwright automation & form filler
│   ├── cover_letter.py    # Dynamic cover letter generation
│   ├── proxy_manager.py   # Tor and proxy management
│   ├── requirements.txt   # Python dependencies
│   ├── scheduler.py       # Automated daily execution scheduler
│   ├── searcher.py        # Job board scraper & query generator
│   ├── resume/            # Resumes directory
│   └── data/              # Applied jobs logs and session data
├── .gitignore
└── README.md
```

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.9+ installed
- Chromium browser dependencies for Playwright

### 2. Clone the Repository
```bash
git clone https://github.com/Prathamsharma2/aiagent.git
cd aiagent
```

### 3. Install Dependencies
```bash
cd job-agent
pip install -r requirements.txt
playwright install chromium
```

---

## ⚙️ Configuration & Usage

### 1. Add Your Resume
Place your resume PDF inside the `job-agent/resume/` folder (e.g. `Datascienceresume.pdf` or `WebDresume.pdf`).

### 2. Update Personal Details
In `job-agent/app.py`, update your application details:
```python
user_data = {
    "name": "Your Name",
    "email": "your.email@example.com",
    "phone": "+91 9876543210",
    "cover_letter": cover_letter
}
```

### 3. Run the Agent
Run a single application cycle:
```bash
python job-agent/app.py
```

Or start the automated daily scheduler:
```bash
python job-agent/scheduler.py
```

---

## 🛡️ Disclaimer
This tool is built for educational and productivity purposes. Ensure you comply with the terms of service of any job platform or website you interact with.
