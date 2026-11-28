from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import os
import re
import json
from cover_letter import CoverLetterGenerator

class JobApplier:
    def __init__(self, use_tor=False, cover_letter_gen=None):
        self.use_tor = use_tor
        self.playwright = None
        self.browser_context = None
        self.page = None
        self.cl_gen = cover_letter_gen or CoverLetterGenerator()

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

    def _dismiss_modal(self):
        """Cleanly dismiss an open Easy Apply modal and confirm discard."""
        try:
            for dismiss_sel in [
                "button[aria-label*='Dismiss']",
                "button[data-test-modal-close-btn]",
                "button.artdeco-modal__dismiss",
                "button[aria-label*='Close']"
            ]:
                btn = self.page.locator(dismiss_sel).first
                if btn.is_visible(timeout=500):
                    btn.click()
                    time.sleep(1)
                    break

            # Confirm discard if prompt appears
            for discard_sel in [
                "button:has-text('Discard')",
                "[data-test-dialog-primary-btn]",
                "button[data-control-name='discard_application_confirm_btn']",
                ".artdeco-modal__confirm-dialog-btn"
            ]:
                btn = self.page.locator(discard_sel).first
                if btn.is_visible(timeout=500):
                    btn.click()
                    time.sleep(1)
                    break
        except Exception as e:
            print(f"  ⚠️ Error dismissing modal: {e}")

    def _smart_handle_validation_errors(self, page, user_data):
        """Finds fields that have validation error classes or missing inputs and auto-fills them."""
        try:
            error_elements = page.query_selector_all(".artdeco-inline-feedback--error, [data-test-form-builder-error]")
            for err in error_elements:
                parent = err.query_selector("xpath=..")
                if not parent:
                    continue
                inps = parent.query_selector_all("input, select, textarea")
                for inp in inps:
                    t = inp.get_attribute("type") or ""
                    if t in ["text", "number"]:
                        inp.fill("2")
                    elif t == "radio":
                        inp.check()
                    elif inp.evaluate("el => el.tagName.toLowerCase()") == "select":
                        opts = inp.query_selector_all("option")
                        if len(opts) > 1:
                            inp.select_option(index=1)
        except Exception as e:
            print(f"  ⚠️ Error recovery attempt: {e}")

    def _fill_and_submit_modal(self, resume_path, user_data):
        """
        Fills through the multi-step form and clicks submit.
        Includes anti-freeze guard: detects if stuck on the same step and auto-recovers.
        """
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

        previous_dialog_text = ""
        stuck_step_count = 0

        for step in range(15):
            self._close_messaging_overlays()
            time.sleep(0.5)

            # Check if modal is still active
            dialog = self.page.locator("div[role='dialog'], .jobs-easy-apply-modal").first
            if not dialog.is_visible():
                break

            current_text = ""
            try:
                current_text = dialog.inner_text()[:300]
            except:
                pass

            # Anti-freeze check: did the step advance after clicking Next?
            if current_text and current_text == previous_dialog_text:
                stuck_step_count += 1
                print(f"  ⚠️ Step did not advance (stuck check {stuck_step_count}/3)... applying self-healing...")
                self._smart_handle_validation_errors(self.page, user_data)
                if stuck_step_count >= 3:
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
                if self._click_if_visible(["button:has-text('Done')"]):
                    return True
                return False

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

                # Extract real company name and job description from the page
                company_name, job_desc = self._extract_job_details()
                print(f"  🏢 Company: {company_name}")

                # Dynamically generate tailored cover letter for this specific job
                job_user_data = dict(user_data) if user_data else {}
                if self.cl_gen:
                    tailored_letter = self.cl_gen.generate(title, company_name, job_desc)
                    job_user_data["cover_letter"] = tailored_letter
                    print(f"  ✍️ Generated tailored cover letter ({len(tailored_letter)} chars)")

                # Click Easy Apply and start filling
                print(f"  ⚡ Job #{idx+1}: '{title}' (ID: {jid}) - Starting Easy Apply...")
                ea_btn.click()
                time.sleep(1)

                submitted = self._fill_and_submit_modal(resume_path, job_user_data)
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
            # --- 1. Phone ---
            for sel in ["input[id*='phoneNumber']", "input[type='tel']", "input[name*='phone']"]:
                if page.is_visible(sel, timeout=50):
                    current = page.input_value(sel)
                    if not current.strip():
                        page.fill(sel, user_data.get("phone", "+91 7988105180"))
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
                    context = f"{label_text} {aria_label} {placeholder}"

                    if any(w in context for w in ["year", "experience", "exp"]):
                        inp.fill("2")
                    elif any(w in context for w in ["salary", "ctc", "lpa", "package", "compensation"]):
                        inp.fill("600000")
                    elif any(w in context for w in ["notice", "period"]):
                        inp.fill("30")
                    elif any(w in context for w in ["linkedin", "profile"]):
                        inp.fill("https://www.linkedin.com/in/prathamsharma2")
                    elif any(w in context for w in ["github", "git"]):
                        inp.fill("https://github.com/Prathamsharma2")
                    elif any(w in context for w in ["website", "portfolio", "url"]):
                        inp.fill("https://github.com/Prathamsharma2")
                    elif any(w in context for w in ["city", "location", "address"]):
                        inp.fill("Haryana, India")
                    elif any(w in context for w in ["gpa", "percentage", "cgpa"]):
                        inp.fill("8.5")
                    else:
                        inp.fill("2")
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

            # --- 7. Radio Buttons (Context-Aware Answering) ---
            radio_groups = page.query_selector_all("fieldset, div[role='radiogroup']")
            for group in radio_groups:
                try:
                    # Check if already answered in this group
                    checked = group.query_selector("input[type='radio']:checked")
                    if checked:
                        continue

                    group_text = group.inner_text().lower()

                    # Sponsorship / Visa question -> Answer "No"
                    if any(w in group_text for w in ["sponsor", "visa", "immigration"]):
                        no_radio = group.query_selector(
                            "input[type='radio'][value='No'], label:has-text('No') input[type='radio'], input[type='radio'][aria-label*='No']"
                        )
                        if no_radio and no_radio.is_visible():
                            no_radio.check()
                            continue

                    # Disability / Veteran / Demographic question -> Answer "Decline" or "No"
                    if any(w in group_text for w in ["disability", "veteran", "gender", "race", "ethnicity"]):
                        decline_radio = group.query_selector(
                            "input[type='radio'][value*='Decline'], label:has-text('Decline') input[type='radio'], "
                            "label:has-text('wish') input[type='radio'], label:has-text('No') input[type='radio']"
                        )
                        if decline_radio and decline_radio.is_visible():
                            decline_radio.check()
                            continue

                    # Qualification / Willingness question -> Answer "Yes"
                    yes_radio = group.query_selector(
                        "input[type='radio'][value='Yes'], label:has-text('Yes') input[type='radio'], input[type='radio'][aria-label*='Yes']"
                    )
                    if yes_radio and yes_radio.is_visible():
                        yes_radio.check()
                        continue

                    # Default fallback: check first available radio option
                    radios = group.query_selector_all("input[type='radio']")
                    for r in radios:
                        if r.is_visible():
                            r.check()
                            break
                except:
                    pass

            # --- 8. Checkboxes (Terms, Policies, Consents) ---
            checkboxes = page.query_selector_all("input[type='checkbox']")
            for chk in checkboxes:
                try:
                    if chk.is_visible() and not chk.is_checked():
                        chk_id = chk.get_attribute("id") or ""
                        label = page.query_selector(f"label[for='{chk_id}']")
                        label_text = label.inner_text().lower() if label else ""
                        # Auto-check terms, agreement, or consent checkboxes
                        if any(w in label_text for w in ["agree", "consent", "terms", "policy", "acknowledge", "certify"]):
                            chk.check()
                except:
                    pass

            # --- 9. Dropdowns & Custom Comboboxes ---
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

            # Custom Artdeco comboboxes
            comboboxes = page.query_selector_all("div[role='combobox'], input[role='combobox']")
            for combo in comboboxes:
                try:
                    if combo.is_visible():
                        val = combo.input_value() if hasattr(combo, 'input_value') else ""
                        if not val.strip():
                            combo.click()
                            time.sleep(0.4)
                            first_opt = page.query_selector("div[role='option'], li[role='option']")
                            if first_opt and first_opt.is_visible():
                                first_opt.click()
                except:
                    pass

            # --- 10. Resume Selection or File Upload ---
            # If previous resumes are shown as radio cards, select the first one
            resume_cards = page.query_selector_all("div.jobs-document-upload__title, [data-test-document-card]")
            if resume_cards:
                for card in resume_cards:
                    try:
                        radio = card.query_selector("input[type='radio']")
                        if radio and not radio.is_checked():
                            radio.check()
                            break
                    except:
                        pass

            # If file input is present and file upload is required
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
