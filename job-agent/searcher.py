import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

class JobSearcher:
    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # All job roles to target
        self.WEB_DEV_ROLES = [
            "Frontend Developer",
            "Backend Developer",
            "Full Stack Developer",
            "Software Developer",
            "React Developer",
            "Node.js Developer",
            "MERN Stack Developer",
        ]

        self.DATA_SCIENCE_ROLES = [
            "Data Scientist",
            "Data Analyst",
            "Python Developer",
            "Machine Learning Engineer",
            "Generative AI Engineer",
            "AI Engineer",
            "Data Science Engineer",
        ]

    def _build_linkedin_jobs(self, role, location="India", count=10):
        """
        Build LinkedIn Easy Apply job URLs for a given role.
        LinkedIn Easy Apply filter: f_AL=true
        """
        query = urllib.parse.quote(role)
        loc   = urllib.parse.quote(location)
        base  = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={query}&location={loc}&f_AL=true&f_TPR=r86400"
            # f_TPR=r86400 → posted in the last 24 hours
        )
        print(f"  🌐 LinkedIn URL: {base}")

        # Generate job-page entries (each ?start=N loads the next set of results)
        jobs = []
        for page_offset in range(0, count, 25):
            jobs.append({
                "title": role,
                "url": f"{base}&start={page_offset}",
                "desc": f"LinkedIn Easy Apply listing for {role} in {location}",
            })
        return jobs

    def get_all_jobs(self, location="India", jobs_per_role=25):
        """
        Returns a combined list of jobs for ALL web dev and data science roles.
        """
        all_jobs = []

        print("\n📋 Web Development roles:")
        for role in self.WEB_DEV_ROLES:
            print(f"  🔎 Searching: {role}")
            all_jobs.extend(self._build_linkedin_jobs(role, location, jobs_per_role))
            time.sleep(0.2)  # small delay

        print("\n📋 Data Science / AI roles:")
        for role in self.DATA_SCIENCE_ROLES:
            print(f"  🔎 Searching: {role}")
            all_jobs.extend(self._build_linkedin_jobs(role, location, jobs_per_role))
            time.sleep(0.2)

        print(f"\n✅ Total job search targets: {len(all_jobs)}")
        return all_jobs

    # kept for backwards-compatibility
    def search_jobs(self, role, location="India"):
        return self._build_linkedin_jobs(role, location, count=25)
