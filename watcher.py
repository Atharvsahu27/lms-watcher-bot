import requests
from bs4 import BeautifulSoup
import time
import json
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

USERNAME = os.getenv("LMS_USER")
PASSWORD = os.getenv("LMS_PASS")

print("Starting LMS watcher...")
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

    session.post(LOGIN_URL, data=payload, verify=False)

    dashboard = session.get(DASHBOARD_URL, verify=False)

    soup = BeautifulSoup(dashboard.text, "html.parser")
    print("Dashboard URL:", dashboard.url)

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
    try:
        print("Checking LMS for assignments...")
        check_assignments()

        print("Sleeping for 10 minutes...\n")
        time.sleep(600)

    except Exception as e:
        print("Error occurred:", e)
        time.sleep(60)