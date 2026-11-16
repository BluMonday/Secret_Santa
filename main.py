import base64
import json
import random
import os
import re
from datetime import date
from urllib.parse import urlsplit

PAGES_BASE_URL = "https://blumonday.github.io/Secret_Santa"
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "match_history.json")

class Person:
    def __init__(self, name, exclusions):
        self.name = name
        self.exclusions = exclusions
    def __str__(self):
        return f"{self.name} matched with {self.match}"
    name = ""
    email = ""
    match = ""

def find_matching(people, history_exclusions=None):
    assignments = {}
    history_exclusions = history_exclusions or {}

    def search(unassigned, remaining_recipients):
        if not unassigned:
            return True

        candidates_by_person = {}
        for person in unassigned:
            candidates = [
                recipient
                for recipient in remaining_recipients
                if recipient != person.name
                and recipient not in person.exclusions
                and recipient not in history_exclusions.get(person.name, set())
                and assignments.get(recipient) != person.name
            ]
            if not candidates:
                return False
            candidates_by_person[person.name] = candidates

        fewest_candidates = min(len(candidates) for candidates in candidates_by_person.values())
        most_constrained = [
            person for person in unassigned
            if len(candidates_by_person[person.name]) == fewest_candidates
        ]
        person = random.choice(most_constrained)
        candidates = candidates_by_person[person.name]
        random.shuffle(candidates)

        for recipient in candidates:
            assignments[person.name] = recipient
            if search(
                [other for other in unassigned if other != person],
                remaining_recipients - {recipient},
            ):
                return True
            del assignments[person.name]

        return False

    if search(people[:], {person.name for person in people}):
        return assignments
    return None

def load_history():
    with open(HISTORY_FILE, encoding="utf-8") as file:
        history = json.load(file)
    if not isinstance(history, dict):
        raise ValueError("Match history must be a JSON object keyed by year.")
    for year, assignments in history.items():
        if not year.isdigit() or not isinstance(assignments, dict):
            raise ValueError("Each match-history entry must map a year to participant assignments.")
        if any(not isinstance(giver, str) or not isinstance(recipient, str)
               for giver, recipient in assignments.items()):
            raise ValueError(f"Assignments for {year} must map participant names to names.")
    return history

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, sort_keys=True)
        file.write("\n")

def find_matching_with_history(people, history):
    years = sorted(history, key=int)
    participant_names = {person.name for person in people}

    for oldest_year_index in range(len(years) + 1):
        active_years = years[oldest_year_index:]
        history_exclusions = {}
        for year in active_years:
            for giver, recipient in history[year].items():
                if giver in participant_names:
                    history_exclusions.setdefault(giver, set()).add(recipient)

        matches = find_matching(people, history_exclusions)
        if matches is not None:
            return matches, active_years, years[:oldest_year_index]

    return None, [], years

