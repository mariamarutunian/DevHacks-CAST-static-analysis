import os
import re
import requests
from collections import defaultdict
from bs4 import BeautifulSoup
from tqdm import tqdm
from git import Repo
import tempfile
import subprocess

ALLITEMS_URL = "https://cve.mitre.org/data/downloads/allitems.txt"
ALLITEMS_FILE = "allitems.txt"
CVE_GITHUB_COMMITS = "cve_github_commit.txt"
EXTRACTED_FUNCTIONS_DIR = "extracted_functions"
CVE_FIRST_YEAR = "2014"
CVE_LAST_YEAR = "2014"

def download_allitems():
    if not os.path.exists(ALLITEMS_FILE):
        print(f"Downloading {ALLITEMS_URL}...")
        r = requests.get(ALLITEMS_URL)
        r.raise_for_status()
        with open(ALLITEMS_FILE, 'wb') as f:
            f.write(r.content)
    else:
        print(f"{ALLITEMS_FILE} already exists. Skipping download.")

def extract_github_links():
    if os.path.exists(CVE_GITHUB_COMMITS):
        print("file", CVE_GITHUB_COMMITS, "exists")
        unique_links = []
        with open(CVE_GITHUB_COMMITS, 'r', encoding='latin1') as f:
            for line in f.read():
                unique_links.append(line.split())
        
    cve_commits = set()
    with open(ALLITEMS_FILE, 'r', encoding='latin1') as f:
        content = f.read()

    entries = content.split("=======================================")
    for entry in entries:
        cve_pattern = r'CVE-\d{4}-\d{4,7}'
        first_match = re.search(cve_pattern, entry)
        if not first_match:
            continue
        cve_id = first_match.group()
        
        links = re.findall(r"https://github\.com/[^\s)]+/commit/[0-9a-f]{7,40}", entry)
        for link in links:
            if CVE_FIRST_YEAR <= cve_id[4:8] <= CVE_LAST_YEAR:
                cve_commits.add((link.strip(), cve_id))

    unique_links = sorted(cve_commits)

    print("Creating file", CVE_GITHUB_COMMITS)
    with open(CVE_GITHUB_COMMITS, 'w') as f:
        for link, cve_id in unique_links:
                f.write(f"{cve_id} {link}\n")
    print(f"Extracted {len(unique_links)} unique CVE-related GitHub commit links.")

    return unique_links

def get_repo_info(commit_url):
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/commit/([0-9a-f]+)", commit_url)
    if not m:
        return None, None
    repo_url = f"https://github.com/{m.group(1)}"
    commit_hash = m.group(2)
    return repo_url, commit_hash

def sparse_clone_and_extract(repo_url, commit_hash, out_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            repo = Repo.clone_from(repo_url, tmpdir, depth=1, no_single_branch=True)
            repo.git.fetch("origin", commit_hash)
            repo.git.checkout(commit_hash)
        except Exception as e:
            print(f"[!] Failed to clone or checkout {repo_url}@{commit_hash}: {e}")
            return
        
        # save diff
        diff_output = subprocess.run(
            ["git", "diff", f"{commit_hash}~1", commit_hash],
            cwd=tmpdir,
            capture_output=True, text=True
        ).stdout

        file_tag = repo_url.strip("https://").replace("/", "_")
        os.makedirs(out_path, exist_ok=True)
        output_file_start = os.path.join(out_path, f"{file_tag}_{commit_hash}")
        diff_file = output_file_start + ".diff"

        with open(diff_file, "w") as f:
            f.write(diff_output)
        print(f"[+] Saved diff in {diff_file}")

        function_names = extract_changed_functions(diff_output)
        print("function_names", function_names)

        # Extract functions using regex for simplicity
        #function_pattern = re.compile(r'^[+-]\s*(\w[\w\s\*]+)?\s+(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE)
        #functions_file = output_file_start + ".functions"
            
        #with open(functions_file, "w") as f:
        #    for match in function_pattern.finditer(diff_output):
        #        f.write(match.group(0) + "\n")
        #print(f"[+] Saved function matches in {functions_file}")
        
def extract_changed_functions(diff_content):
    """
    Extracts the names of functions that have been changed (added or modified)
    in a given Git diff content.

    This function specifically looks for Python function definitions ('def function_name(...)')
    within lines marked as added (+) or removed (-) in the diff.

    Args:
        diff_content: A string containing the Git diff output.

    Returns:
        A set of strings, where each string is the name of a function
        that was changed in the diff.
    """
    changed_functions = set()
    # Regex to capture Python function definitions:
    # ^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?\):
    # ^\s* - Start of line, optional leading whitespace
    # def\s+     - 'def' keyword followed by one or more spaces
    # ([a-zA-Z_][a-zA-Z0-9_]*) - Capturing group for function name:
    #                            starts with letter or underscore, followed by letters, digits, or underscores
    # \s*\(.*?\): - Optional whitespace, opening parenthesis, any characters (non-greedy), closing parenthesis, colon
    function_pattern = re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?\):")

    # Split the diff content into lines
    lines = diff_content.splitlines()

    for line in lines:
        # Check if the line is an added or removed line in the diff
        if line.startswith('+') or line.startswith('-'):
            # Remove the '+' or '-' prefix for easier regex matching
            code_line = line[1:].strip()
            match = function_pattern.match(code_line)
            if match:
                function_name = match.group(1)
                changed_functions.add(function_name)

    return changed_functions

def process_all_commits(unique_links):
    os.makedirs(EXTRACTED_FUNCTIONS_DIR, exist_ok=True)
    for commit_url, cve_id in tqdm(unique_links, desc="Processing commits"):
        repo_url, commit_hash = get_repo_info(commit_url)
        if not repo_url:
            continue
        sparse_clone_and_extract(repo_url, commit_hash, EXTRACTED_FUNCTIONS_DIR)


def main():
    download_allitems()
    unique_links = extract_github_links()
    
    process_all_commits(unique_links)

if __name__ == "__main__":
    main()
