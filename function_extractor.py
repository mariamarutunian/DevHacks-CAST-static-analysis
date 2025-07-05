#!/usr/bin/env python3
"""
Multi-Language Function Body Extractor

This script extracts complete function definitions (including bodies) from source code files
supporting C, C++, Python, and Java.
"""

import re
import os
import sys
from typing import List, Dict, Tuple, Optional
from pathlib import Path

class FunctionExtractor:
    def __init__(self):
        # File extensions mapping
        self.extensions = {
            '.c': 'c',
            '.h': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.hpp': 'cpp',
            '.hxx': 'cpp',
            '.py': 'python',
            '.java': 'java',
        }

    def detect_language(self, filename: str) -> str:
        """Detect programming language based on file extension."""
        ext = Path(filename).suffix.lower()
        return self.extensions.get(ext, 'unknown')

    def find_matching_brace(self, content: str, start_pos: int) -> int:
        """Find the matching closing brace for an opening brace."""
        brace_count = 0
        i = start_pos
        
        while i < len(content):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
            elif content[i] == '"':
                # Skip string literals
                i += 1
                while i < len(content) and content[i] != '"':
                    if content[i] == '\\':
                        i += 1  # Skip escaped character
                    i += 1
            elif content[i] == "'":
                # Skip character literals
                i += 1
                while i < len(content) and content[i] != "'":
                    if content[i] == '\\':
                        i += 1  # Skip escaped character
                    i += 1
            i += 1
        
        return -1

    def extract_c_cpp_functions(self, content: str, language: str) -> List[Dict]:
        """Extract C/C++ function definitions with complete bodies."""
        functions = []
        
        # Pattern for function definitions (not just declarations)
        patterns = [
            # Standard function definition
            r'(?:^|\n)(\s*(?:static\s+|extern\s+|inline\s+|virtual\s+|explicit\s+)*(?:[a-zA-Z_][a-zA-Z0-9_:]*(?:\s*[*&])*\s+)?[a-zA-Z_][a-zA-Z0-9_:]*\s*\([^)]*\)(?:\s*const)?(?:\s*override)?(?:\s*final)?)\s*\{',
            # Constructor definitions
            r'(?:^|\n)(\s*(?:explicit\s+)?[A-Z][a-zA-Z0-9_]*\s*\([^)]*\)(?:\s*:\s*[^{]*)?)\s*\{',
            # Destructor definitions
            r'(?:^|\n)(\s*(?:virtual\s+)?~[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\))\s*\{',
            # Template function definitions
            r'(?:^|\n)(template\s*<[^>]*>\s*(?:inline\s+|static\s+)*[a-zA-Z_][a-zA-Z0-9_:]*(?:\s*[*&])*\s+[a-zA-Z_][a-zA-Z0-9_:]*\s*\([^)]*\))\s*\{',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                signature = match.group(1).strip()
                brace_start = match.end() - 1  # Position of opening brace
                
                # Find matching closing brace
                brace_end = self.find_matching_brace(content, brace_start)
                
                if brace_end != -1:
                    # Extract complete function body
                    full_function = content[match.start():brace_end + 1].strip()
                    
                    # Extract function name
                    func_name = self.extract_function_name(signature, language)
                    
                    # Calculate line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    functions.append({
                        'name': func_name,
                        'signature': signature,
                        'body': full_function,
                        'line_number': line_num,
                        'language': language
                    })
        
        return functions

    def extract_python_functions(self, content: str) -> List[Dict]:
        """Extract Python function definitions with complete bodies."""
        functions = []
        
        # Pattern for Python function definitions
        patterns = [
            r'(?:^|\n)(\s*(?:@[a-zA-Z_][a-zA-Z0-9_.]*\s*\n\s*)*(?:async\s+)?def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                signature = match.group(1).strip()
                def_start = match.start()
                def_end = match.end()
                
                # Find the complete function body by analyzing indentation
                function_body = self.extract_python_function_body(content, def_start, def_end)
                
                if function_body:
                    # Extract function name
                    func_name = self.extract_function_name(signature, 'python')
                    
                    # Calculate line number
                    line_num = content[:def_start].count('\n') + 1
                    
                    functions.append({
                        'name': func_name,
                        'signature': signature,
                        'body': function_body,
                        'line_number': line_num,
                        'language': 'python'
                    })
        
        return functions

    def extract_python_function_body(self, content: str, start_pos: int, def_end: int) -> str:
        """Extract complete Python function body based on indentation."""
        lines = content.split('\n')
        start_line = content[:start_pos].count('\n')
        
        # Find the base indentation of the function definition
        def_line = lines[start_line]
        base_indent = len(def_line) - len(def_line.lstrip())
        
        function_lines = []
        i = start_line
        
        # Add the function definition line(s)
        while i < len(lines):
            line = lines[i]
            function_lines.append(line)
            if line.strip().endswith(':'):
                break
            i += 1
        
        i += 1  # Move to first line after colon
        
        # Extract function body based on indentation
        while i < len(lines):
            line = lines[i]
            
            # Empty lines are part of the function
            if line.strip() == '':
                function_lines.append(line)
                i += 1
                continue
            
            # Check indentation
            current_indent = len(line) - len(line.lstrip())
            
            # If indentation is greater than base, it's part of the function
            if current_indent > base_indent:
                function_lines.append(line)
            else:
                # Function ended
                break
            
            i += 1
        
        return '\n'.join(function_lines)

    def extract_java_functions(self, content: str) -> List[Dict]:
        """Extract Java method definitions with complete bodies."""
        functions = []
        
        # Pattern for Java method definitions
        patterns = [
            # Regular methods
            r'(?:^|\n)(\s*(?:public\s+|private\s+|protected\s+|static\s+|final\s+|abstract\s+|synchronized\s+|native\s+)*[a-zA-Z_][a-zA-Z0-9_<>\[\]]*\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)(?:\s*throws\s+[^{;]+)?)\s*\{',
            # Constructors
            r'(?:^|\n)(\s*(?:public\s+|private\s+|protected\s+)*[A-Z][a-zA-Z0-9_]*\s*\([^)]*\)(?:\s*throws\s+[^{;]+)?)\s*\{',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                signature = match.group(1).strip()
                brace_start = match.end() - 1  # Position of opening brace
                
                # Find matching closing brace
                brace_end = self.find_matching_brace(content, brace_start)
                
                if brace_end != -1:
                    # Extract complete function body
                    full_function = content[match.start():brace_end + 1].strip()
                    
                    # Extract function name
                    func_name = self.extract_function_name(signature, 'java')
                    
                    # Calculate line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    functions.append({
                        'name': func_name,
                        'signature': signature,
                        'body': full_function,
                        'line_number': line_num,
                        'language': 'java'
                    })
        
        return functions

    def extract_function_name(self, signature: str, language: str) -> str:
        """Extract function name from signature."""
        if language == 'python':
            # Python: def function_name(
            match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', signature)
            return match.group(1) if match else 'unknown'
        
        elif language == 'java':
            # Java: return_type function_name( or Constructor(
            # Remove modifiers and find the function name
            parts = signature.split('(')[0].split()
            return parts[-1] if parts else 'unknown'
        
        else:  # C/C++
            # C/C++: return_type function_name(
            # Handle template functions, constructors, destructors
            if signature.startswith('template'):
                # Template function
                template_part = signature.split('>', 1)[1] if '>' in signature else signature
                parts = template_part.split('(')[0].split()
                return parts[-1] if parts else 'unknown'
            elif '~' in signature:
                # Destructor
                match = re.search(r'~([a-zA-Z_][a-zA-Z0-9_]*)', signature)
                return '~' + match.group(1) if match else 'unknown'
            else:
                # Regular function or constructor
                parts = signature.split('(')[0].split()
                return parts[-1] if parts else 'unknown'

    def extract_functions_from_content(self, content: str, language: str) -> List[Dict]:
        """Extract function definitions from source code content."""
        if language == 'python':
            return self.extract_python_functions(content)
        elif language in ['c', 'cpp']:
            return self.extract_c_cpp_functions(content, language)
        elif language == 'java':
            return self.extract_java_functions(content)
        else:
            return []

    def extract_from_file(self, filepath: str) -> List[Dict]:
        """Extract function definitions from a single file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            language = self.detect_language(filepath)
            if language == 'unknown':
                print(f"Warning: Unknown file type for {filepath}")
                return []
            
            functions = self.extract_functions_from_content(content, language)
            
            # Add filepath to each function record
            for func in functions:
                func['file'] = filepath
            
            return functions
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return []

    def extract_from_directory(self, directory: str, recursive: bool = True) -> List[Dict]:
        """Extract function definitions from all supported files in a directory."""
        all_functions = []
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    filepath = os.path.join(root, file)
                    if Path(filepath).suffix.lower() in self.extensions:
                        functions = self.extract_from_file(filepath)
                        all_functions.extend(functions)
        else:
            for file in os.listdir(directory):
                filepath = os.path.join(directory, file)
                if os.path.isfile(filepath) and Path(filepath).suffix.lower() in self.extensions:
                    functions = self.extract_from_file(filepath)
                    all_functions.extend(functions)
        
        return all_functions

    def print_functions(self, functions: List[Dict], show_body: bool = True, group_by_file: bool = True):
        """Print extracted functions in a formatted way."""
        if not functions:
            print("No functions found.")
            return
        
        if group_by_file:
            # Group functions by file
            files = {}
            for func in functions:
                file_path = func['file']
                if file_path not in files:
                    files[file_path] = []
                files[file_path].append(func)
            
            for file_path, file_functions in files.items():
                #print(f"\n{'='*80}")
                #print(f"File: {file_path}")
                #print(f"Language: {file_functions[0]['language'].upper()}")
                #print(f"Functions found: {len(file_functions)}")
                #print('='*80)
                
                for i, func in enumerate(file_functions, 1):
                    #print(f"\n{'-'*60}")
                    #print(f"Function {i}: {func['name']} (Line {func['line_number']})")
                    #print(f"{'-'*60}")
                    #print(f"Signature: {func['signature']}")
                    if show_body:
                        #print(f"\nComplete Definition:")
                        print(func['body'])
        else:
            # Print all functions sequentially
            for i, func in enumerate(functions, 1):
                print(f"\n{'='*80}")
                #print(f"Function {i}: {func['name']}")
                #print(f"File: {func['file']}")
                #print(f"Language: {func['language'].upper()}")
                #print(f"Line: {func['line_number']}")
                #print('='*80)
                #print(f"Signature: {func['signature']}")
                if show_body:
                    #print(f"\nComplete Definition:")
                    print(func['body'])

    def save_to_file(self, functions: List[Dict], output_file: str, format_type: str = 'txt'):
        """Save extracted functions to a file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if format_type == 'csv':
                    f.write("File,Language,Line,Name,Signature,Body\n")
                    for func in functions:
                        # Escape commas and quotes in CSV
                        signature = func['signature'].replace('"', '""')
                        body = func['body'].replace('"', '""')
                        f.write(f'"{func["file"]}","{func["language"]}",{func["line_number"]},"{func["name"]}","{signature}","{body}"\n')
                else:
                    # Default text format
                    for i, func in enumerate(functions, 1):
                        #f.write(f"Function {i}: {func['name']}\n")
                        #f.write(f"File: {func['file']}\n")
                        #f.write(f"Language: {func['language'].upper()}\n")
                        #f.write(f"Line: {func['line_number']}\n")
                        #f.write(f"Signature: {func['signature']}\n")
                        #f.write(f"\nComplete Definition:\n")
                        f.write(func['body'])
                        f.write("\n" + "="*80 + "\n")
            
            print(f"Results saved to {output_file}")
            
        except Exception as e:
            print(f"Error saving to file: {e}")

