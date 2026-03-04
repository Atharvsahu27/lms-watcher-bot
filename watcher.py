import os
import json
import time
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

DATA_FILE = "assignments.json"


def send_whatsapp(msg):

    client = Client(TWILIO_SID, TWILIO_TOKEN)

    client.messages.create(
        body=msg,
        from_="whatsapp:+14155238886",
        to=MY_PHONE
    )


def load_data():

    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"assignments": []}


def save_data(data):

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def days_remaining(due):

    if not due:
        return None

    delta = due - datetime.now()

    return max(delta.days, 0)


def check_assignments():

    data = load_data()
    stored = data["assignments"]

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        page = context.new_page()

        print("Opening LMS login")

        page.goto(LOGIN_URL, timeout=60000)

        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)

        page.click('button[type="submit"]')

        page.wait_for_selector("#page")

        print("Opening dashboard")

        page.goto(DASHBOARD_URL)

        page.wait_for_selector("#page")

        links = page.locator('a[href*="mod/assign/view.php"]').all()

        assignment_links = set()

        for l in links:

            href = l.get_attribute("href")

            if href:
                assignment_links.add(href)

        print("Assignments found:", len(assignment_links))

        for url in assignment_links:

            assignment_id = url.split("id=")[-1]

            if any(a["id"] == assignment_id for a in stored):
                continue

            print("Opening assignment:", url)

            page.goto(url)

            page.wait_for_load_state("networkidle")

            # TITLE
            title = "Assignment"

            if page.locator("h1").count() > 0:
                title = page.locator("h1").first.inner_text().strip()

            # COURSE
            course = "Course"

            crumbs = page.locator(".breadcrumb li")

            if crumbs.count() > 1:
                course = crumbs.nth(1).inner_text().strip()

            # DESCRIPTION
            description = ""

            desc = page.locator(".activity-description")

            if desc.count() > 0:
                description = desc.first.inner_text().strip()

            # DUE DATE
            due_date = None

            date_block = page.locator(".description-inner")

            if date_block.count() > 0:

                text = date_block.first.inner_text()

                if "Due date" in text:

                    lines = text.split("\n")

                    for i in range(len(lines)):

                        if "Due date" in lines[i]:

                            if i + 1 < len(lines):

                                date_str = lines[i+1].strip()

                                try:
                                    due_date = datetime.strptime(
                                        date_str,
                                        "%A, %d %B %Y, %I:%M %p"
                                    )
                                except:
                                    pass

            days = days_remaining(due_date)

            # MESSAGE
            msg = "📚 NEW ASSIGNMENT\n\n"

            msg += f"Course: {course}\n"
            msg += f"Title: {title}\n"

            if due_date:
                msg += f"Due: {due_date.strftime('%d %B %Y')}\n"

            if days is not None:
                msg += f"Days Remaining: {days}\n"

            msg += "\n"

            if description:
                msg += "Description:\n"
                msg += description[:300] + "\n\n"

            msg += "Open Assignment:\n"
            msg += url

            send_whatsapp(msg)

            time.sleep(2)

            stored.append({
                "id": assignment_id,
                "title": title,
                "due": due_date.isoformat() if due_date else None,
                "reminders": []
            })

        save_data(data)

        browser.close()


def check_reminders():

    data = load_data()

    for a in data["assignments"]:

        if not a["due"]:
            continue

        due = datetime.fromisoformat(a["due"])

        days = days_remaining(due)

        if days is None or days < 0:
            continue

        if days == 7 and "7" not in a["reminders"]:

            send_whatsapp(f"⚠️ Reminder\n\n{a['title']} due in 7 days")

            a["reminders"].append("7")

        if days == 3 and "3" not in a["reminders"]:

            send_whatsapp(f"⚠️ Reminder\n\n{a['title']} due in 3 days")

            a["reminders"].append("3")

        if days == 1 and "1" not in a["reminders"]:

            send_whatsapp(f"🚨 Deadline Tomorrow\n\n{a['title']} due tomorrow")

            a["reminders"].append("1")

        time.sleep(2)

    save_data(data)


print("LMS bot started")


while True:

    try:

        check_assignments()

        check_reminders()

        print("Sleeping 10 minutes")

        time.sleep(600)

    except Exception as e:

        print("Error:", e)

        time.sleep(60)