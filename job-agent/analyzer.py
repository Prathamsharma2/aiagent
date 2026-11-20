import PyPDF2
import json

class ResumeAnalyzer:
    def __init__(self, resume_path):
        self.resume_path = resume_path
        self.skills = []
        self.experience = ""

    def extract_text(self):
        """Extract text from PDF resume."""
        try:
            with open(self.resume_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            print(f"❌ Error reading PDF: {e}")
            return ""

    def analyze(self):
        """Analyze resume text and extract key information (Mock AI Logic)."""
        text = self.extract_text().lower()
        
        # Simple keyword matching (In production, use an LLM here)
        skill_sets = {
            "python": "Backend Developer",
            "sql": "Data Analyst",
            "machine learning": "Data Scientist",
            "data science": "Data Scientist",
            "node.js": "Node.js Developer",
            "react": "Frontend Developer"
        }
        
        found_skills = [skill for skill in skill_sets.keys() if skill in text]
        detected_roles = list(set([skill_sets[s] for s in found_skills if s in skill_sets]))
        
        if not detected_roles:
            detected_roles = ["Software Engineer"]

        analysis = {
            "top_skills": found_skills,
            "roles": detected_roles,
            "experience_level": "Junior" if "fresher" in text or "0-1" in text else "Professional"
        }
        return analysis

    def match_job(self, job_description, resume_analysis):
        """Calculate match score between resume and job description."""
        jd_lower = job_description.lower()
        score = 0
        matches = []
        
        for skill in resume_analysis["top_skills"]:
            if skill in jd_lower:
                score += 1
                matches.append(skill)
        
        total_possible = len(resume_analysis["top_skills"])
        match_percentage = (score / total_possible * 100) if total_possible > 0 else 0
        
        return {
            "score": match_percentage,
            "matching_skills": matches
        }
