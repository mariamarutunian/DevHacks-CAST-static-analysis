# ts-toolkit

A set of utilities built around [tree-sitter](https://tree-sitter.github.io/) for code structure analysis.

---

## Requirements
* Python 3.x
* tree-sitter-cli (via Cargo)
* Node.js (for grammar generation)
* Compilers and build tools (gcc, clang, build-essential etc.)
* Supported tree-sitter grammars cloned and generated locally

---

## Installation
You can set up the full environment using one of these options:

---

### 1. Installer script
Run:

```bash
./install.sh
```

This script:
* Installs all dependencies (system, Cargo, Node.js)
* Clones all Tree-sitter grammar repos into `grammar/`
* Builds each grammar using tree-sitter generate=

---

### 2. Docker
Alternatively, build and run in a containerized environment:

```bash
docker build -t ts-toolkit .
docker run -it --rm ts-toolkit
```
This will also copy `function_cutter.py`, which will be ready for use.

---

## Tools
Currently, the repository includes a single tool:

### `function_cutter.py`

Extracts functions from source code files using tree-sitter and outputs their positions and content in JSON format.

---

#### Supported Languages

Currently supports:
- C
- C++
- C#
- Java
- Javascript
- Python
- Ruby
- Rust

---

#### Usage

```bash
python3 function_cutter.py --source file1.c file2.cpp ...
```
or recursively from a directory:

```bash
python3 function_cutter.py --dir directory --result output.json
```

---

#### Output Format
The result is a JSON list, where each item represents a file and contains:
* File path
* Start row and column of each function
* End row and column
* Function content

> **Note**: If --result argument is not specified the default value is set to:
> `<ts-toolkit>/<timestamp_of_run>_collected_functions.json`.

Example:
```json
[
  {
    "file_path": "src/example.c",
    "functions": [
      {
        "start": {
          "row": 3,
          "column": 0
        },
        "end": {
          "row": 5,
          "column": 1
        },
        "contents": "int func() { ... }"  
      }
    ]
  }
]
```

