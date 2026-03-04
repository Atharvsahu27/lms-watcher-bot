import requests
from bs4 import BeautifulSoup
import time
import json
import os

LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

USERNAME = os.getenv("LMS_USER")
PASSWORD = os.getenv("LMS_PASS")


def load_seen():
    try:
        with open("seen_assignments.json") as f:
            return json.load(f)["assignments"]
    except:
        return []


def save_seen(assignments):
    with open("seen_assignments.json", "w") as f:
        json.dump({"assignments": assignments}, f)


def check_assignments():

    session = requests.Session()

    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }

    session.post(LOGIN_URL, data=payload)

    dashboard = session.get(DASHBOARD_URL)

    soup = BeautifulSoup(dashboard.text, "html.parser")

    assignments = []

    for link in soup.find_all("a"):
        href = link.get("href", "")
        if "assign" in href:
            assignments.append(link.text.strip())

    seen = load_seen()

    for a in assignments:
        if a not in seen:
            print("New assignment detected:", a)

    save_seen(assignments)


while True:

    check_assignments()

    time.sleep(600)