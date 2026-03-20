from playwright.sync_api import sync_playwright
import traceback

def debug_launch():
    print("Attempting to launch Playwright...")
    try:
        with sync_playwright() as p:
            print("Launching chromium...")
            browser = p.chromium.launch(
                headless=False,
                channel="chrome",  # Test with real Chrome
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            print("Chromium launched successfully!")
            page = browser.new_page()
            page.goto("https://www.google.com")
            print(f"Page title: {page.title()}")
            browser.close()
    except Exception as e:
        print(f"Launch failed!")
        traceback.print_exc()

if __name__ == "__main__":
    debug_launch()
