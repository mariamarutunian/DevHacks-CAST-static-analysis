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
        print("file", CVE_GITHUB_COMMITS, " already exists")
        unique_links = []
        with open(CVE_GITHUB_COMMITS, 'r', encoding='latin1') as f:
            for line in f:
                CVE_ID_LINK = line.split()
                unique_links.append(CVE_ID_LINK)                
        return unique_links
        
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
    file_tag = repo_url.strip("https://").replace("/", "_")
    os.makedirs(out_path, exist_ok=True)
    repodir = os.path.join(out_path, f"{file_tag}_{commit_hash}")
    diff_file = repodir + ".diff"
    
    if not os.path.exists(repodir):
        os.makedirs(repodir, exist_ok=True)
        try:
            repo = Repo.clone_from(repo_url, repodir, depth=1, no_single_branch=True)
            repo.git.fetch("origin", commit_hash)
            repo.git.checkout(commit_hash)
        except Exception as e:
            print(f"[!] Failed to clone or checkout {repo_url}@{commit_hash}: {e}")
            return
        
        # save diff
        diff_output = subprocess.run(
            ["git", "diff", "-W", f"{commit_hash}~1", commit_hash],
            cwd=repodir,
            capture_output=True, text=True
        ).stdout

        with open(diff_file, "w") as f:
            f.write(diff_output)
        print(f"[+] Saved diff in {diff_file}")

    
    extract_changed_functions(repodir, diff_file)
        
def extract_changed_functions(repodir, diff_file):
    with open(diff_file, "r") as f:
        diff_content = f.read()
    import parse_diff
    results = parse_diff.parse_git_diff_to_old_version(diff_content)
    
    repo_all_diffs = repodir + "_all_diffs"
    os.makedirs(repo_all_diffs, exist_ok=True)

    repo_vulnerable_fragments = repodir + "_vulnerable_fragments"
    os.makedirs(repo_vulnerable_fragments, exist_ok=True)

    for i in range(len(results)):
        item = results[i]
        path_part = "part_" + str(i) + "_" + item['file'].replace("/", "_")

        diff_part = os.path.join(repo_all_diffs, path_part + ".diff")
        with open(diff_part, "w") as f:
            f.write(item['diff_part'])

        is_code_change = if_code_functional_change(diff_part)
        
        if is_code_change:
            print(f"{diff_part} contains functional change, saving old, vulnarable version")
            old_version_path = os.path.join(repo_vulnerable_fragments, path_part)
            with open(old_version_path, "w") as f:
                f.write(item['old_version'])
    
    remove_useless_files(repodir, diff_file, repo_all_diffs)

def if_code_functional_change(diff_part):
    import check_for_functional_patch
    git_diff = check_for_functional_patch.get_git_diff(file_path=diff_part)

    analyzer = check_for_functional_patch.CodeChangeAnalyzer("codellama/CodeLlama-7b-Instruct-hf")
    analyzer.download_and_load_model()
    is_code_change, explanation = analyzer.analyze_diff(git_diff)
    return is_code_change

def remove_useless_files(repodir, diff_file, repo_all_diffs):
    import shutil
    try:
        shutil.rmtree(repodir)
        shutil.rmtree(repo_all_diffs)
        os.remove(diff_file)
    except OSError as e:
        print(f"Error: {e.strerror}")

def process_all_commits(unique_links):
    os.makedirs(EXTRACTED_FUNCTIONS_DIR, exist_ok=True)
    for cve_id, commit_url in tqdm(unique_links, desc="Processing commits"):
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
