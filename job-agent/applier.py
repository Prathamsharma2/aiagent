from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import os
import re
import json
from cover_letter import CoverLetterGenerator
from resume_router import ResumeRouter

class JobApplier:
    def __init__(self, use_tor=False, cover_letter_gen=None, resume_router=None):
        self.use_tor = use_tor
        self.playwright = None
        self.browser_context = None
        self.page = None
        self.cl_gen = cover_letter_gen or CoverLetterGenerator()
        self.resume_router = resume_router or ResumeRouter()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(script_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.applied_file = os.path.join(self.data_dir, "applied_job_ids.json")
        self.applied_ids = self._load_applied_ids()
        self.session_skipped_ids = set()

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

    def _close_messaging_overlays(self):
        """Minimizes or closes LinkedIn messaging popup bubbles if they obstruct buttons."""
        try:
            close_btns = self.page.locator(
                "button[data-control-name='overlay.close_conversation_window'], "
                "button.msg-overlay-bubble-header__control--close, "
                ".msg-overlay-bubble-header__button[aria-label*='Close']"
            ).all()
            for btn in close_btns:
                if btn.is_visible(timeout=200):
                    btn.click()
        except:
            pass

    def _ensure_all_modals_closed(self):
        """Ensures that any modal, popup, or overlay is completely dismissed before proceeding."""
        self._close_messaging_overlays()

        # Only attempt to dismiss if an actual modal/dialog is visible on screen
        for _ in range(3):
            modal_locator = self.page.locator("div[role='dialog'], .artdeco-modal, .jobs-easy-apply-modal").first
            is_modal = False
            try:
                is_modal = modal_locator.is_visible(timeout=150)
            except:
                pass

            if not is_modal:
                break

            # Click dismiss or discard buttons STRICTLY SCOPED INSIDE THE MODAL (never page-wide!)
            for sel in [
                "div[role='dialog'] button:has-text('Not now')",
                "div[role='dialog'] button.artdeco-modal__dismiss",
                "div[role='dialog'] button[data-test-modal-close-btn]",
                "div[role='dialog'] button[aria-label*='Dismiss']",
                "div[role='dialog'] button:has-text('Discard')",
                "div[role='dialog'] button:has-text('Done')",
                "div[role='dialog'] button:has-text('Close')",
                ".artdeco-modal button.artdeco-modal__dismiss",
                ".artdeco-modal button[data-test-modal-close-btn]",
                ".artdeco-modal button:has-text('Not now')",
                ".artdeco-modal button:has-text('Discard')",
                "[data-test-dialog-primary-btn]"
            ]:
                try:
                    b = self.page.locator(sel).first
                    if b.is_visible(timeout=250):
                        try:
                            b.click(timeout=1500, force=True)
                        except:
                            b.dispatch_event("click")
                        time.sleep(0.4)
                        break
                except:
                    pass

            try:
                self.page.keyboard.press("Escape")
            except:
                pass
            time.sleep(0.3)

    def _dismiss_modal(self):
        """Cleanly dismiss an open Easy Apply modal and confirm discard."""
        try:
            # 1. Close button on dialog (STRICTLY SCOPED INSIDE DIALOG)
            for sel in [
                "div[role='dialog'] button:has-text('Not now')",
                "div[role='dialog'] button.artdeco-modal__dismiss",
                "div[role='dialog'] button[data-test-modal-close-btn]",
                "div[role='dialog'] button[aria-label*='Dismiss']",
                "div[role='dialog'] button:has-text('Done')",
                "div[role='dialog'] button:has-text('Close')",
                ".artdeco-modal button.artdeco-modal__dismiss",
                ".artdeco-modal button[data-test-modal-close-btn]"
            ]:
                try:
                    b = self.page.locator(sel).first
                    if b.is_visible(timeout=300):
                        try:
                            b.click(timeout=1500, force=True)
                        except:
                            b.dispatch_event("click")
                        time.sleep(0.5)
                        break
                except:
                    pass

            try:
                self.page.keyboard.press("Escape")
            except:
                pass
            time.sleep(0.4)

            # 2. Confirm discard if prompt appears
            for discard_sel in [
                "button:has-text('Discard')",
                "[data-test-dialog-primary-btn]",
                "button[data-control-name='discard_application_confirm_btn']",
                ".artdeco-modal__confirm-dialog-btn"
            ]:
                try:
                    b = self.page.locator(discard_sel).first
                    if b.is_visible(timeout=400):
                        try:
                            b.click(timeout=1500, force=True)
                        except:
                            b.dispatch_event("click")
                        time.sleep(0.5)
                        break
                except:
                    pass
        except Exception as e:
            print(f"  ⚠️ Error dismissing modal: {e}")

    def _smart_handle_validation_errors(self, page, user_data):
        """Finds fields that have validation error classes or missing inputs and auto-fills them."""
        try:
            # 1. Elements marked invalid with aria-invalid="true"
            for inp in page.query_selector_all("[aria-invalid='true']"):
                try:
                    tag = inp.evaluate("el => el.tagName.toLowerCase()")
                    t = (inp.get_attribute("type") or "").lower()
                    if tag == "textarea":
                        inp.fill("Yes, I have relevant experience.")
                    elif t in ["text", "number"]:
                        inp.fill("2")
                    elif t in ["radio", "checkbox"]:
                        inp.check(force=True)
                except:
                    pass

            # 2. LinkedIn inline feedback error messages
            error_elements = page.query_selector_all(".artdeco-inline-feedback--error, [data-test-form-builder-error]")
            for err in error_elements:
                try:
                    err_text = (err.inner_text() or "").lower()
                    parent = err.query_selector(
                        "xpath=ancestor::div[contains(@class, 'fb-dash-form-element') or contains(@class, 'jobs-easy-apply-form-section') or contains(@class, 'artdeco-text-input')] | ancestor::fieldset"
                    ) or err.query_selector("xpath=..")
                    if not parent:
                        continue
                    inps = parent.query_selector_all("input, select, textarea")
                    for inp in inps:
                        t = (inp.get_attribute("type") or "").lower()
                        tag = inp.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "textarea":
                            inp.fill("Yes, I have extensive relevant experience.")
                        elif "number" in err_text or "whole number" in err_text or t == "number":
                            inp.fill("2")
                        elif t == "text":
                            inp.fill("2" if any(w in err_text for w in ["number", "digit", "decimal", "range", "between"]) else "Yes")
                        elif t in ["radio", "checkbox"]:
                            inp.check(force=True)
                        elif tag == "select":
                            opts = inp.query_selector_all("option")
                            if len(opts) > 1:
                                inp.select_option(index=1)
                except:
                    pass

            # 3. Any unchecked radio buttons on the page
            all_radios = page.query_selector_all("input[type='radio']")
            seen_radio_names = set()
            for r in all_radios:
                try:
                    r_name = r.get_attribute("name") or ""
                    if r_name and r_name not in seen_radio_names:
                        seen_radio_names.add(r_name)
                        group = [rad for rad in all_radios if rad.get_attribute("name") == r_name]
                        if not any(rad.is_checked() for rad in group):
                            yes_r = next((rad for rad in group if (rad.get_attribute("value") or "").lower() == "yes"), None)
                            if yes_r:
                                yes_r.check(force=True)
                            elif group:
                                group[0].check(force=True)
                except:
                    pass

            # 4. Unselected select dropdowns (India-first priority)
            for sel in page.query_selector_all("select"):
                try:
                    val = sel.input_value()
                    if not val or val == "Select an option" or val == "":
                        opts = sel.query_selector_all("option")
                        selected_in = False
                        for opt in opts:
                            t = opt.inner_text().lower()
                            v = opt.get_attribute("value") or ""
                            if "india" in t or "+91" in t or v.lower() == "in" or v.lower() == "+91":
                                sel.select_option(value=v)
                                selected_in = True
                                break
                        if not selected_in and len(opts) > 1:
                            sel.select_option(index=1)
                except:
                    pass

        except Exception as e:
            print(f"  ⚠️ Error recovery attempt: {e}")

    def _fill_and_submit_modal(self, resume_path, user_data):
        """
        Fills through the multi-step form and clicks submit.
        Includes anti-freeze guard: detects if stuck on the same step and auto-recovers.
        """
        modal_appeared = False
        for _ in range(10):
            for modal_sel in [
                ".jobs-easy-apply-content",
                ".jobs-easy-apply-modal",
                "[data-test-modal]",
                ".artdeco-modal__content",
                ".artdeco-modal",
                "div[role='dialog']",
                "button[aria-label*='Submit']",
                "button:has-text('Submit application')",
                "button[aria-label*='Review']",
                "button:has-text('Review')",
                "button[aria-label*='Continue']",
                "button:has-text('Next')",
                "footer button",
            ]:
                try:
                    if self.page.locator(modal_sel).first.is_visible(timeout=250):
                        modal_appeared = True
                        break
                except:
                    pass
            if modal_appeared:
                break
            time.sleep(0.5)

        if not modal_appeared:
            return False

        previous_dialog_text = ""
        stuck_step_count = 0

        for step in range(15):
            self._close_messaging_overlays()
            time.sleep(0.5)

            # Check if form/modal is still active
            form_active = False
            for active_sel in [
                "button[aria-label*='Submit']",
                "button:has-text('Submit application')",
                "button:has-text('Submit')",
                "button[aria-label*='Review']",
                "button:has-text('Review')",
                "button[aria-label*='Continue']",
                "button[aria-label*='Next']",
                "button:has-text('Next')",
                "button:has-text('Done')",
                ".jobs-easy-apply-content",
                ".jobs-easy-apply-modal",
                "div[role='dialog']",
                "[data-test-modal]",
                ".artdeco-modal",
                "footer button.artdeco-button--primary",
                ".jobs-easy-apply-footer",
                "div.jobs-apply-form"
            ]:
                try:
                    if self.page.locator(active_sel).first.is_visible(timeout=150):
                        form_active = True
                        break
                except:
                    pass

            if not form_active:
                if self._click_if_visible(["button:has-text('Done')", "button[aria-label*='Done']"]):
                    return True
                break

            # Extract current step text for anti-freeze check
            current_text = ""
            for c_sel in [
                ".jobs-easy-apply-content",
                "div[role='dialog']",
                ".jobs-easy-apply-modal",
                "[data-test-modal]",
                ".artdeco-modal",
                ".scaffold-layout__main",
                "form"
            ]:
                try:
                    c = self.page.locator(c_sel).first
                    if c.is_visible(timeout=100):
                        t = c.inner_text()[:400]
                        if t.strip():
                            current_text = t
                            break
                except:
                    pass
            if not current_text:
                try:
                    current_text = self.page.locator("body").inner_text()[:400]
                except:
                    pass

            # Anti-freeze check: did the step advance after clicking Next?
            if current_text and current_text == previous_dialog_text:
                stuck_step_count += 1
                print(f"  ⚠️ Step did not advance (stuck check {stuck_step_count}/6)... applying self-healing...")
                self._smart_handle_validation_errors(self.page, user_data)
                if stuck_step_count >= 6:
                    try:
                        self.page.screenshot(path="job-agent/data/last_stuck_form.png")
                    except:
                        pass
                    print("  🧠 Smart Decision: Form requires complex manual input. Discarding cleanly to keep hunt moving!")
                    return False
            else:
                stuck_step_count = 0
                previous_dialog_text = current_text

            # Fill all fields on current step
            self._fill_all_fields(self.page, user_data, resume_path)
            time.sleep(0.8)

            # 1. Submit application (final step)
            if self._click_if_visible([
                "button[aria-label='Submit application']",
                "footer button:has-text('Submit application')",
                "button:has-text('Submit application')",
                "button[aria-label*='Submit']",
                "button:has-text('Submit')",
            ], timeout=1500):
                print("  📊 Status: APPLIED ✅ - Application submitted successfully!")
                time.sleep(2)

                # Actively dismiss post-submission upsell dialog ("Not now", "Done", etc.)
                for _ in range(8):
                    clicked = self._click_if_visible([
                        "button:has-text('Not now')",
                        "button[aria-label*='Not now']",
                        "button:has-text('Done')",
                        "button[aria-label*='Done']",
                        "button[aria-label*='Dismiss']",
                        "button.artdeco-modal__dismiss",
                        "button[data-test-modal-close-btn]",
                        "button:has-text('Maybe later')",
                        "button:has-text('No thanks')",
                        "button[aria-label*='Close']",
                        "button:has-text('Close')",
                    ], timeout=800)
                    if clicked:
                        print("  ✨ Dismissed post-apply popup ('Not now' / 'Done')!")
                        time.sleep(1)
                        break
                    try:
                        self.page.keyboard.press("Escape")
                    except:
                        pass
                    time.sleep(0.5)

                self._ensure_all_modals_closed()
                return True

            # 2. Review
            elif self._click_if_visible([
                "button[aria-label='Review your application']",
                "footer button:has-text('Review')",
                "button:has-text('Review')",
                "button[aria-label*='Review']",
            ], timeout=1000):
                time.sleep(1)
                continue

            # 3. Next step
            elif self._click_if_visible([
                "button[aria-label='Continue to next step']",
                "footer button:has-text('Next')",
                "button:has-text('Next')",
                "button[aria-label*='Next']",
                "button[aria-label*='Continue']",
                "footer button.artdeco-button--primary",
                ".jobs-easy-apply-footer button.artdeco-button--primary",
            ], timeout=1000):
                time.sleep(1)
                continue

            # 4. Check for 'Done'
            elif self._click_if_visible([
                "button:has-text('Done')",
                "button[aria-label*='Done']"
            ], timeout=600):
                print("  📊 Status: APPLIED ✅ - Application completed ('Done' clicked)!")
                time.sleep(1)
                self._ensure_all_modals_closed()
                return True

            # 5. Fallback: try clicking any primary button
            elif self._click_if_visible([
                "button.artdeco-button--primary",
                "button[type='submit']"
            ], timeout=800):
                time.sleep(1)
                continue

            else:
                # If no button found, attempt error recovery once
                self._smart_handle_validation_errors(self.page, user_data)
                time.sleep(0.5)

        return False

    def _extract_job_details(self):
        """Extracts the company name and full job description from the currently active job pane."""
        company_name = "Company"
        for sel in [
            'a[href*="/company/"]',
            '.job-details-jobs-unified-top-card__company-name a',
            '.jobs-unified-top-card__company-name',
            '.job-card-container__company-name'
        ]:
            try:
                matches = self.page.locator(sel).all()
                for m in matches:
                    t = m.inner_text().strip().split('\n')[0].strip()
                    if t and t.lower() not in ['company', 'linkedin', 'home', 'jobs', 'for business']:
                        company_name = t
                        break
                if company_name != "Company":
                    break
            except:
                pass

        job_desc = ""
        try:
            body_text = self.page.locator('body').inner_text()
            if "About the job" in body_text:
                idx = body_text.index("About the job")
                job_desc = body_text[idx + len("About the job"):].strip()
                for stop_phrase in ["About the company", "Similar jobs", "People also viewed", "How you match", "Show more"]:
                    if stop_phrase in job_desc:
                        job_desc = job_desc.split(stop_phrase)[0].strip()
        except:
            pass

        return company_name, job_desc

    def apply_all_on_search_page(self, search_url, resume_path, user_data=None, max_apply_per_page=15):
        """
        Navigates to search results and iterates through all discovered job cards.
        No unnecessary reloads during iteration.
        Returns the number of successfully submitted applications.
        """
        if not self.browser_context:
            self.start_session()

        print(f"🚀 Navigating to: {search_url}")
        try:
            self.page.goto(search_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(3)
        except Exception as e:
            print(f"📊 Status: FAILED (Navigation Error: {e})")
            return 0

        # Ensure any leftover overlays or messaging windows are closed
        self._ensure_all_modals_closed()

        # Discover all job entries on the page via title links
        links = self.page.locator("a.job-card-list__title--link, a.job-card-container__link, .jobs-search-results-list a[href*='/jobs/view/']").all()
        job_entries = []
        seen_jids = set()

        for l in links:
            try:
                href = l.get_attribute("href") or ""
                m = re.search(r'/jobs/view/(\d+)', href)
                jid = m.group(1) if m else "unknown"
                t = l.inner_text().strip().split('\n')[0].strip()
                if not t:
                    continue
                if jid != "unknown" and jid in seen_jids:
                    continue
                if jid != "unknown":
                    seen_jids.add(jid)

                job_entries.append({
                    "title": t,
                    "jid": jid,
                    "link": l
                })
            except:
                pass

        # Fallback if no specific title links found: discover list cards
        if not job_entries:
            cards = self.page.locator(".jobs-search-results-list li, .scaffold-layout__list-container li, li.jobs-search-results__list-item, div.job-card-container").all()
            for c in cards:
                try:
                    title_elem = c.locator("a[href*='/jobs/view/'], a.job-card-list__title--link, a.job-card-container__link, strong").first
                    if title_elem.is_visible(timeout=100):
                        t = title_elem.inner_text().strip().split('\n')[0].strip()
                        c_jid = c.get_attribute("data-occludable-job-id") or c.get_attribute("data-job-id") or "unknown"
                        if t and (c_jid == "unknown" or c_jid not in seen_jids):
                            if c_jid != "unknown":
                                seen_jids.add(c_jid)
                            job_entries.append({
                                "title": t,
                                "jid": c_jid,
                                "link": title_elem
                            })
                except:
                    pass

        print(f"📋 Discovered {len(job_entries)} jobs on this search page.")

        applied_count = 0

        for idx, entry in enumerate(job_entries):
            if applied_count >= max_apply_per_page:
                print(f"🎯 Target of {max_apply_per_page} applications reached on this page.")
                break

            title = entry.get("title", "Job Role")
            jid = entry.get("jid", "unknown")
            link = entry.get("link")

            try:
                # 1. Quick pre-check before clicking: Already applied or handled?
                if jid != "unknown" and (jid in self.applied_ids or str(jid) in self.session_skipped_ids):
                    print(f"  ⏭️ Job #{idx+1}: '{title}' (ID: {jid}) already applied/handled. Skipping...")
                    continue

                # Ensure no stray popup or overlay is blocking clicks
                self._ensure_all_modals_closed()

                # 2. Click the job card link to open details in the right pane
                opened = False
                if link:
                    try:
                        link.scroll_into_view_if_needed(timeout=1500)
                        time.sleep(0.2)
                        link.click(timeout=2000, force=True)
                        opened = True
                    except Exception:
                        try:
                            link.dispatch_event("click")
                            opened = True
                        except:
                            pass

                if not opened:
                    try:
                        card_loc = self.page.locator(f".jobs-search-results-list text='{title}'").first
                        card_loc.scroll_into_view_if_needed(timeout=1500)
                        card_loc.click(timeout=2000, force=True)
                        opened = True
                    except Exception as e:
                        print(f"  ⏭️ Job #{idx+1}: '{title}' could not be clicked ({e}). Skipping...")
                        continue

                time.sleep(1.6)

                # 3. Extract Job ID from page URL if it was unknown
                if jid == "unknown":
                    m = re.search(r'currentJobId=(\d+)', self.page.url) or re.search(r'/jobs/view/(\d+)', self.page.url)
                    jid = m.group(1) if m else "unknown"

                if jid != "unknown" and (jid in self.applied_ids or str(jid) in self.session_skipped_ids):
                    print(f"  ⏭️ Job #{idx+1}: '{title}' (ID: {jid}) already applied/handled. Skipping...")
                    continue

                # 4. Check if the job details pane says "Unable to load the page" or job removed
                pane_text = ""
                try:
                    pane_loc = self.page.locator(".jobs-details__main-content, .scaffold-layout__detail, body").first
                    pane_text = (pane_loc.inner_text() or "").lower()
                except:
                    pass

                if "unable to load the page" in pane_text or "job posting has been removed" in pane_text:
                    print(f"  ⚠️ Job #{idx+1}: '{title}' (ID: {jid}) has been removed or unable to load. Skipping...")
                    if jid != "unknown":
                        self.session_skipped_ids.add(str(jid))
                    continue

                # 5. Check if already marked 'Applied' on LinkedIn
                applied_btn = self.page.locator('.jobs-details__top-card button:has-text("Applied"), .jobs-s-apply button:has-text("Applied"), button:has-text("Applied")').first
                is_applied_btn = applied_btn.is_visible(timeout=200) if applied_btn else False
                applied_badge = self.page.locator('.jobs-s-apply__applied-badge, .jobs-details__top-card .artdeco-inline-feedback--success').first
                is_applied_badge = applied_badge.is_visible(timeout=200) if applied_badge else False

                applied_text = False
                top_actions = self.page.locator('.jobs-apply-button--top-card, .jobs-s-apply, .jobs-details__top-card').all()
                for ta in top_actions:
                    if 'applied' in ta.inner_text().lower():
                        applied_text = True
                        break

                if is_applied_btn or is_applied_badge or applied_text:
                    print(f"  ⏭️ Job #{idx+1}: '{title}' (ID: {jid}) is ALREADY APPLIED on LinkedIn! Skipping...")
                    if jid != "unknown":
                        self.mark_job_applied(jid, title)
                    continue

                # 6. Locate Easy Apply button in the details pane
                ea_btn = None
                for _ in range(8):
                    for sel in [
                        ".jobs-apply-button--top-card button",
                        ".jobs-details__top-card button",
                        ".jobs-s-apply button",
                        "button.jobs-apply-button",
                        "div.jobs-apply-button--top-card button",
                        ".jobs-details__top-card button:has-text('Easy Apply')",
                        "button[aria-label*='Easy Apply to']",
                        "button:has-text('Easy Apply'):not(#searchFilter_f_AL):not([aria-label*='filter'])"
                    ]:
                        try:
                            loc = self.page.locator(sel).first
                            if loc.is_visible(timeout=250):
                                b_id = loc.get_attribute("id") or ""
                                b_aria = (loc.get_attribute("aria-label") or "").lower()
                                b_txt = (loc.inner_text() or "").lower()
                                if "searchfilter" not in b_id.lower() and "filter" not in b_aria:
                                    if "easy apply" in b_txt or "easy apply" in b_aria:
                                        ea_btn = loc
                                        break
                        except:
                            pass
                    if ea_btn:
                        break
                    time.sleep(0.3)

                if not ea_btn:
                    print(f"  ⏭️ Job #{idx+1}: '{title}' (ID: {jid}) does not have Easy Apply in details pane. Skipping...")
                    continue

                # Extract real company name and job description from the page
                company_name, job_desc = self._extract_job_details()
                print(f"  🏢 Company: {company_name}")

                # Dynamically choose the best resume (Web Development vs Data Science)
                active_resume_path = resume_path
                if self.resume_router:
                    chosen_path, resume_type = self.resume_router.get_resume_for_job(title, job_desc)
                    if chosen_path:
                        active_resume_path = chosen_path
                    print(f"  📄 Target Resume: {resume_type}")

                # Dynamically generate tailored cover letter for this specific job
                job_user_data = dict(user_data) if user_data else {}
                if self.cl_gen:
                    tailored_letter = self.cl_gen.generate(title, company_name, job_desc)
                    job_user_data["cover_letter"] = tailored_letter
                    print(f"  ✍️ Generated tailored cover letter ({len(tailored_letter)} chars)")

                # Click Easy Apply and start filling
                print(f"  ⚡ Job #{idx+1}: '{title}' (ID: {jid}) - Starting Easy Apply...")
                try:
                    ea_btn.scroll_into_view_if_needed(timeout=1000)
                    ea_btn.click(timeout=2000)
                except:
                    ea_btn.click(force=True)
                time.sleep(1)

                submitted = self._fill_and_submit_modal(active_resume_path, job_user_data)
                if submitted:
                    if jid != "unknown":
                        self.mark_job_applied(jid, title)
                    applied_count += 1
                    print(f"  ✅ Applied to '{title}'! Total on this page: {applied_count}")
                    print("  😴 Resting for 4 seconds...")
                    time.sleep(4)
                else:
                    print(f"  ⚠️ Form could not be auto-completed (custom questions). Discarding...")
                    self._dismiss_modal()
                    if jid != "unknown":
                        self.session_skipped_ids.add(str(jid))

                # Always ensure all popups and modals are dismissed before next job
                self._ensure_all_modals_closed()

            except Exception as e:
                print(f"  ⚠️ Error processing job '{title}': {e}. Moving to next...")
                self._ensure_all_modals_closed()
                if jid != "unknown":
                    self.session_skipped_ids.add(str(jid))
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
                    try:
                        locator.click(timeout=1500, force=True)
                    except:
                        locator.dispatch_event("click")
                    return True
            except:
                pass
        return False

    def _fill_all_fields(self, page, user_data, resume_path):
        """
        Intelligently fills every field type in LinkedIn Easy Apply forms:
        - Text & Number fields with contextual heuristics (experience, salary, notice, urls)
        - Radio buttons with smart question understanding (visa/sponsorship -> No, qualifications -> Yes)
        - Checkboxes (terms, agreements, data privacy)
        - Native and custom dropdowns / comboboxes
        - Resume file upload & pre-uploaded resume selection
        """
        if not user_data:
            return
        try:
            # --- 1. Country Code & Phone (India +91) ---
            for sel in [
                "select[id*='countryCode']",
                "select[id*='phoneNumber-country']",
                "select[name*='countryCode']",
                "select[name*='country']",
                "select[id*='country']"
            ]:
                try:
                    if page.is_visible(sel, timeout=100):
                        dropdown = page.locator(sel).first
                        options = dropdown.query_selector_all("option")
                        for opt in options:
                            t = opt.inner_text().lower()
                            val = opt.get_attribute("value") or ""
                            if "india" in t or "+91" in t or val.lower() == "in" or val.lower() == "+91":
                                dropdown.select_option(value=val)
                                break
                except:
                    pass

            for sel in ["input[id*='phoneNumber']", "input[type='tel']", "input[name*='phone']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        # Fill 10-digit Indian mobile number
                        page.fill(sel, user_data.get("phone", "7988105180"))
                    break

            # --- 2. First Name ---
            for sel in ["input[id*='firstName']", "input[name*='firstName']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        name_parts = user_data.get("name", "Pratham Sharma").split()
                        page.fill(sel, name_parts[0])
                    break

            # --- 3. Last Name ---
            for sel in ["input[id*='lastName']", "input[name*='lastName']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        name_parts = user_data.get("name", "Pratham Sharma").split()
                        page.fill(sel, name_parts[-1] if len(name_parts) > 1 else "")
                    break

            # --- 4. Email ---
            for sel in ["input[id*='email']", "input[type='email']", "input[name*='email']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        page.fill(sel, user_data.get("email", "kkrpratham33@gmail.com"))
                    break

            # --- 5. Text / Number Inputs (Years of experience, salary, URLs, etc.) ---
            text_inputs = page.query_selector_all("input[type='text']:not([readonly]), input[type='number']:not([readonly])")
            for inp in text_inputs:
                try:
                    if not inp.is_visible():
                        continue
                    val = inp.input_value() or ""
                    if val.strip():
                        continue  # Already filled

                    # Contextual label analysis
                    label_text = ""
                    inp_id = inp.get_attribute("id") or ""
                    if inp_id:
                        label = page.query_selector(f"label[for='{inp_id}']")
                        if label:
                            label_text = label.inner_text().lower()

                    aria_label = (inp.get_attribute("aria-label") or "").lower()
                    placeholder = (inp.get_attribute("placeholder") or "").lower()
                    inp_name = (inp.get_attribute("name") or "").lower()
                    context = f"{label_text} {aria_label} {placeholder} {inp_name}"

                    is_num = (inp.get_attribute("type") or "").lower() == "number" or "number" in (inp.get_attribute("inputmode") or "")

                    if any(w in context for w in [
                        "year", "experience", "exp", "scale", "rating", "score",
                        "python", "react", "sql", "aws", "node", "fastapi", "django",
                        "java", "javascript", "typescript", "c++", "c#", "golang",
                        "machine learning", "data", "ml", "ai", "docker", "kubernetes",
                        "git", "linux", "cloud", "api", "rest", "backend", "frontend",
                        "html", "css", "vue", "angular", "spark", "hadoop", "pandas"
                    ]):
                        inp.fill("2")
                    elif any(w in context for w in ["salary", "ctc", "lpa", "package", "compensation", "remuneration"]):
                        inp.fill("600000")
                    elif any(w in context for w in ["notice", "period", "days"]):
                        inp.fill("30")
                    elif any(w in context for w in ["linkedin", "profile"]):
                        inp.fill("https://www.linkedin.com/in/prathamsharma2")
                    elif any(w in context for w in ["github", "git"]):
                        inp.fill("https://github.com/Prathamsharma2")
                    elif any(w in context for w in ["website", "portfolio", "url"]):
                        inp.fill("https://github.com/Prathamsharma2")
                    elif any(w in context for w in ["country", "nation", "citizenship"]):
                        inp.fill("India")
                    elif any(w in context for w in ["nationality"]):
                        inp.fill("Indian")
                    elif any(w in context for w in ["state", "province"]):
                        inp.fill("Haryana")
                    elif any(w in context for w in ["city", "town"]):
                        inp.fill("Gurugram")
                    elif any(w in context for w in ["zip", "postal", "pin"]):
                        inp.fill("136118")
                    elif any(w in context for w in ["location", "address"]):
                        inp.fill("Haryana, India")
                    elif any(w in context for w in ["gpa", "percentage", "cgpa", "grade", "marks"]):
                        inp.fill("8.5")
                    elif any(w in context for w in ["yes", "no", "comfortable", "authorized", "commute", "willing", "eligible", "relocate", "hybrid", "onsite"]):
                        inp.fill("Yes")
                    else:
                        inp.fill("2" if is_num else "Yes")
                except:
                    pass

            # --- 6. Textarea (Cover Letter / Additional Questions) ---
            textareas = page.query_selector_all("textarea")
            for ta in textareas:
                try:
                    if ta.is_visible():
                        val = ta.input_value() or ""
                        if not val.strip():
                            ta.fill(user_data.get("cover_letter", "I am excited to apply for this role and look forward to contributing."))
                except:
                    pass

            # --- 7. Radio Buttons (Context-Aware Answering for ALL radio groups) ---
            all_radios = page.query_selector_all("input[type='radio']")
            seen_radio_names = set()
            for r in all_radios:
                try:
                    r_name = r.get_attribute("name") or ""
                    if not r_name or r_name in seen_radio_names:
                        continue
                    seen_radio_names.add(r_name)

                    group = [rad for rad in all_radios if rad.get_attribute("name") == r_name]
                    if any(rad.is_checked() for rad in group):
                        continue

                    parent_text = ""
                    try:
                        p = r.query_selector("xpath=ancestor::div[contains(@class, 'fb-dash-form-element') or contains(@class, 'jobs-easy-apply-form-section')] | ancestor::fieldset")
                        if p:
                            parent_text = p.inner_text().lower()
                    except:
                        pass

                    # Sponsorship / Visa question -> Answer "No"
                    if any(w in parent_text for w in ["sponsor", "visa", "immigration"]):
                        no_radio = next((rad for rad in group if (rad.get_attribute("value") or "").lower() == "no"), None)
                        if no_radio:
                            try:
                                no_radio.check(force=True)
                            except:
                                no_radio.click(force=True)
                            continue

                    # Disability / Veteran / Demographic question -> Answer "Decline" or "No"
                    if any(w in parent_text for w in ["disability", "veteran", "gender", "race", "ethnicity"]):
                        dec_radio = next((rad for rad in group if any(d in (rad.get_attribute("value") or "").lower() for d in ["decline", "wish", "no"])), None)
                        if dec_radio:
                            try:
                                dec_radio.check(force=True)
                            except:
                                dec_radio.click(force=True)
                            continue

                    # Qualification / Willingness / Authorization question -> Answer "Yes"
                    yes_radio = next((rad for rad in group if (rad.get_attribute("value") or "").lower() == "yes"), None)
                    if yes_radio:
                        try:
                            yes_radio.check(force=True)
                        except:
                            yes_radio.click(force=True)
                        continue

                    # Default fallback: check first available radio option
                    if group:
                        try:
                            group[0].check(force=True)
                        except:
                            group[0].click(force=True)
                except:
                    pass

            # --- 8. Checkboxes (Terms, Policies, Consents) ---
            checkboxes = page.query_selector_all("input[type='checkbox']")
            for chk in checkboxes:
                try:
                    if not chk.is_checked():
                        chk_id = chk.get_attribute("id") or ""
                        label = page.query_selector(f"label[for='{chk_id}']")
                        label_text = label.inner_text().lower() if label else ""
                        # Auto-check terms, agreement, or consent checkboxes
                        if any(w in label_text for w in ["agree", "consent", "terms", "policy", "acknowledge", "certify", "confirm"]):
                            try:
                                chk.check(force=True)
                            except:
                                chk.click(force=True)
                except:
                    pass

            # --- 9. Dropdowns & Custom Comboboxes (India-First) ---
            dropdowns = page.query_selector_all("select")
            for dropdown in dropdowns:
                try:
                    if not dropdown.is_visible():
                        continue
                    options = dropdown.query_selector_all("option")

                    # Step A: Check if India or +91 is an option in this dropdown
                    selected = False
                    for opt in options:
                        t = opt.inner_text().lower()
                        val = opt.get_attribute("value") or ""
                        if "india" in t or "+91" in t or val.lower() == "in" or val.lower() == "+91":
                            dropdown.select_option(value=val)
                            selected = True
                            break

                    if selected:
                        continue

                    # Step B: Otherwise pick first valid non-placeholder option
                    for opt in options:
                        val = opt.get_attribute("value") or ""
                        text = opt.inner_text().lower()
                        if val.strip() and "select" not in text and "choose" not in text:
                            dropdown.select_option(value=val)
                            break
                except:
                    pass

            # Custom Artdeco comboboxes (Search India first)
            comboboxes = page.query_selector_all("div[role='combobox'], input[role='combobox']")
            for combo in comboboxes:
                try:
                    if not combo.is_visible():
                        continue
                    val = combo.input_value() if hasattr(combo, 'input_value') else ""
                    if val.strip():
                        continue

                    c_aria = (combo.get_attribute("aria-label") or "").lower()
                    c_ph = (combo.get_attribute("placeholder") or "").lower()
                    c_ctx = f"{c_aria} {c_ph}"

                    # If it's a Country or Location combobox
                    if any(w in c_ctx for w in ["country", "nation", "citizenship"]):
                        combo.click()
                        time.sleep(0.3)
                        if hasattr(combo, 'fill'):
                            combo.fill("India")
                            time.sleep(0.4)
                        in_opt = page.query_selector("div[role='option']:has-text('India'), li[role='option']:has-text('India')")
                        if in_opt:
                            in_opt.click()
                            continue

                    combo.click()
                    time.sleep(0.4)
                    first_opt = page.query_selector("div[role='option'], li[role='option']")
                    if first_opt and first_opt.is_visible():
                        first_opt.click()
                except:
                    pass

            # --- 10. Resume Selection or File Upload ---
            target_resume_name = os.path.basename(resume_path).lower() if resume_path else ""
            is_webd = "web" in target_resume_name
            is_ds = not is_webd

            resume_selected = False
            resume_cards = page.query_selector_all("div.jobs-document-upload__title, [data-test-document-card]")
            if resume_cards:
                # 1. Look for the card specifically matching the target resume
                for card in resume_cards:
                    try:
                        card_text = card.inner_text().lower()
                        title_attr = (card.get_attribute("title") or "").lower()
                        full_info = f"{card_text} {title_attr}"

                        match_target = False
                        if is_webd and "web" in full_info:
                            match_target = True
                        elif is_ds and any(k in full_info for k in ["data", "pratham", "final", "dated"]):
                            match_target = True

                        if match_target:
                            radio = card.query_selector("input[type='radio']")
                            if radio:
                                try:
                                    radio.check(force=True)
                                except:
                                    try:
                                        card.click(force=True)
                                    except:
                                        pass
                                resume_selected = True
                                break
                    except:
                        pass

                # 2. Fallback: select first resume if no specific card matched
                if not resume_selected:
                    for card in resume_cards:
                        try:
                            radio = card.query_selector("input[type='radio']")
                            if radio and not radio.is_checked():
                                radio.check()
                                resume_selected = True
                                break
                        except:
                            pass

            # If file input is present and needs file upload
            file_inputs = page.query_selector_all("input[type='file']")
            for file_input in file_inputs:
                try:
                    if resume_path and os.path.exists(resume_path):
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
