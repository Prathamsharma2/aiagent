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
    try:
        # 4. Autonomous Loop
        for job in jobs:
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

                # 5. AUTO-APPLY (No manual intervention)
                print(f"\n⚡ AUTONOMOUS ATTEMPT: {job['title']}")
                success = applier.apply_to_job(job['url'], resume_path, user_data=user_data)
                
                if success:
                    applied_count += 1
                    print(f"📈 Total Applied so far: {applied_count}")
                
                # Short rest to look human
                print("😴 Resting for 5 seconds...")
                time.sleep(5)

                if applied_count >= 20:
                    print("🏆 Daily Goal Reached! Stopping.")
                    break

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