def main():
    """Main function to run the script."""
    extractor = FunctionExtractor()
    
    if len(sys.argv) < 2:
        print("Usage: python function_extractor.py <file_or_directory> [options]")
        print("Options:")
        print("  --recursive, -r        : Search directories recursively")
        print("  --output, -o FILE      : Save results to file")
        print("  --format FORMAT        : Output format (txt, csv)")
        print("  --no-body             : Show only signatures, not full bodies")
        print("  --help, -h            : Show this help message")
        return
    
    # Parse command line arguments
    target = sys.argv[1]
    recursive = '--recursive' in sys.argv or '-r' in sys.argv
    show_body = '--no-body' not in sys.argv
    output_file = None
    format_type = 'txt'
    
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    elif '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if '--format' in sys.argv:
        idx = sys.argv.index('--format')
        if idx + 1 < len(sys.argv):
            format_type = sys.argv[idx + 1]
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print("Function Body Extractor")
        print("Extracts complete function definitions (including bodies)")
        print("Supports: C, C++, Python, Java")
        print("\nUsage: python function_extractor.py <file_or_directory> [options]")
        print("\nOptions:")
        print("  --recursive, -r        : Search directories recursively")
        print("  --output, -o FILE      : Save results to file")
        print("  --format FORMAT        : Output format (txt, csv)")
        print("  --no-body             : Show only signatures, not full bodies")
        print("  --help, -h            : Show this help message")
        return
    
    # Extract functions
    if os.path.isfile(target):
        print(f"Processing file: {target}")
        functions = extractor.extract_from_file(target)
    elif os.path.isdir(target):
        print(f"Processing directory: {target} (recursive: {recursive})")
        functions = extractor.extract_from_directory(target, recursive)
    else:
        print(f"Error: {target} is not a valid file or directory")
        return
    
    # Display results
    print(f"\nTotal functions found: {len(functions)}")
    
    if functions:
        #extractor.print_functions(functions, show_body=show_body)
        
        if output_file:
            extractor.save_to_file(functions, output_file, format_type)

if __name__ == "__main__":
    main()