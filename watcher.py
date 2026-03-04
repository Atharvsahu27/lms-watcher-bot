import requests
from bs4 import BeautifulSoup
import time
import json
import os
import urllib3

# Disable SSL warnings (needed for Railway container)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

USERNAME = os.getenv("LMS_USER")
PASSWORD = os.getenv("LMS_PASS")

SEEN_FILE = "seen_assignments.json"


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            data = json.load(f)
            return data["assignments"]
    except:
        return []


def save_seen(assignments):
    with open(SEEN_FILE, "w") as f:
        json.dump({"assignments": assignments}, f)


def login(session):

    print("Loading login page...")

    login_page = session.get(LOGIN_URL, verify=False)

    soup = BeautifulSoup(login_page.text, "html.parser")

    token_input = soup.find("input", {"name": "logintoken"})

    if not token_input:
        raise Exception("Login token not found")

    logintoken = token_input["value"]

    print("Submitting login form...")

    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "logintoken": logintoken
    }

    session.post(LOGIN_URL, data=payload, verify=False)

    dashboard = session.get(DASHBOARD_URL, verify=False)

    print("Dashboard URL:", dashboard.url)

    return dashboard


def check_assignments():

    print("Starting assignment check...")

    session = requests.Session()

    dashboard = login(session)

    soup = BeautifulSoup(dashboard.text, "html.parser")

    assignments = []

    for link in soup.find_all("a", href=True):

        if "mod/assign/view.php" in link["href"]:

            title = link.text.strip()

            if title:
                assignments.append(title)

    print("Assignments found:", assignments)

    seen = load_seen()

    for a in assignments:
        if a not in seen:
            print("NEW ASSIGNMENT DETECTED:", a)

    save_seen(assignments)


print("LMS watcher started...")

while True:

    try:

        check_assignments()

        print("Sleeping for 10 minutes...\n")

        time.sleep(600)

    except Exception as e:

        print("Error occurred:", e)

        print("Retrying in 60 seconds...\n")

        time.sleep(60)