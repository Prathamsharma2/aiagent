import os

class ResumeRouter:
    """
    Intelligently routes between Web Development and Data Science resumes
    based on the target role and job description.
    """
    def __init__(self, resume_dir=None):
        if not resume_dir:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            resume_dir = os.path.join(script_dir, "resume")
        self.resume_dir = resume_dir
        self.webd_resume = os.path.join(resume_dir, "WebDresume.pdf")
        ds_named = os.path.join(resume_dir, "Pratham_Sharma_Resume_Final_Dated.pdf")
        self.ds_resume = ds_named if os.path.exists(ds_named) else os.path.join(resume_dir, "Datascienceresume.pdf")

    def get_resume_for_job(self, job_title, job_desc=""):
        """
        Returns (resume_path, resume_label) based on job title and description.
        - Software / Web Dev / Frontend / Backend / Full Stack -> WebDresume.pdf
        - Data Science / ML / AI / GenAI / Data Analyst -> Datascienceresume.pdf
        """
        combined = f"{job_title} {job_desc or ''}".lower()

        # Keywords strongly indicating Web Development & Software Engineering
        web_keywords = [
            "frontend", "front-end", "front end", "backend", "back-end", "back end",
            "full stack", "fullstack", "full-stack", "software engineer", "software developer",
            "sde", "web developer", "react", "node.js", "nodejs", "javascript", "typescript",
            "mern", "html", "css", "angular", "vue", "django", "express", "ui/ux",
            "web development", "java developer", "springboot", "next.js", "nextjs",
            "web application", "developer", "api developer", "golang", "devops"
        ]

        # Keywords strongly indicating Data Science, Machine Learning, and AI
        ds_keywords = [
            "data scientist", "data science", "machine learning", "deep learning",
            "ai engineer", "artificial intelligence", "data analyst", "data analytics",
            "genai", "generative ai", "llm", "nlp", "computer vision", "applied scientist",
            "research scientist", "tableau", "powerbi", "pandas", "pytorch", "tensorflow",
            "scikit", "statistical", "analytics", "data analysis", "big data", "ml engineer"
        ]

        web_score = sum(2 if kw in job_title.lower() else 1 for kw in web_keywords if kw in combined)
        ds_score = sum(2 if kw in job_title.lower() else 1 for kw in ds_keywords if kw in combined)

        # Title-specific tie-breaker weighting
        title_lower = job_title.lower()
        if any(w in title_lower for w in ["software", "frontend", "front end", "backend", "back end", "full stack", "fullstack", "react", "node", "web", "sde", "developer", "java"]):
            web_score += 4
        if any(w in title_lower for w in ["data", "scientist", "ai", "machine learning", "analyst", "genai", "llm", "deep learning"]):
            ds_score += 4

        if web_score > ds_score and os.path.exists(self.webd_resume):
            return self.webd_resume, "Web Development / Software (WebDresume.pdf)"
        elif ds_score > web_score and os.path.exists(self.ds_resume):
            return self.ds_resume, f"Data Science / AI ({os.path.basename(self.ds_resume)})"
        elif any(w in title_lower for w in ["software", "frontend", "front end", "backend", "back end", "full stack", "web", "react", "node", "sde"]) and os.path.exists(self.webd_resume):
            return self.webd_resume, "Web Development / Software (WebDresume.pdf)"
        elif os.path.exists(self.ds_resume):
            return self.ds_resume, f"Data Science / AI ({os.path.basename(self.ds_resume)})"
        elif os.path.exists(self.webd_resume):
            return self.webd_resume, "Web Development / Software (WebDresume.pdf)"
        else:
            return None, "Default Resume"
