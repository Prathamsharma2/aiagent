import os

class CoverLetterGenerator:
    def __init__(self, user_name, skills):
        self.user_name = user_name
        self.skills = skills

    def generate(self, job_title, company_name, job_desc):
        """Generates a tailored cover letter."""
        # Simple Template (AI-Ready)
        letter = f"""
Hi Hiring Manager at {company_name},

I am excited to apply for the {job_title} role. 

With my experience in {', '.join(self.skills)}, I am confident I can contribute effectively to your team. 

In my previous projects, I have worked extensively on similar challenges mentioned in your job description:
"{job_desc[:100]}..."

Looking forward to discussing how my skills align with your needs.

Best regards,
{self.user_name}
"""
        return letter
