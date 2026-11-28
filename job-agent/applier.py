from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import os
import re
import json

class JobApplier:
    def __init__(self, use_tor=False):
        self.use_tor = use_tor
        self.playwright = None
        self.browser_context = None
        self.page = None

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(script_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.applied_file = os.path.join(self.data_dir, "applied_job_ids.json")
        self.applied_ids = self._load_applied_ids()

    def _load_applied_ids(self):
        """Loads previously applied job IDs from local disk."""
        if os.path.exists(self.applied_file):
            try:
                with open(self.applied_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data) if isinstance(data, list) else set(data.keys())
            except Exception as e:
                print(f"⚠️ Error loading applied jobs file: {e}")
        return set()

    def mark_job_applied(self, job_id, job_title=""):
        """Saves a job ID to the persistent applied jobs file so it is never re-attempted."""
        if not job_id or job_id == "unknown":
            return
        self.applied_ids.add(str(job_id))
        try:
            with open(self.applied_file, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.applied_ids)), f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving applied job id: {e}")

    def start_session(self):
        """Starts a persistent browser session and keeps it open."""
        if self.browser_context:
            return

        if not self.playwright:
            self.playwright = sync_playwright().start()
        
        session_dir = os.path.join(self.data_dir, "browser_session")
        
        browser_args = ["--disable-blink-features=AutomationControlled"]
        if self.use_tor:
            browser_args.append("--proxy-server=socks5://127.0.0.1:9050")

        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=False,
            args=browser_args,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.browser_context.pages[0] if self.browser_context.pages else self.browser_context.new_page()
        Stealth().apply_stealth_sync(self.page)
        
        self.ensure_login()

    def ensure_login(self):
        """Verifies if the user is logged into LinkedIn; if not, pauses and waits for user to log in."""
        cookies = self.browser_context.cookies("https://www.linkedin.com")
        has_li_at = any(c.get("name") == "li_at" for c in cookies)
        
        if not has_li_at:
            print("\n" + "="*65)
            print("🔐 LINKEDIN LOGIN REQUIRED")
            print("Aapka browser khul chuka hai. Kripya apna LinkedIn login karein.")
            print("Login karne ke baad terminal mein ENTER dabayein taaki agent continue kar sake.")
            print("="*65 + "\n")
            self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            input("👉 LinkedIn login complete hone ke baad yahan ENTER dabayein: ")
            print("✅ Login completed! Continuing job search...")
        else:
            print("✅ LinkedIn session verified (Logged in).")

    def _screenshot(self, name):
        """Save a debug screenshot."""
        pass

    def _dismiss_modal(self):
        """Cleanly dismiss an open Easy Apply modal and confirm discard."""
        try:
            dismiss_btn = self.page.locator(
                "button[aria-label*='Dismiss'], button[data-test-modal-close-btn], button.artdeco-modal__dismiss"
            ).first
            if dismiss_btn.is_visible(timeout=800):
                dismiss_btn.click()
                time.sleep(1)
                discard_btn = self.page.locator(
                    "button:has-text('Discard'), [data-test-dialog-primary-btn]"
                ).first
                if discard_btn.is_visible(timeout=800):
                    discard_btn.click()
                time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ Error dismissing modal: {e}")

    def _fill_and_submit_modal(self, resume_path, user_data):
        """Fills through the multi-step form and clicks submit."""
        modal_appeared = False
        for _ in range(8):
            for modal_sel in [
                ".jobs-easy-apply-content",
                ".jobs-easy-apply-modal",
                "[data-test-modal]",
                ".artdeco-modal__content",
                "div[role='dialog']",
                "button[aria-label='Continue to next step']",
                "button:has-text('Next')",
                "button:has-text('Review')",
                "button:has-text('Submit application')",
            ]:
                try:
                    if self.page.is_visible(modal_sel, timeout=300):
                        modal_appeared = True
                        break
                except:
                    pass
            if modal_appeared:
                break
            time.sleep(0.5)

        if not modal_appeared:
            return False

        for step in range(12):
            time.sleep(0.5)
            self._fill_all_fields(self.page, user_data, resume_path)
            time.sleep(0.5)

            # 1. Submit application (final step)
            if self._click_if_visible([
                "button[aria-label='Submit application']",
                "footer button:has-text('Submit application')",
                "button:has-text('Submit application')",
            ], timeout=1500):
                print("  📊 Status: APPLIED ✅ - Application submitted successfully!")
                time.sleep(2)
                self._click_if_visible([
                    "button:has-text('Done')",
                    "button[aria-label='Dismiss']",
                    "button.artdeco-modal__dismiss",
                ], timeout=1500)
                return True

            # 2. Review
            elif self._click_if_visible([
                "button[aria-label='Review your application']",
                "footer button:has-text('Review')",
                "button:has-text('Review')",
            ], timeout=1000):
                time.sleep(1)
                continue

            # 3. Next step
            elif self._click_if_visible([
                "button[aria-label='Continue to next step']",
                "footer button:has-text('Next')",
                "button:has-text('Next')",
            ], timeout=1000):
                time.sleep(1)
                continue
            else:
                return False

        return False

    def apply_all_on_search_page(self, search_url, resume_path, user_data=None, max_apply_per_page=10):
        """
        Navigates to search results and iterates through all job cards.
        If a job is already applied, it skips immediately to the next job.
        Returns the number of successfully submitted applications.
        """
        if not self.browser_context:
            self.start_session()

        print(f"🚀 Navigating to: {search_url}")
        try:
            self.page.goto(search_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(4)
        except Exception as e:
            print(f"📊 Status: FAILED (Navigation Error: {e})")
            return 0

        # Discover all job entries on the page
        dismiss_btns = self.page.locator('button[aria-label*="Dismiss "]').all()
        job_titles = []
        if dismiss_btns:
            for b in dismiss_btns:
                aria = b.get_attribute("aria-label") or ""
                t = aria.replace("Dismiss ", "").replace(" job", "").strip()
                if t and t not in job_titles:
                    job_titles.append(t)

        print(f"📋 Discovered {len(job_titles)} jobs on this search page.")

        applied_count = 0

        for idx, title in enumerate(job_titles):
            if applied_count >= max_apply_per_page:
                print(f"🎯 Target of {max_apply_per_page} applications reached on this page.")
                break

            try:
                # Find the clickable title/card on screen
                job_el = self.page.locator(f'text="{title}"').first
                if not job_el.is_visible(timeout=1000):
                    continue

                job_el.scroll_into_view_if_needed()
                job_el.click()
                time.sleep(1.5)

                # Extract Job ID
                m = re.search(r'currentJobId=(\d+)', self.page.url) or re.search(r'/jobs/view/(\d+)', self.page.url)
                jid = m.group(1) if m else "unknown"

                # Check 1: In local applied history?
                if jid != "unknown" and jid in self.applied_ids:
                    print(f"  ⏭️ Job #{idx+1}: '{title}' (ID: {jid}) already in local applied history. Skipping to next...")
                    continue

                # Check 2: Marked 'Applied' on LinkedIn?
                applied_btn = self.page.locator('button:has-text("Applied")').first
                is_applied_btn = applied_btn.is_visible(timeout=300) if applied_btn else False
                applied_badge = self.page.locator('.jobs-s-apply__applied-badge').first
                is_applied_badge = applied_badge.is_visible(timeout=300) if applied_badge else False

                applied_text = False
                top_actions = self.page.locator('.jobs-apply-button--top-card, .jobs-s-apply, .jobs-details__top-card').all()
                for ta in top_actions:
                    if 'applied' in ta.inner_text().lower():
                        applied_text = True
                        break

                if is_applied_btn or is_applied_badge or applied_text:
                    print(f"  ⏭️ Job #{idx+1}: '{title}' (ID: {jid}) is ALREADY APPLIED on LinkedIn! Skipping to next...")
                    self.mark_job_applied(jid, title)
                    continue

                # Check 3: Is Easy Apply button available?
                ea_btn = self.page.locator('button:has-text("Easy Apply"), button[aria-label*="Easy Apply"]').first
                if not ea_btn.is_visible(timeout=800):
                    print(f"  ⏭️ Job #{idx+1}: '{title}' (ID: {jid}) does not have Easy Apply. Skipping to next...")
                    continue

                # Click Easy Apply and start filling
                print(f"  ⚡ Job #{idx+1}: '{title}' (ID: {jid}) - Starting Easy Apply...")
                ea_btn.click()
                time.sleep(1)

                submitted = self._fill_and_submit_modal(resume_path, user_data)
                if submitted:
                    self.mark_job_applied(jid, title)
                    applied_count += 1
                    print(f"  ✅ Applied to '{title}'! Total on this page: {applied_count}")
                    print("  😴 Resting for 4 seconds...")
                    time.sleep(4)
                else:
                    print(f"  ⚠️ Form could not be auto-completed (custom questions). Discarding and moving to next...")
                    self._dismiss_modal()
                    self.mark_job_applied(jid, title)
                    time.sleep(1)

            except Exception as e:
                print(f"  ⚠️ Error processing job '{title}': {e}. Moving to next...")
                self._dismiss_modal()
                continue

        return applied_count

    # Backwards compatibility
    def apply_to_job(self, job_url, resume_path, user_data=None):
        return self.apply_all_on_search_page(job_url, resume_path, user_data, max_apply_per_page=1) > 0

    def _click_if_visible(self, selectors, timeout=1000):
        """Try a list of selectors; click the first visible one. Returns True if clicked."""
        for sel in selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.is_visible(timeout=timeout):
                    locator.click()
                    return True
            except:
                pass
        return False

    def _fill_all_fields(self, page, user_data, resume_path):
        """Fill every field type LinkedIn might ask in Easy Apply forms."""
        if not user_data:
            return
        try:
            # --- Phone ---
            for sel in ["input[id*='phoneNumber']", "input[type='tel']", "input[name*='phone']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        page.fill(sel, user_data.get("phone", ""))
                    break

            # --- First Name ---
            for sel in ["input[id*='firstName']", "input[name*='firstName']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        name_parts = user_data.get("name", "").split()
                        page.fill(sel, name_parts[0] if name_parts else "")
                    break

            # --- Last Name ---
            for sel in ["input[id*='lastName']", "input[name*='lastName']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        name_parts = user_data.get("name", "").split()
                        page.fill(sel, name_parts[-1] if len(name_parts) > 1 else "")
                    break

            # --- Email ---
            for sel in ["input[id*='email']", "input[type='email']", "input[name*='email']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        page.fill(sel, user_data.get("email", ""))
                    break

            # --- Text/Number inputs (e.g. years of experience, salary) ---
            text_inputs = page.query_selector_all("input[type='text']:not([readonly]), input[type='number']:not([readonly])")
            for inp in text_inputs:
                try:
                    if not inp.is_visible():
                        continue
                    val = inp.input_value() or ""
                    if val.strip():
                        continue  # Already filled
                    # Get label text for context
                    label_text = ""
                    inp_id = inp.get_attribute("id") or ""
                    if inp_id:
                        label = page.query_selector(f"label[for='{inp_id}']")
                        if label:
                            label_text = label.inner_text().lower()
                    if any(w in label_text for w in ["year", "experience", "exp"]):
                        inp.fill("2")
                    elif any(w in label_text for w in ["salary", "ctc", "lpa", "package"]):
                        inp.fill("500000")
                    elif any(w in label_text for w in ["notice", "period"]):
                        inp.fill("30")
                    else:
                        inp.fill("2")
                except:
                    pass

            # --- Textarea (cover letter / additional info) ---
            textareas = page.query_selector_all("textarea")
            for ta in textareas:
                try:
                    if ta.is_visible():
                        val = ta.input_value() or ""
                        if not val.strip():
                            ta.fill(user_data.get("cover_letter", "I am excited to apply for this role."))
                except:
                    pass

            # --- Radio buttons: select "Yes" option or first option ---
            radio_groups = page.query_selector_all("fieldset")
            for group in radio_groups:
                try:
                    # Try to find a "Yes" radio
                    yes_radio = group.query_selector("input[type='radio'][value='Yes'], label:has-text('Yes') input[type='radio']")
                    if yes_radio and yes_radio.is_visible():
                        if not yes_radio.is_checked():
                            yes_radio.check()
                        continue
                    # Otherwise check first radio in group
                    radios = group.query_selector_all("input[type='radio']")
                    for radio in radios:
                        if radio.is_visible() and not radio.is_checked():
                            radio.check()
                            break
                except:
                    pass

            # --- Select dropdowns ---
            dropdowns = page.query_selector_all("select")
            for dropdown in dropdowns:
                try:
                    if not dropdown.is_visible():
                        continue
                    options = dropdown.query_selector_all("option")
                    for opt in options:
                        val = opt.get_attribute("value") or ""
                        text = opt.inner_text().lower()
                        if val.strip() and "select" not in text and "choose" not in text:
                            dropdown.select_option(value=val)
                            break
                except:
                    pass

            # --- File upload (resume) ---
            file_inputs = page.query_selector_all("input[type='file']")
            for file_input in file_inputs:
                try:
                    file_input.set_input_files(resume_path)
                    time.sleep(1)
                except:
                    pass

        except Exception as e:
            print(f"  ⚠️ Field fill error: {e}")

    def stop_session(self):
        try:
            if self.browser_context:
                self.browser_context.close()
        except:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except:
            pass
