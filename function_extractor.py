#!/usr/bin/env python3
"""
Multi-Language Function Extractor

This script extracts complete function declarations and bodies from source code
files in multiple programming languages: C, C++, Python, Java, and Rust.

Usage:
    python function_extractor.py <file_path>
    python function_extractor.py <directory_path> --recursive
"""

import re
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Function:
    """Represents an extracted function"""
    name: str
    signature: str
    body: str
    start_line: int
    end_line: int
    language: str


class FunctionExtractor:
    """Main class for extracting functions from source code"""
    
    def __init__(self):
        self.language_extensions = {
            'c': ['.c', '.h'],
            'cpp': ['.cpp', '.cc', '.cxx', '.c++', '.hpp', '.hh', '.hxx', '.h++'],
            'python': ['.py', '.pyx'],
            'java': ['.java'],
            'rust': ['.rs']
        }
        
    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language based on file extension"""
        ext = Path(file_path).suffix.lower()
        for lang, extensions in self.language_extensions.items():
            if ext in extensions:
                return lang
        return None
    
    def extract_functions(self, file_path: str) -> List[Function]:
        """Extract functions from a source file"""
        language = self.detect_language(file_path)
        if not language:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
        
        if language == 'python':
            return self._extract_python_functions(content, file_path)
        elif language in ['c', 'cpp']:
            return self._extract_c_cpp_functions(content, file_path, language)
        elif language == 'java':
            return self._extract_java_functions(content, file_path)
        elif language == 'rust':
            return self._extract_rust_functions(content, file_path)
        
        return []
    
    def _extract_python_functions(self, content: str, file_path: str) -> List[Function]:
        """Extract Python functions and methods"""
        functions = []
        lines = content.split('\n')
        
        # Pattern for function/method definitions
        func_pattern = re.compile(r'^(\s*)(def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*[^:]+)?\s*:)')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.match(line)
            
            if match:
                indent = len(match.group(1))
                func_name = match.group(3)
                signature = match.group(2).strip()
                start_line = i + 1
                
                # Find the end of the function
                j = i + 1
                while j < len(lines):
                    current_line = lines[j]
                    # Skip empty lines and comments
                    if current_line.strip() == '' or current_line.strip().startswith('#'):
                        j += 1
                        continue
                    
                    # Check if we've reached the end of the function
                    current_indent = len(current_line) - len(current_line.lstrip())
                    if current_line.strip() and current_indent <= indent:
                        break
                    j += 1
                
                end_line = j
                body = '\n'.join(lines[i:end_line])
                
                functions.append(Function(
                    name=func_name,
                    signature=signature,
                    body=body,
                    start_line=start_line,
                    end_line=end_line,
                    language='python'
                ))
                
                i = end_line
            else:
                i += 1
        
        return functions
    
    def _extract_c_cpp_functions(self, content: str, file_path: str, language: str) -> List[Function]:
        """Extract C/C++ functions"""
        functions = []
        
        # Remove comments to avoid false matches
        content = self._remove_c_comments(content)
        
        # Pattern for function definitions (simplified)
        # This matches return_type function_name(parameters) {
        func_pattern = re.compile(
            r'(?:^|\n)\s*'  # Start of line
            r'(?:(?:static|extern|inline|virtual|explicit|const|constexpr|template\s*<[^>]*>)\s+)*'  # Modifiers
            r'([a-zA-Z_][a-zA-Z0-9_]*(?:\s*\*\s*|\s*&\s*|\s+))'  # Return type
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*'  # Function name
            r'(\([^)]*\))\s*'  # Parameters
            r'(?:const\s*)?'  # Optional const
            r'(?:override\s*)?'  # Optional override
            r'(?:final\s*)?'  # Optional final
            r'(?:noexcept\s*)?'  # Optional noexcept
            r'(?:throw\s*\([^)]*\)\s*)?'  # Optional throw specification
            r'\s*\{',  # Opening brace
            re.MULTILINE | re.DOTALL
        )
        
        lines = content.split('\n')
        
        for match in func_pattern.finditer(content):
            func_name = match.group(2)
            signature = f"{match.group(1).strip()} {func_name}{match.group(3)}"
            
            # Find the complete function body by matching braces
            start_pos = match.start()
            brace_pos = match.end() - 1  # Position of opening brace
            
            # Find matching closing brace
            brace_count = 1
            pos = brace_pos + 1
            
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            if brace_count == 0:
                # Extract the complete function
                func_body = content[start_pos:pos]
                
                # Calculate line numbers
                start_line = content[:start_pos].count('\n') + 1
                end_line = content[:pos].count('\n') + 1
                
                functions.append(Function(
                    name=func_name,
                    signature=signature.strip(),
                    body=func_body.strip(),
                    start_line=start_line,
                    end_line=end_line,
                    language=language
                ))
        
        return functions
    
    def _extract_java_functions(self, content: str, file_path: str) -> List[Function]:
        """Extract Java methods"""
        functions = []
        
        # Remove comments
        content = self._remove_java_comments(content)
        
        # Pattern for method definitions
        method_pattern = re.compile(
            r'(?:^|\n)\s*'  # Start of line
            r'(?:(?:public|private|protected|static|final|abstract|synchronized|native|strictfp)\s+)*'  # Modifiers
            r'([a-zA-Z_][a-zA-Z0-9_<>[\]]*(?:\s*\*\s*|\s+))'  # Return type
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*'  # Method name
            r'(\([^)]*\))\s*'  # Parameters
            r'(?:throws\s+[a-zA-Z0-9_,\s]+)?\s*'  # Optional throws
            r'\{',  # Opening brace
            re.MULTILINE | re.DOTALL
        )
        
        for match in method_pattern.finditer(content):
            method_name = match.group(2)
            signature = f"{match.group(1).strip()} {method_name}{match.group(3)}"
            
            # Find the complete method body
            start_pos = match.start()
            brace_pos = match.end() - 1
            
            brace_count = 1
            pos = brace_pos + 1
            
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            if brace_count == 0:
                func_body = content[start_pos:pos]
                start_line = content[:start_pos].count('\n') + 1
                end_line = content[:pos].count('\n') + 1
                
                functions.append(Function(
                    name=method_name,
                    signature=signature.strip(),
                    body=func_body.strip(),
                    start_line=start_line,
                    end_line=end_line,
                    language='java'
                ))
        
        return functions
    
    def _extract_rust_functions(self, content: str, file_path: str) -> List[Function]:
        """Extract Rust functions"""
        functions = []
        
        # Remove comments
        content = self._remove_rust_comments(content)
        
        # Pattern for function definitions
        func_pattern = re.compile(
            r'(?:^|\n)\s*'  # Start of line
            r'(?:(?:pub|const|unsafe|extern|async)\s+)*'  # Modifiers
            r'fn\s+'  # fn keyword
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*'  # Function name
            r'(?:<[^>]*>)?\s*'  # Optional generics
            r'(\([^)]*\))\s*'  # Parameters
            r'(?:->\s*[^{]+)?\s*'  # Optional return type
            r'\{',  # Opening brace
            re.MULTILINE | re.DOTALL
        )
        
        for match in func_pattern.finditer(content):
            func_name = match.group(1)
            signature = f"fn {func_name}{match.group(2)}"
            
            # Find the complete function body
            start_pos = match.start()
            brace_pos = match.end() - 1
            
            brace_count = 1
            pos = brace_pos + 1
            
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            if brace_count == 0:
                func_body = content[start_pos:pos]
                start_line = content[:start_pos].count('\n') + 1
                end_line = content[:pos].count('\n') + 1
                
                functions.append(Function(
                    name=func_name,
                    signature=signature.strip(),
                    body=func_body.strip(),
                    start_line=start_line,
                    end_line=end_line,
                    language='rust'
                ))
        
        return functions
    
    def _remove_c_comments(self, content: str) -> str:
        """Remove C/C++ style comments"""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def _remove_java_comments(self, content: str) -> str:
        """Remove Java style comments"""
        return self._remove_c_comments(content)  # Same as C/C++
    
    def _remove_rust_comments(self, content: str) -> str:
        """Remove Rust style comments"""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def process_file(self, file_path: str) -> List[Function]:
        """Process a single file and extract functions"""
        return self.extract_functions(file_path)
    
    def process_directory(self, directory_path: str, recursive: bool = False) -> Dict[str, List[Function]]:
        """Process all supported files in a directory"""
        results = {}
        
        path = Path(directory_path)
        if not path.exists():
            print(f"Directory {directory_path} does not exist")
            return results
        
        # Get all supported file extensions
        supported_extensions = set()
        for extensions in self.language_extensions.values():
            supported_extensions.update(extensions)
        
        # Find all supported files
        if recursive:
            files = [f for f in path.rglob('*') if f.suffix.lower() in supported_extensions]
        else:
            files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in supported_extensions]
        
        for file_path in files:
            functions = self.process_file(str(file_path))
            if functions:
                results[str(file_path)] = functions
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Extract functions from source code files')
    parser.add_argument('path', help='File or directory path to process')
    parser.add_argument('--recursive', '-r', action='store_true', 
                       help='Process directories recursively')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    
    args = parser.parse_args()
    
    extractor = FunctionExtractor()
    
    if os.path.isfile(args.path):
        # Process single file
        functions = extractor.process_file(args.path)
        results = {args.path: functions} if functions else {}
    elif os.path.isdir(args.path):
        # Process directory
        results = extractor.process_directory(args.path, args.recursive)
    else:
        print(f"Error: {args.path} is not a valid file or directory")
        sys.exit(1)
    
    # Output results
    if args.format == 'json':
        import json
        output_data = {}
        for file_path, functions in results.items():
            output_data[file_path] = [
                {
                    'name': f.name,
                    'signature': f.signature,
                    'body': f.body,
                    'start_line': f.start_line,
                    'end_line': f.end_line,
                    'language': f.language
                }
                for f in functions
            ]
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
        else:
            print(json.dumps(output_data, indent=2))
    else:
        # Text format
        output_lines = []
        for file_path, functions in results.items():
            #output_lines.append(f"=== {file_path} ===")
            #output_lines.append(f"Found {len(functions)} functions")
            #output_lines.append("")
            
            for func in functions:
                #output_lines.append(f"Function: {func.name}")
                #output_lines.append(f"Language: {func.language}")
                #output_lines.append(f"Lines: {func.start_line}-{func.end_line}")
                #output_lines.append(f"Signature: {func.signature}")
                #output_lines.append("Body:")
                #output_lines.append("-" * 50)
                output_lines.append(func.body)
                output_lines.append("-" * 50)
        
        output_text = '\n'.join(output_lines)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_text)
        else:
            print(output_text)


if __name__ == "__main__":
    main()