# Vulnerability Detector

Vulnerability Detector is a tool developed during the ԴևHacks (VTC, Armenia 2025) hackathon to identify known vulnerabilities (CVEs) in software projects.

The tool collects CVE data (primarily from cve.org) and analyzes the associated fix commits to extract the specific code changes that address each vulnerability. These extracted code fragments (representing CVE fixes) are then used to search for similar, potentially vulnerable code patterns in other software projects.


Vulnerability Detector-ը գործիք է, որը մշակվել է ԴևHacks (VTC, Armenia 2025) հաքաթոնի ընթացքում՝ ծրագրերում հայտնի խոցելիությունները (CVE) հայտնաբերելու համար։
Հիմնական գաղափարը ներառում է հայտնի խոցելիությունների (CVE) մասին տվյալների հավաքագրում (հիմնականում cve.org կայքից) և մշակում, մասնավորապես խոցելիություն պարունակող և ուղղած կոդի տարբերակների առանձնացում LLM-ին ուղղված թիրախավորված հարցումների միջոցով։ Այնուհետև, օգտագործելով ML մոդել (UniXcoder), հավաքագրված տվյալները և մուտքային ծրագրի նախնական կոդը թարգմանվում է թվային վեկտորի, ինչն էլ հնարավորություն է տալիս գտնել նմանատիպ կոդի հատվածներ մուտքային ծրագրում, պոտենցիալ խոցելիության մասին զեկուցելու համար։
---

## extract_github_cves.py

This script automates the process of extracting vulnerable code fragments from public GitHub CVE fix commits.

### Steps:

1. Downloading CVE Data
2. Extracting GitHub Commit Links
3. Cloning Repos and Extracting Diffs
4. Filtering Functional Changes by using targeted prompting for LLM

Produces a set of code fragments representing vulnerable implementations that were fixed in known CVE commits. 

---

## function_extractor.py

This script extracts complete function definitions from source code files across multiple languages.

- Supports:
  - C
  - C++
  - Python
  - Java
  - Rust

Outputs extracted functions in either plain text or JSON format.

---

## project_functions_embedder.py

Generates embeddings for all files (each containing a function) in a given directory using the microsoft/unixcoder-base-nine model. 
It uses overlapping chunks on large functions, computes averaged CLS embeddings, and saves results as a JSON file.

---

## detect_clones_from_embeddings.py

Compares embeddings from CVE and project JSON files using cosine similarity. 
Reports matching pairs (above a threshold) as potential clones and saves the results to a JSON file.

---
