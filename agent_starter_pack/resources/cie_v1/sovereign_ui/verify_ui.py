from playwright.sync_api import sync_playwright
import sys

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            print("Navigating to http://localhost:5173")
            page.goto("http://localhost:5173")

            # Check for title
            print("Checking for title...")
            page.wait_for_selector("text=Sovereign UI")
            print("Title found.")

            # Check for upload input
            print("Checking for file input...")
            if page.locator("input[type=file]").count() > 0:
                print("File input found.")
            else:
                print("File input missing.")
                sys.exit(1)

            page.screenshot(path="sovereign_ui_screenshot.png")
            print("Screenshot saved to sovereign_ui_screenshot.png")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    verify()
