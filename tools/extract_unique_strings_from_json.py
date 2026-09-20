"""Extract all unique string values from a JSON file.

The initial goal was to review the test files to anonymize data before
committing to source control. This was done after manually checking the file
and replacing obvious stuff, since some strings may look like garbage when
looked in isolation when in fact they are not (i.e. some ids used in api calls)

I did not remove dates and base64-encoded strings from the results because one
might want to also check those to be extra sure. It might have been better to
pair each string with the name of the field it's assigned to (perhaps the whole
hierarchy of fields up to the root, and group strings by that) but that was
maybe a bit overkill considering the JSON I used is not huge and I hope I won't
have to update it.

Sample usage:
    $ python tools/extract_unique_strings_from_json.py
    result exported at: /path/to/jiraworklogs/walk_result.json
"""
import json
import os


def extract_all_unique_strings(json_obj) -> set[str]:
    all_strings = set()
    def walk(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                walk(value)
        elif isinstance(obj, str):
            all_strings.add(obj)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
        elif isinstance(obj, (int, float)) or obj is None:
            # bool/int, float and null are valid JSON values we don't care about
            pass
        else:
            print(f"ERROR: cannot walk on value `{obj}` (type `{type(obj)}`)")

    walk(json_obj)
    return all_strings


if __name__ == "__main__":
    with open("test/jira_tasks_with_worklogs.json") as f:
        tasks_data = json.load(f)

    all_strings = extract_all_unique_strings(tasks_data)

    output_path = "walk_result.json"
    with open(output_path, "w") as f:
        json.dump(sorted(all_strings), f, indent=4)
    print("result exported at:", os.path.abspath(output_path))