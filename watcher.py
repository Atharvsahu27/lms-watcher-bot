import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from twilio.rest import Client


LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

USERNAME = os.getenv("LMS_USER")
PASSWORD = os.getenv("LMS_PASS")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
MY_PHONE = os.getenv("MY_PHONE")

DATA_FILE = "seen.json"


def send_whatsapp(msg):

    client = Client(TWILIO_SID, TWILIO_TOKEN)

    client.messages.create(
        body=msg,
        from_="whatsapp:+14155238886",
        to=MY_PHONE
    )


def load_seen():

    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {"seen": []}


def save_seen(data):

    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def get_due_date(page):

    try:

        due_div = page.locator(".description-inner div:has-text('Due')")

        if due_div.count() > 0:

            due_text = due_div.first.inner_text()

            date_str = due_text.replace("Due:", "").strip()

            return datetime.strptime(
                date_str,
                "%A, %d %B %Y, %I:%M %p"
            )

    except:
        return None


def get_description(page):

    try:

        desc = page.locator(".activity-description")

        if desc.count() > 0:

            return desc.first.inner_text().strip()

    except:
        return ""

    return ""


def scan_courses(page, seen):

    activities = []

    course_links = page.locator('a[href*="/course/view.php"]').all()

    for c in course_links:

        url = c.get_attribute("href")

        if not url:
            continue

        print("Opening course:", url)

        page.goto(url)

        page.wait_for_load_state("networkidle")

        acts = page.locator('a[href*="mod/"]').all()

        for a in acts:

            link = a.get_attribute("href")

            title = a.inner_text()

            if not link or not title:
                continue

            if link in seen:
                continue

            activities.append((title, link))

    return activities


def check_lms():

    data = load_seen()
    seen = data["seen"]

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = browser.new_page()

        print("Logging into LMS")

        page.goto(LOGIN_URL)

        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)

        page.click('button[type="submit"]')

        page.wait_for_selector("#page")

        page.goto(DASHBOARD_URL)

        page.wait_for_selector("#page")

        activities = scan_courses(page, seen)

        print("New activities:", len(activities))

        for title, url in activities:

            print("Opening:", url)

            page.goto(url)

            page.wait_for_load_state("networkidle")

            page_text = page.inner_text("body")

            # skip submitted assignments
            if "Submission status" in page_text and "Submitted for grading" in page_text:

                seen.append(url)
                continue

            activity_type = "Activity"

            if "mod/assign" in url:
                activity_type = "📚 Assignment"

            elif "mod/quiz" in url:
                activity_type = "📝 Quiz"

            elif "mod/forum" in url:
                activity_type = "📢 Announcement"

            elif "mod/resource" in url:
                activity_type = "📂 New File"

            due = get_due_date(page)

            desc = get_description(page)

            msg = f"{activity_type}\n\n"

            msg += f"Title: {title}\n"

            if due:
                msg += f"Due: {due.strftime('%d %B %Y')}\n"

            if desc:
                msg += "\nDescription:\n"
                msg += desc[:400] + "\n"

            msg += "\nOpen:\n"
            msg += url

            send_whatsapp(msg)

            seen.append(url)

        save_seen(data)

        browser.close()


if __name__ == "__main__":

    print("Running LMS scan")

    try:
        check_lms()
    except Exception as e:
        print("Error:", e)