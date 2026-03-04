import requests
from bs4 import BeautifulSoup
import time
import json
import os
import urllib3
from datetime import datetime
from twilio.rest import Client

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

USERNAME = os.getenv("LMS_USER")
PASSWORD = os.getenv("LMS_PASS")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
MY_PHONE = os.getenv("MY_PHONE")

DATA_FILE = "assignments.json"


def send_whatsapp(msg, media=None):

    client = Client(TWILIO_SID, TWILIO_TOKEN)

    client.messages.create(
        body=msg,
        media_url=[media] if media else None,
        from_='whatsapp:+14155238886',
        to=MY_PHONE
    )


def load_data():

    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {"assignments": []}


def save_data(data):

    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def login(session):

    login_page = session.get(LOGIN_URL, verify=False)

    soup = BeautifulSoup(login_page.text, "html.parser")

    token = soup.find("input", {"name": "logintoken"})["value"]

    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "logintoken": token
    }

    session.post(LOGIN_URL, data=payload, verify=False)

    dashboard = session.get(DASHBOARD_URL, verify=False)

    print("Dashboard:", dashboard.url)

    return dashboard


def parse_due_date(text):

    try:
        return datetime.strptime(text, "%A, %d %B %Y, %I:%M %p")
    except:
        return None


def days_remaining(due):

    if not due:
        return None

    delta = due - datetime.now()

    return delta.days


def get_assignment_details(session, url):

    page = session.get(url, verify=False)

    soup = BeautifulSoup(page.text, "html.parser")

    title = soup.find("h2").text.strip()

    description = ""

    desc = soup.find("div", {"class": "no-overflow"})
    if desc:
        description = desc.text.strip()

    attachments = []

    for link in soup.find_all("a", href=True):

        if any(ext in link["href"] for ext in [".pdf", ".doc", ".docx"]):

            attachments.append(link["href"])

    due_date = None

    for row in soup.find_all("td"):

        if "Due date" in row.text:

            due_text = row.find_next("td").text.strip()

            due_date = parse_due_date(due_text)

    return title, description, attachments, due_date


def format_message(course, title, desc, attachments, due, days, url):

    msg = f"""
📚 NEW ASSIGNMENT

Course: {course}
Title: {title}

Due: {due}
Days Remaining: {days}

Description:
{desc[:300]}

Attachments:
"""

    for a in attachments:
        msg += f"\n{a}"

    msg += f"\n\nOpen Assignment:\n{url}"

    return msg


def check_assignments():

    session = requests.Session()

    dashboard = login(session)

    soup = BeautifulSoup(dashboard.text, "html.parser")

    data = load_data()

    stored = data["assignments"]

    links = []

    for link in soup.find_all("a", href=True):

        if "mod/assign/view.php" in link["href"]:

            links.append(link["href"])

    for url in links:

        assignment_id = url.split("id=")[-1]

        if not any(a["id"] == assignment_id for a in stored):

            print("New assignment found:", url)

            title, desc, attachments, due = get_assignment_details(session, url)

            days = days_remaining(due)

            course = "Course"

            msg = format_message(course, title, desc, attachments, due, days, url)

            send_whatsapp(msg)

            stored.append({
                "id": assignment_id,
                "title": title,
                "due": str(due),
                "reminders": []
            })

    save_data(data)


def check_reminders():

    data = load_data()

    for a in data["assignments"]:

        if not a["due"]:
            continue

        due = datetime.fromisoformat(a["due"])

        days = days_remaining(due)

        if days == 7 and "7" not in a["reminders"]:

            send_whatsapp(f"Reminder: {a['title']} due in 7 days")

            a["reminders"].append("7")

        if days == 3 and "3" not in a["reminders"]:

            send_whatsapp(f"Reminder: {a['title']} due in 3 days")

            a["reminders"].append("3")

        if days == 1 and "1" not in a["reminders"]:

            send_whatsapp(f"Reminder: {a['title']} due tomorrow")

            a["reminders"].append("1")

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