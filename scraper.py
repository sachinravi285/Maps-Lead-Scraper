import os
import re
import time
import random
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ================= CONFIG =================

SEARCH_QUERY = "software development in erode"
MAX_RESULTS = 40
OUTPUT_FILE = "maps_leads.xlsx"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# ==========================================


def extract_website_data(url):
    emails = set()
    socials = set()

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        found = re.findall(EMAIL_REGEX, response.text)
        emails.update(found)

        for mail in soup.select("a[href^=mailto]"):
            emails.add(mail.get("href").replace("mailto:", "").strip())

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(platform in href for platform in [
                "facebook.com",
                "instagram.com",
                "linkedin.com",
                "twitter.com",
                "youtube.com"
            ]):
                socials.add(href)

    except Exception:
        pass

    return ", ".join(emails), ", ".join(socials)


def auto_scroll(page):
    try:
        page.wait_for_selector('div[role="feed"]', timeout=10000)
    except:
        print("Results panel not found.")
        return

    results_panel = page.locator('div[role="feed"]')
    last_count = 0

    for _ in range(50):
        results_panel.evaluate("(el) => el.scrollTo(0, el.scrollHeight)")
        time.sleep(2)

        cards = page.locator('div[role="article"]')
        current_count = cards.count()

        if current_count >= MAX_RESULTS:
            break

        if current_count == last_count:
            break

        last_count = current_count


def extract_business_links(page):
    links = set()
    cards = page.locator('div[role="article"] a[href*="/place/"]')
    count = cards.count()

    for i in range(count):
        href = cards.nth(i).get_attribute("href")
        if href:
            links.add(href.split("&")[0])

    return list(links)




def extract_business_details(page):
    data = {
        "Business Name": "",
        "Address": "",
        "Phone Number": "",
        "Website URL": "",
        "Email Address": "",
        "businessType": SEARCH_QUERY,
        "Social Media Links": ""
    }

    try:
        page.wait_for_selector("h1", timeout=5000)
        data["Business Name"] = page.locator("h1").first.inner_text()

        try:
            data["Address"] = page.locator('button[data-item-id="address"]').inner_text()
        except:
            pass

        try:
            data["Phone Number"] = page.locator('button[data-item-id^="phone"]').inner_text()
        except:
            pass

        try:
            website = page.locator('a[data-item-id="authority"]').get_attribute("href")
            data["Website URL"] = website
        except:
            pass


        if data["Website URL"]:
            emails, socials = extract_website_data(data["Website URL"])
            data["Email Address"] = emails
            data["Social Media Links"] = socials

    except Exception:
        pass

    return data


def run_scraper():
    print(f"Scraper started for query: {SEARCH_QUERY}")
    leads = []

    with sync_playwright() as p:
        is_server = os.environ.get("RAILWAY_ENVIRONMENT_ID") or os.environ.get("RENDER") or os.environ.get("VERCEL")
        
        print(f"Launching playwright (headless={'True' if is_server else 'False'})...")
        
        browser = p.chromium.launch(
            headless=True if is_server else False,
            args=["--no-sandbox", "--disable-setuid-sandbox"] if is_server else []
        )



        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        search_url = f"https://www.google.com/maps/search/{SEARCH_QUERY.replace(' ', '+')}"
        page.goto(search_url, timeout=60000)

        time.sleep(5)
        auto_scroll(page)

        business_links = extract_business_links(page)

        for link in business_links:
            if len(leads) >= MAX_RESULTS:
                break
                
            try:
                page.goto(link, timeout=60000)
                time.sleep(random.uniform(2, 4))

                details = extract_business_details(page)

                # Skip filter for more results, but check for name at least
                if not details["Business Name"]:
                    continue

                leads.append(details)
                yield {"type": "lead", "data": details}

            except Exception:
                continue

        browser.close()

    df = pd.DataFrame(leads)
    df.to_excel(OUTPUT_FILE, index=False)

    yield {"type": "done", "file": OUTPUT_FILE, "count": len(leads)}
