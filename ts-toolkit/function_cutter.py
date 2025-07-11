from enum import Enum
import subprocess
import datetime
import argparse
import json
import sys
import re
import os


PATH_TO_SRC = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
FIXED_TIMESTAMP = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
TREE_SITTER_PATH = os.path.expanduser("~/.cargo/bin/tree-sitter") # Change as needed


class EXTENSIONS(Enum):
    C = ".c"
    H = ".h"
    CC = ".cc"
    CPP = ".cpp"
    HPP = ".hpp"
    CXX = ".cxx"
    HXX = ".hxx"
    CS = ".cs"
    JAVA = ".java"
    JS = ".js"
    MJS = ".mjs"
    CJS = ".cjs"
    JSX = ".jsx"
    PY = ".py"
    RB = ".rb"
    RS = ".rs"


EXTENSION_TO_FUNCTION_NODE_LIST = {
    EXTENSIONS.C.value: ["function_definition"],
    EXTENSIONS.H.value: ["function_definition"],
    EXTENSIONS.CC.value: ["function_definition"],
    EXTENSIONS.CPP.value: ["function_definition"],
    EXTENSIONS.HPP.value: ["function_definition"],
    EXTENSIONS.CXX.value: ["function_definition"],
    EXTENSIONS.HXX.value: ["function_definition"],
    EXTENSIONS.CS.value: ["method_declaration"],
    EXTENSIONS.JAVA.value: ["method_declaration"],
    EXTENSIONS.JS.value: ["function_declaration"],
    EXTENSIONS.MJS.value: ["function_declaration"],
    EXTENSIONS.CJS.value: ["function_declaration"],
    EXTENSIONS.JSX.value: ["function_declaration"],
    EXTENSIONS.PY.value: ["function_definition"],
    EXTENSIONS.RB.value: ["method"],
    EXTENSIONS.RS.value: ["function_item"],
}


def append_function_contents(file_path: str, functions_positions: list):
    result = []

    with open(file_path, 'r') as f:
        lines = f.readlines()

    for function_position in functions_positions:
        start_row = function_position['start']['row']
        start_col = function_position['start']['column']
        end_row = function_position['end']['row']
        end_col = function_position['end']['column']

        if start_row == end_row:
            snippet = lines[start_row][start_col:end_col]
        else:
            snippet_lines = [lines[start_row][start_col:]]
            snippet_lines += lines[start_row + 1:end_row]
            snippet_lines.append(lines[end_row][:end_col])
            snippet = ''.join(snippet_lines)

        result.append({
            "start": {"row": start_row, "column": start_col},
            "end": {"row": end_row, "column": end_col},
            "contents": snippet,
        })

    return result


def get_patterns_from_file_extension(extension: str):
    function_node_list = EXTENSION_TO_FUNCTION_NODE_LIST[extension]
    patterns = []

    for function_node in function_node_list:
        # print(f"Appending to pattern: {function_node}")
        patterns.append(
            re.compile(
                rf'\({function_node}\s+\[(\d+),\s*(\d+)\]\s*-\s*\[(\d+),\s*(\d+)\](.*?)\)',
                re.DOTALL
            ),
        )

    return patterns


def parse_function_positions(file_path: str):
    result = subprocess.run([
        TREE_SITTER_PATH,
        "parse",
        file_path,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Warning! tree-sitter parse return error code {result.returncode} for {file_path}")
        print(f"Error message: {result.stderr}")

    text = result.stdout
    # print(text)

    extension = os.path.splitext(file_path)[1]

    patterns = get_patterns_from_file_extension(extension)

    functions = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            start_line, start_col, end_line, end_col = map(int, match.groups()[0:4])

            functions.append({
                "start": {"row": start_line, "column": start_col},
                "end": {"row": end_line, "column": end_col},
            })

    return functions


def process_file(file_path, result):
    file_path = os.path.abspath(file_path)
    functions_positions = parse_function_positions(file_path)
    functions_with_full_info = append_function_contents(file_path, functions_positions)

    record = {
        "file_path": file_path,
        "functions": functions_with_full_info,
    }

    # Remove existing record with the same file_path
    result[:] = [r for r in result if r["file_path"] != file_path]

    result.append(record)



def main():
    parser = argparse.ArgumentParser(description="Extract function positions from source files using tree-sitter.")
    parser.add_argument("--source", nargs='+', help="Path(s) to source files")
    parser.add_argument("--dir", nargs='+', help="Path(s) to directory(ies) with source files")
    parser.add_argument("--result", help="Path to result JSON file")
    args = parser.parse_args()

    file_count, parsed_file_count, current_file_count = 0, 0, 0

    if args.source:
        for source_path in args.source:
            if not os.path.exists(source_path):
                parser.error(f"Given source file doesn't exist: {source_path}")
            base_name, extension = os.path.splitext(source_path)
            if extension in (e.value for e in EXTENSIONS):
                file_count += 1
    if args.dir:
        for dir_path in args.dir:
            if not os.path.isdir(dir_path):
                parser.error(f"Given directory path doesn't exist: {dir_path}")
            for dirpath, _, filenames in os.walk(os.path.abspath(dir_path)):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    base_name, extension = os.path.splitext(filepath)
                    if extension in (e.value for e in EXTENSIONS):
                        file_count += 1

    if not args.source and not args.dir:
        parser.error("At least one argument is required to run this script!")
    if not args.result:
        args.result = os.path.join(PATH_TO_SRC, f"{FIXED_TIMESTAMP}_collected_functions.json")

    final_results = []

    if args.source:
        for path in args.source:
            base_name, extension = os.path.splitext(path)
            if not extension in (e.value for e in EXTENSIONS):
                print(f"Skipping file path: {path}")
                print(f"|- Given file extension is not supported: {extension}")
                continue
            current_file_count += 1
            try:
                abs_path = os.path.abspath(path)
                print(f"[{current_file_count}/{file_count}] Processing file: {abs_path}")
                process_file(str(abs_path), final_results)
                parsed_file_count += 1
            except RuntimeError as e:
                print(f"Error processing file '{path}':")
                print(f"|- {e}")
    if args.dir:
        for directory in args.dir:
            for dirpath, _, filenames in os.walk(os.path.abspath(directory)):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    base_name, extension = os.path.splitext(filepath)
                    if os.path.isfile(filepath) and extension in (e.value for e in EXTENSIONS):
                        current_file_count += 1
                        try:
                            abs_path = os.path.abspath(str(filepath))
                            print(f"[{current_file_count}/{file_count}] Processing file: {abs_path}")
                            process_file(str(abs_path), final_results)
                            parsed_file_count += 1
                        except RuntimeError as e:
                            print(f"Error processing file '{filepath}':")
                            print(f"|- {e}")

    with open(args.result, 'w') as f:
        json.dump(final_results, f, indent=2)

    # print(f"Parsed {parsed_file_count}/{file_count} given valid files")
    print(f"You can check results in: {args.result}")


if __name__ == "__main__":
    main()
