import os
import sys
import time

from analyzer import ResumeAnalyzer
from searcher import JobSearcher 
from applier import JobApplier
from cover_letter import CoverLetterGenerator

def run_agent():
    # 1. Initialize Components
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resume_path = os.path.join(script_dir, "resume/Datascienceresume.pdf")
    if not os.path.exists(resume_path):
        print(f"❌ Resume not found at {resume_path}.")
        return

    analyzer = ResumeAnalyzer(resume_path)
    searcher = JobSearcher() 
    applier = JobApplier(use_tor=False)

    # 2. Analyze Resume
    print("🔍 Analyzing your resume...")
    analysis = analyzer.analyze()
    print(f"✅ Found skills: {', '.join(analysis['top_skills'])}")
    roles = analysis.get('roles', ['Data Scientist'])
    print(f"🎯 Target Roles: {', '.join(roles)}")

    # Letter Generator
    cl_gen = CoverLetterGenerator("Pratham Sharma", analysis['top_skills'])

    # 3. Search for Jobs
    print("🏹 Opening Hunting Grounds...")
    jobs = searcher.search_jobs_for_roles(roles, location="India", count_per_role=25)
    print(f"📋 Total job targets queued: {len(jobs)}")

    applied_count = 0
    daily_goal = 20

    try:
        # 4. Autonomous Loop
        for job in jobs:
            if applied_count >= daily_goal:
                print("🏆 Daily Goal Reached! Stopping.")
                break

            try:
                # Generate Custom Cover Letter
                cover_letter = cl_gen.generate(job['title'], "Company", job['desc'])

                # ⬇️ APNI REAL INFO YAHAN BHAR DO ⬇️
                user_data = {
                    "name": "Pratham Sharma",
                    "email": "kkrpratham33@gmail.com",
                    "phone": "+91 7988105180",
                    "cover_letter": cover_letter
                }

                print(f"\n⚡ AUTONOMOUS HUNT: Searching {job['title']}...")
                new_applied = applier.apply_all_on_search_page(
                    search_url=job['url'],
                    resume_path=resume_path,
                    user_data=user_data,
                    max_apply_per_page=15
                )
                applied_count += new_applied
                print(f"📈 Total Applied so far: {applied_count}")

            except Exception as e:
                print(f"❌ Critical loop error: {e}. Moving to next.")
    finally:
        print("\n" + "="*50)
        print(f"🏁 Summary: Total jobs successfully applied = {applied_count}")
        if applied_count == 0:
            print("💡 TIP: Browser open hai taaki aap status dekh sakein.")
            try:
                input("👉 Browser band karne ke liye ENTER dabayein: ")
            except (KeyboardInterrupt, EOFError):
                pass
        applier.stop_session()
        print("👋 Session finished.")

if __name__ == "__main__":
    run_agent()
