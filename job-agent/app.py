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
    webd_resume = os.path.join(script_dir, "resume/WebDresume.pdf")
    ds_resume = os.path.join(script_dir, "resume/Datascienceresume.pdf")
    default_resume = ds_resume if os.path.exists(ds_resume) else webd_resume

    if not os.path.exists(default_resume):
        print(f"❌ No resume found in {os.path.join(script_dir, 'resume')}.")
        return

    # 2. Analyze Resume
    analyzer = ResumeAnalyzer(default_resume)
    print("🔍 Analyzing your resume...")
    analysis = analyzer.analyze()
    print(f"✅ Found skills: {', '.join(analysis['top_skills'])}")

    # Smart Cover Letter Generator & Applier
    cl_gen = CoverLetterGenerator("Pratham Sharma", analysis['top_skills'])
    searcher = JobSearcher() 
    applier = JobApplier(use_tor=False, cover_letter_gen=cl_gen)

    # 3. Target Roles (Software/Web Development + Data Science/AI)
    all_target_roles = list(dict.fromkeys(
        analysis.get('roles', []) + searcher.DATA_SCIENCE_ROLES + searcher.WEB_DEV_ROLES
    ))
    print(f"🎯 Target Roles ({len(all_target_roles)} total): {', '.join(all_target_roles[:6])}...")

    # 4. Search for Jobs
    print("🏹 Opening Hunting Grounds...")
    jobs = searcher.search_jobs_for_roles(all_target_roles, location="India", count_per_role=25)
    print(f"📋 Total search queries queued: {len(jobs)}")

    applied_count = 0
    daily_goal = 20

    try:
        # 5. Autonomous Loop
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
                    resume_path=default_resume,
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
        print("💡 Browser open hai taaki aap status aur applications dekh sakein.")
        try:
            input("👉 Browser band karne ke liye ENTER dabayein: ")
        except (KeyboardInterrupt, EOFError):
            pass
        applier.stop_session()
        print("👋 Session finished.")

if __name__ == "__main__":
    run_agent()
