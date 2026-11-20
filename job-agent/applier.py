from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import os

class JobApplier:
    def __init__(self, use_tor=False):
        self.use_tor = use_tor
        self.playwright = None
        self.browser_context = None
        self.page = None

    def start_session(self):
        """Starts a persistent browser session and keeps it open."""
        if self.browser_context:
            return

        if not self.playwright:
            self.playwright = sync_playwright().start()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        session_dir = os.path.join(script_dir, "data/browser_session")
        
        browser_args = ["--disable-blink-features=AutomationControlled"]
        if self.use_tor:
            browser_args.append("--proxy-server=socks5://127.0.0.1:9050")

        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=False,
            args=browser_args,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.browser_context.new_page()
        Stealth().apply_stealth_sync(self.page)
        
        print("💡 TIP: Agar browser mein login nahi hai, toh abhi login kar lein.")
        print("⏳ 2 seconds wait - Abhi login kar sakte hain...")
        time.sleep(2)

    def _screenshot(self, name):
        """Save a debug screenshot."""
        pass

    def apply_to_job(self, job_url, resume_path, user_data=None):
        """Autonomous Easy Apply flow."""
        if not self.browser_context:
            self.start_session()

        print(f"🚀 Navigating to: {job_url}")
        try:
            self.page.goto(job_url, timeout=60000, wait_until="load")
            time.sleep(1)
        except Exception as e:
            print(f"📊 Status: FAILED (Navigation Error: {e})")
            return False

        self._screenshot("after_navigate")

        try:
            # --- Click job cards until we find one with Easy Apply ---
            job_cards = self.page.locator(".job-card-container").all()
            if not job_cards:
                job_cards = self.page.locator("li.jobs-search-results__list-item").all()
            if not job_cards:
                job_cards = self.page.locator("[data-occludable-job-id]").all()

            easy_apply_selectors = [
                ".jobs-apply-button--top-card",
                ".jobs-s-apply button",
                "button.jobs-apply-button",
                "button:has-text('Easy Apply')",
            ]

            applied_clicked = False
            for idx, card in enumerate(job_cards):
                try:
                    # Scroll card into view and click
                    card.scroll_into_view_if_needed()
                    card.click()
                    time.sleep(1)

                    # Look for 'Easy Apply' button
                    for sel in easy_apply_selectors:
                        if self.page.is_visible(sel, timeout=500):
                            self.page.click(sel)
                            print(f"✅ Clicked Easy Apply on job card #{idx+1}!")
                            applied_clicked = True
                            time.sleep(1)
                            break
                    
                    if applied_clicked:
                        break  # We got one! Exit the loop to fill the form.
                    else:
                        print(f"  ⏭️ Job card #{idx+1} already applied or no Easy Apply. Trying next...")
                except Exception as e:
                    print(f"  ⚠️ Failed to click job card #{idx+1}: {e}")
                    continue

            if not applied_clicked:
                self._screenshot("no_easy_apply_found")
                print("📊 Status: SKIPPED (No valid Easy Apply button found on this page)")
                return False

            # --- Handle the Easy Apply MODAL ---
            # Wait for the modal to appear
            modal_appeared = False
            for modal_sel in [
                ".jobs-easy-apply-content",
                ".jobs-easy-apply-modal",
                "[data-test-modal]",
                ".artdeco-modal__content",
            ]:
                try:
                    self.page.wait_for_selector(modal_sel, timeout=2000)
                    print(f"✅ Easy Apply modal detected: {modal_sel}")
                    modal_appeared = True
                    break
                except:
                    pass
            
            if not modal_appeared:
                self._screenshot("modal_not_found")
                print("📊 Status: FAILED (Easy Apply modal did not open)")
                return False

            # --- Navigate through form steps ---
            for step in range(15):
                time.sleep(0.5)
                print(f"  📝 Form step {step + 1}...")
                self._screenshot(f"form_step_{step + 1}")

                # Fill all fields on this page
                self._fill_all_fields(self.page, user_data, resume_path)
                time.sleep(0.5)

                # 1. Submit application (final step)
                if self._click_if_visible([
                    "button[aria-label='Submit application']",
                    "footer button:has-text('Submit application')",
                    "button:has-text('Submit application')",
                ]):
                    print("📊 Status: APPLIED ✅ - Check your email for confirmation!")
                    time.sleep(1)
                    self._screenshot("applied_success")
                    # Close the success popup
                    self._click_if_visible([
                        "button:has-text('Done')",
                        "button[aria-label='Dismiss']",
                        "button.artdeco-modal__dismiss",
                    ])
                    return True

                # 2. Review (second to last step)
                elif self._click_if_visible([
                    "button[aria-label='Review your application']",
                    "footer button:has-text('Review')",
                    "button:has-text('Review')",
                ]):
                    print("  ➡️ Clicked Review")
                    continue

                # 3. Next
                elif self._click_if_visible([
                    "button[aria-label='Continue to next step']",
                    "footer button:has-text('Next')",
                    "button:has-text('Next')",
                ]):
                    print("  ➡️ Clicked Next")
                    continue

                else:
                    # Log what buttons ARE visible for debugging
                    all_buttons = self.page.query_selector_all("button")
                    visible_buttons = []
                    for btn in all_buttons:
                        try:
                            if btn.is_visible():
                                txt = btn.inner_text().strip()
                                if txt:
                                    visible_buttons.append(txt)
                        except:
                            pass
                    print(f"  ⚠️ Visible buttons: {visible_buttons}")
                    print("  ⚠️ No navigation button found. Stopping.")
                    break

            print("📊 Status: FAILED (Could not complete all form steps)")
            return False

        except Exception as e:
            print(f"📊 Status: FAILED ({e})")
            self._screenshot("exception_error")
            return False

    def _click_if_visible(self, selectors, timeout=100):
        """Try a list of selectors; click the first visible one. Returns True if clicked."""
        for sel in selectors:
            try:
                if self.page.is_visible(sel, timeout=timeout):
                    self.page.click(sel)
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
