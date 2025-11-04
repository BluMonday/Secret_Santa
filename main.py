import random

class Person:
    def __init__(self, name, exclusions):
        self.name = name
        self.exclusions = exclusions
    def __str__(self):
        return f"{self.name} matched with {self.match}"
    name = ""
    email = ""
    match = ""

def cycle_check(people):
    target_length = len(people)
    i = 1
    # keep track of where we start
    first_person = people[0]
    # init loop variables
    current_person = first_person
    next_person = [x for x in people if x.name == current_person.match][0]
    while first_person != next_person:
        i += 1
        current_person = next_person
        next_person = [x for x in people if x.name == current_person.match][0]
    if i == target_length:
        print("full cycle!")
        return True
    else:
        print(f"not full cycle. Target: {target_length} Result: {i}")
        return False

def save_results(people):
    for person in people:
        f = open(f"{person.name}.txt", "w")
        f.write(f"You have been matched with: {person.match}!")
        f.close()
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    all_names = ["Peter", "Paige", "Rob", "Cindy", "Carrie", "Cody", "Dale"]
    people = [Person("Peter",["Paige", "Cindy"]),
              Person("Paige", ["Peter", "Rob"]),
              Person("Rob", ["Cindy", "Dale"]),
              Person("Cindy", ["Rob", "Cody"]),
              Person("Carrie", ["Cody", "Peter"]),
              Person("Cody", ["Carrie", "Paige"]),
              Person("Dale", ["Carrie"]),
              ]
    while True:
        try:
            # copy by value
            remaining_names = all_names[:]
            random.shuffle(people)
            for person in people:
                match_candidates = [x for x in remaining_names if x != person.name and x not in person.exclusions]
                random.shuffle(match_candidates)
                person.match = match_candidates[0]
                remaining_names.remove(person.match)
        except:
            print("Invalid. Trying again...")
            continue
        else:
            if cycle_check(people):
                save_results(people)
                break
            else:
                continue

    # printout names for testing
    if False:
        for person in people:
            print(person)


