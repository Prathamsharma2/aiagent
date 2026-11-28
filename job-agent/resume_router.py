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
        self.ds_resume = os.path.join(resume_dir, "Datascienceresume.pdf")

    def get_resume_for_job(self, job_title, job_desc=""):
        """
        Returns (resume_path, resume_label) based on job title and description.
        - Software / Web Dev / Frontend / Backend / Full Stack -> WebDresume.pdf
        - Data Science / ML / AI / GenAI / Data Analyst -> Datascienceresume.pdf
        """
        combined = f"{job_title} {job_desc or ''}".lower()

        # Keywords strongly indicating Web Development & Software Engineering
        web_keywords = [
            "frontend", "front-end", "backend", "back-end", "full stack", "fullstack",
            "software engineer", "software developer", "sde", "web developer", "react",
            "node.js", "nodejs", "javascript", "typescript", "mern", "html", "css",
            "angular", "vue", "django", "express", "ui/ux", "web development",
            "java developer", "springboot", "next.js", "nextjs", "web application"
        ]

        # Keywords strongly indicating Data Science, Machine Learning, and AI
        ds_keywords = [
            "data scientist", "data science", "machine learning", "deep learning",
            "ai engineer", "artificial intelligence", "data analyst", "genai",
            "generative ai", "llm", "nlp", "computer vision", "applied scientist",
            "research scientist", "tableau", "powerbi", "pandas", "pytorch", "tensorflow",
            "scikit", "statistical", "analytics", "data analysis", "big data"
        ]

        web_score = sum(2 if kw in job_title.lower() else 1 for kw in web_keywords if kw in combined)
        ds_score = sum(2 if kw in job_title.lower() else 1 for kw in ds_keywords if kw in combined)

        # Title-specific tie-breaker weighting
        title_lower = job_title.lower()
        if any(w in title_lower for w in ["software", "frontend", "backend", "full stack", "react", "node", "web", "sde"]):
            web_score += 3
        if any(w in title_lower for w in ["data", "scientist", "ai", "machine learning", "analyst", "genai", "llm"]):
            ds_score += 3

        if web_score > ds_score and os.path.exists(self.webd_resume):
            return self.webd_resume, "Web Development / Software (WebDresume.pdf)"
        elif os.path.exists(self.ds_resume):
            return self.ds_resume, "Data Science / AI (Datascienceresume.pdf)"
        elif os.path.exists(self.webd_resume):
            return self.webd_resume, "Web Development / Software (WebDresume.pdf)"
        else:
            return None, "Default Resume"