def save_results(people, pages_base_url):
    names = [person.name for person in people]
    if not names:
        raise ValueError("At least one participant is required.")
    if len(names) != len(set(names)):
        raise ValueError("Participant names must be unique.")
    if any(not name or "\0" in name for name in names):
        raise ValueError("Participant names must be nonempty and cannot contain null characters.")

    parsed_url = urlsplit(pages_base_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc or parsed_url.query or parsed_url.fragment:
        raise ValueError("Enter the HTTPS base URL for the GitHub Pages site.")
    pages_base_url = pages_base_url.rstrip("/")

    encoded_names = {name: name.encode("utf-8") for name in names}
    padded_name_length = max(len(name) for name in encoded_names.values())
    codes = {}
    for name, encoded_name in encoded_names.items():
        payload = encoded_name + b"\0" + b"\0" * (padded_name_length - len(encoded_name))
        codes[name] = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    def render_page(content):
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta name="referrer" content="no-referrer">
  <title>Secret Santa Match</title>
  <style>
    :root {{
      --evergreen: #164b35;
      --berry: #a32638;
      --gold: #c9a85b;
      --cream: #fffaf0;
    }}
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
      padding: 1rem; box-sizing: border-box;
      background: linear-gradient(135deg, #10452f, #1d6848 58%, #842538);
      color: #20352c; font: 18px/1.5 system-ui, sans-serif; }}
    main {{ box-sizing: border-box; width: min(90%, 32rem); padding: 2rem;
      border: 2px solid var(--gold); border-top: 0.5rem solid var(--berry);
      border-radius: 1rem; background: var(--cream); text-align: center;
      box-shadow: 0 0.5rem 2rem #09291955; }}
    h1 {{ color: var(--evergreen); font-size: clamp(1.7rem, 8vw, 2.5rem); }}
    h1::after {{ content: ""; display: block; width: 4rem; height: 3px;
      margin: 0.75rem auto; border-radius: 2px; background: var(--berry); }}
    #message {{ color: #526357; }}
    #recipient {{ color: var(--berry); font-size: clamp(2rem, 10vw, 3rem); font-weight: 700; }}
  </style>
</head>
<body>
  <main>
    <h1>Your Secret Santa Match</h1>
    {content}
    <p id="recipient" hidden></p>
  </main>
  <script>
    const code = new URLSearchParams(window.location.search).get("p");
    const message = document.getElementById("message");
    const recipient = document.getElementById("recipient");
    if (!code || !/^[A-Za-z0-9_-]+$/.test(code)) {{
      message.textContent = "This link is invalid or no longer current. Ask the organizer for your link.";
    }} else {{
      fetch("matches/" + code + ".json")
        .then(response => {{
          if (!response.ok) {{
            throw new Error("Match not found");
          }}
          return response.json();
        }})
        .then(data => {{
          if (typeof data.recipient !== "string") {{
            throw new Error("Invalid match data");
          }}
          message.textContent = "You are giving a gift to:";
          recipient.textContent = data.recipient;
          recipient.hidden = false;
        }})
        .catch(() => {{
          message.textContent = "This link is invalid or no longer current. Ask the organizer for your link.";
        }});
    }}
  </script>
</body>
</html>
"""

    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    matches_dir = os.path.join(docs_dir, "matches")
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(matches_dir, exist_ok=True)
    for filename in os.listdir(matches_dir):
        if re.fullmatch(r"[A-Za-z0-9_-]+\.json", filename):
            os.remove(os.path.join(matches_dir, filename))

    with open(os.path.join(docs_dir, "index.html"), "w", encoding="utf-8") as file:
        file.write(render_page('<p id="message">Use your personal link to view your match.</p>'))

    for person in people:
        match_data_path = os.path.join(matches_dir, f"{codes[person.name]}.json")
        with open(match_data_path, "w", encoding="utf-8") as file:
            json.dump({"recipient": person.match}, file, ensure_ascii=True)

    print(f"Generated {os.path.join(docs_dir, 'index.html')} for GitHub Pages.")
    for person in people:
        print(f"{person.name}: {pages_base_url}/?p={codes[person.name]}")
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    people = [Person("Peter",["Paige"]),
              Person("Paige", ["Peter"]),
              Person("Rob", ["Cindy"]),
              Person("Cindy", ["Rob"]),
              Person("Carrie", ["Cody"]),
              Person("Cody", ["Carrie"]),
              Person("Dale", []),
              ]
    history = load_history()
    matches, active_years, dropped_years = find_matching_with_history(people, history)
    if matches is None:
        print("No valid matching found.")
    else:
        if dropped_years:
            print(f"Dropped oldest history years: {', '.join(dropped_years)}")
        if active_years:
            print(f"Applied history years: {', '.join(active_years)}")
        for person in people:
            person.match = matches[person.name]
        save_results(people, PAGES_BASE_URL)
        history[str(date.today().year)] = matches
        save_history(history)
        print(f"Saved match history for {date.today().year}.")

    # printout names for testing
    if False:
        for person in people:
            print(person)


