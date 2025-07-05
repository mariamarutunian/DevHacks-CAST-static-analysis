#!/usr/bin/env python3
"""
Code Change Analyzer using Code Llama 7B
Analyzes git commit diffs to determine if they contain real code changes
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import argparse
import logging

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "transformers", "torch", "accelerate"])
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeChangeAnalyzer:
    def __init__(self, model_name="codellama/CodeLlama-7b-Instruct-hf", use_4bit=True):
        """Initialize the analyzer with Code Llama model"""
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = None  # Will be set after model loading
        self._initial_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_4bit = use_4bit and torch.cuda.is_available()  # Only use 4bit on GPU
        
    def download_and_load_model(self):
        """Download and load the Code Llama model"""
        logger.info(f"Loading model: {self.model_name}")
        logger.info(f"Preferred device: {self._initial_device}")
        logger.info(f"Using 4-bit quantization: {self.use_4bit}")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Prepare model loading arguments
            model_kwargs = {
                "trust_remote_code": True,
                "low_cpu_mem_usage": True,
            }
            
            if self._initial_device.type == "cuda":
                if self.use_4bit:
                    # Use 4-bit quantization for speed and memory efficiency
                    try:
                        from transformers import BitsAndBytesConfig
                        
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_quant_type="nf4"
                        )
                        
                        model_kwargs.update({
                            "quantization_config": quantization_config,
                            "torch_dtype": torch.float16,
                            "device_map": "auto"
                        })
                        
                        logger.info("Using 4-bit quantization for faster inference")
                        
                    except ImportError:
                        logger.warning("BitsAndBytesConfig not available, installing...")
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "bitsandbytes"])
                        from transformers import BitsAndBytesConfig
                        
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_quant_type="nf4"
                        )
                        
                        model_kwargs.update({
                            "quantization_config": quantization_config,
                            "torch_dtype": torch.float16,
                            "device_map": "auto"
                        })
                else:
                    # Standard GPU loading
                    model_kwargs.update({
                        "torch_dtype": torch.float16,
                        "device_map": "auto"
                    })
                    
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )
                
                # Update device to match where the model actually ended up
                if hasattr(self.model, 'device'):
                    self.device = self.model.device
                elif hasattr(self.model, 'hf_device_map'):
                    # Get the device of the first layer
                    first_device = list(self.model.hf_device_map.values())[0]
                    self.device = torch.device(first_device)
                else:
                    self.device = self._initial_device
                    
            else:
                # For CPU - use smaller dtype and optimizations
                model_kwargs.update({
                    "torch_dtype": torch.float32,
                })
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )
                self.model = self.model.to(self._initial_device)
                self.device = self._initial_device
                
            logger.info(f"Model loaded successfully on device: {self.device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def create_analysis_prompt(self, git_diff):
        """Create a prompt for analyzing the git diff"""
        prompt = f"""<s>[INST] You are a code analysis expert. Analyze the following git diff and determine if it contains REAL CODE CHANGES that affect functionality.

REAL CODE CHANGES include:
- Logic changes (conditions, loops, calculations)
- Function/method implementations
- Algorithm modifications
- Data structure changes
- API changes
- Bug fixes that change behavior

NOT REAL CODE CHANGES include:
- README/documentation updates
- Comment changes (adding/removing/updating comments)
- Variable/function renaming without logic changes
- Formatting/whitespace changes
- Import reordering without functional impact
- Version number updates
- Configuration file changes (unless they affect code behavior)

Git Diff:
```
{git_diff}
```

Analyze this diff and respond with ONLY:
"YES" if it contains real code changes
"NO" if it only contains documentation, comments, renaming, or formatting changes

Response: [/INST]"""
        
        return prompt
    
    def analyze_diff(self, git_diff):
        """Analyze a git diff and determine if it contains real code changes"""
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded. Call download_and_load_model() first.")
        
        # Truncate very large diffs to avoid memory issues and speed up processing
        if len(git_diff) > 8000:
            logger.warning(f"Diff is large ({len(git_diff)} chars), truncating to 8000 chars")
            git_diff = git_diff[:8000] + "\n... (truncated)"
        
        prompt = self.create_analysis_prompt(git_diff)
        
        # Tokenize input with shorter max length for faster processing
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,  # Reduced from 4000 for speed
            padding=True
        )
        
        # Move inputs to the same device as the model
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate response with optimized settings
        with torch.no_grad():
            try:
                outputs = self.model.generate(
                    inputs['input_ids'],
                    attention_mask=inputs['attention_mask'],
                    max_new_tokens=5,  # Reduced from 10 - we only need YES/NO
                    temperature=0.1,
                    do_sample=False,  # Greedy decoding is faster
                    pad_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,  # Enable KV caching for speed
                    num_return_sequences=1
                )
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.error("GPU out of memory. Try using --no-4bit or CPU mode.")
                    raise
                else:
                    logger.error(f"Runtime error during generation: {e}")
                    raise
        
        # Decode response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract the answer after [/INST]
        try:
            answer = response.split("[/INST]")[-1].strip()
            # Look for YES or NO in the response
            if "YES" in answer.upper():
                return True, answer
            elif "NO" in answer.upper():
                return False, answer
            else:
                # If unclear, be conservative and assume it's a code change
                return True, f"Unclear response: {answer}"
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return True, f"Error parsing response: {response}"

def get_git_diff(commit_hash=None, file_path=None):
    """Get git diff from command line or file"""
    if file_path:
        with open(file_path, 'r') as f:
            return f.read()
    
    if commit_hash:
        try:
            result = subprocess.run(
                ['git', 'show', commit_hash],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting git diff: {e}")
            return None
    
    # Get diff from stdin
    if not sys.stdin.isatty():
        return sys.stdin.read()
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Analyze git diffs for real code changes using Code Llama")
    parser.add_argument("--commit", "-c", help="Git commit hash to analyze")
    parser.add_argument("--file", "-f", help="File containing git diff")
    parser.add_argument("--model", "-m", default="codellama/CodeLlama-7b-Instruct-hf", 
                       help="Model name to use (default: codellama/CodeLlama-7b-Instruct-hf)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get git diff
    git_diff = get_git_diff(args.commit, args.file)
    
    if not git_diff:
        if sys.stdin.isatty():
            print("Usage: ")
            print("  python script.py --commit <commit_hash>")
            print("  python script.py --file <diff_file>")
            print("  git show <commit> | python script.py")
            sys.exit(1)
        else:
            print("No git diff provided")
            sys.exit(1)
    
    # Initialize analyzer
    analyzer = CodeChangeAnalyzer(args.model)
    
    try:
        # Download and load model
        analyzer.download_and_load_model()
        
        # Analyze the diff
        is_code_change, explanation = analyzer.analyze_diff(git_diff)
        
        # Output result
        if args.verbose:
            print(f"Analysis: {explanation}")
            print(f"Result: {'REAL CODE CHANGE' if is_code_change else 'NOT A REAL CODE CHANGE'}")
        else:
            print("YES" if is_code_change else "NO")
            
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()