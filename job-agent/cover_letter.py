import os
import re
import json

class CoverLetterGenerator:
    def __init__(self, user_name="Pratham Sharma", skills=None, phone="+91 7988105180", email="kkrpratham33@gmail.com"):
        self.user_name = user_name
        self.skills = skills or ["Python", "Machine Learning", "Data Science", "FastAPI", "SQL"]
        self.phone = phone
        self.email = email
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def _generate_with_gemini(self, job_title, company_name, job_desc):
        """Attempts to generate a bespoke cover letter using Gemini API if key is present."""
        if not self.api_key:
            return None
        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            prompt = (
                f"You are writing a professional, concise, punchy 3-paragraph cover letter for {self.user_name} "
                f"(Contact: {self.phone}, {self.email}) applying for the role '{job_title}' at '{company_name}'.\n"
                f"Candidate Background: Full-Stack & AI/ML Engineer with experience in GenAI (LangChain, Pinecone, FastAPI), "
                f"Machine Learning (PyTorch, TensorFlow, Scikit-learn), Data Science (Pandas, EDA, SQL), and production backend systems.\n"
                f"Job Description:\n{job_desc[:1200]}\n\n"
                f"Write a polished, tailored cover letter (around 160-200 words) specifically highlighting how the candidate's "
                f"real project achievements align with the job requirements. Keep it confident, direct, and professional without fluff."
            )
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception as e:
            print(f"  ℹ️ Gemini API call skipped ({e}), using smart semantic generator.")
        return None

    def generate(self, job_title, company_name, job_desc):
        """
        Generates an intelligent, tailored cover letter by analyzing the actual job description,
        matching relevant technical skills and project highlights.
        """
        # Try Gemini if API key is provided
        ai_letter = self._generate_with_gemini(job_title, company_name, job_desc)
        if ai_letter:
            return ai_letter

        # Smart Semantic Generation
        company = company_name.strip() if company_name and company_name.lower() not in ["company", "linkedin"] else "your team"
        title = job_title.strip() if job_title else "this role"
        jd_text = (title + " " + (job_desc or "")).lower()

        # 1. Detect Core Pillars from the JD
        is_genai = any(k in jd_text for k in ["genai", "generative ai", "llm", "llms", "langchain", "rag", "nlp", "prompt", "transformer", "fine-tuning", "vector"])
        is_ml = any(k in jd_text for k in ["machine learning", "predictive", "deep learning", "pytorch", "tensorflow", "scikit", "model training", "computer vision", "opencv"])
        is_data = any(k in jd_text for k in ["data scientist", "data analyst", "analytics", "eda", "tableau", "powerbi", "sql", "insights", "statistics"])
        is_backend = any(k in jd_text for k in ["backend", "api", "fastapi", "django", "flask", "node", "microservice", "database", "rest", "kafka"])

        # 2. Select the Most Relevant Real-World Achievements
        highlights = []
        if is_genai:
            highlights.append("architecting GenAI automation pipelines using LangChain, Pinecone, and FastAPI, as well as fine-tuning LLMs on specialized domain datasets")
        if is_ml:
            highlights.append("building predictive and classification models using Python (PyTorch, TensorFlow, Scikit-learn, Pandas) from data preprocessing to production integration")
        if is_data:
            highlights.append("conducting in-depth exploratory data analysis (EDA), statistical modeling, and transforming complex data into actionable business intelligence")
        if is_backend and not is_genai:
            highlights.append("designing scalable backend architectures and RESTful microservices using Python (FastAPI/Django) and high-performance database design")

        if not highlights:
            highlights.append("building scalable data-driven applications, designing automated ML workflows, and deploying robust software solutions using Python and modern engineering frameworks")

        tech_focus = " and ".join(highlights[:2])

        # 3. Match Specific Technologies Mentioned in JD
        tracked_tech = [
            "Python", "SQL", "PyTorch", "TensorFlow", "FastAPI", "Django", "LangChain",
            "Scikit-learn", "Pandas", "NumPy", "Docker", "PostgreSQL", "NLP", "React", "Kafka"
        ]
        matched = [tech for tech in tracked_tech if tech.lower() in jd_text]
        if not matched:
            matched = ["Python", "Machine Learning", "Data Science", "FastAPI", "SQL"]

        skills_summary = ", ".join(matched[:5])

        greeting = f"Dear Hiring Manager at {company}," if company != "your team" else "Dear Hiring Manager,"
        org_ref = company if company != "your team" else "your organization"

        letter = f"""{greeting}

I am writing to express my strong enthusiasm for the {title} position at {org_ref}. With a solid background in Computer Science and practical experience building production-ready AI and software solutions, I am eager to contribute to {org_ref}'s high-impact engineering initiatives.

Throughout my experience, my focus has been on {tech_focus}. During my work with Quikry and SkyBrisk, I led end-to-end development of AI-driven systems—from fine-tuning machine learning models on real-world datasets to optimizing predictive accuracy and building reliable backend services. Furthermore, my hands-on proficiency with {skills_summary} enables me to quickly ramp up and solve complex, data-intensive challenges.

What excites me most about {org_ref} is your commitment to building scalable, technology-driven solutions. I pride myself on writing clean, maintainable code, adapting swiftly to modern tech stacks, and delivering measurable performance improvements.

I would welcome the opportunity to discuss how my technical skills and problem-solving mindset align with your team's goals for the {title} role. Thank you for your time and consideration.

Sincerely,
{self.user_name}
{self.phone} | {self.email}"""

        return letter.strip()
