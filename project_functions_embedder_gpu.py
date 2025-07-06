from transformers import AutoTokenizer, AutoModel
import torch
import argparse
import json
import os
from typing import List

# Check for GPU availability and set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

model_name = "microsoft/unixcoder-base-nine"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

# Move model to GPU
model = model.to(device)
model.eval()

# Enable mixed precision for better GPU performance
if device.type == "cuda":
    model = model.half()  # Use FP16 for faster inference
    print("Using FP16 precision for GPU acceleration")


def chunk_code(code, max_tokens=512, stride=256):
    token_ids = tokenizer.encode(code, add_special_tokens=True, truncation=False)
    chunks = []

    for start in range(0, len(token_ids), stride):
        end = min(start + max_tokens, len(token_ids))
        chunk = token_ids[start:end]
        if len(chunk) < 2:
            continue
        chunks.append(chunk)
        if end == len(token_ids):
            break

    return chunks


def get_embedding(code):
    chunks = chunk_code(code)
    if not chunks:
        return torch.zeros(model.config.hidden_size, device=device)

    embeddings = []
    with torch.no_grad():
        for chunk in chunks:
            # Move input tensors to GPU
            input_ids = torch.tensor([chunk], device=device)
            outputs = model(input_ids)
            cls_embedding = outputs.last_hidden_state[:, 0, :]
            embeddings.append(cls_embedding)

    # Average all CLS embeddings
    all_cls = torch.cat(embeddings, dim=0)
    return all_cls.mean(dim=0)


def main():
    parser = argparse.ArgumentParser(description="Get embeddings for functions in a given directory and write results to JSON.")
    parser.add_argument("--dir", required=True, help="Path to the directory to process")
    parser.add_argument("--suffix", default="_embeddings.json", help="Suffix for the output JSON file (default: _embeddings.json)")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for processing multiple files (default: 8)")
    args = parser.parse_args()

    results = []
    file_paths = []
    
    # Collect all file paths first
    for root, _, files in os.walk(args.dir):
        for file in files:
            filepath = os.path.abspath(str(os.path.join(root, file)))
            if os.path.isfile(filepath):
                file_paths.append(filepath)
    
    print(f"Found {len(file_paths)} files to process")

    # Process files in batches for better GPU utilization
    for i in range(0, len(file_paths), args.batch_size):
        batch_files = file_paths[i:i + args.batch_size]
        print(f"Processing batch {i//args.batch_size + 1}/{(len(file_paths) + args.batch_size - 1)//args.batch_size}")
        
        batch_contents = []
        batch_paths = []
        
        # Read batch of files
        for filepath in batch_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = str(f.read())
                batch_contents.append(content)
                batch_paths.append(filepath)
            except Exception as e:
                print(f"Skipping file {filepath} due to read error: {e}")
                continue
        
        # Process batch
        for content, filepath in zip(batch_contents, batch_paths):
            embedding = get_embedding(content).cpu().tolist()  # Move to CPU before converting to list
            results.append({
                "path": filepath,
                "embedding": embedding
            })
        
        # Clear GPU cache periodically
        if device.type == "cuda":
            torch.cuda.empty_cache()

    output_path = args.dir + args.suffix
    with open(output_path, 'w', encoding='utf-8') as out_file:
        json.dump(results, out_file, indent=2, ensure_ascii=False)

    print(f"Results written to {output_path}")
    
    # Final cleanup
    if device.type == "cuda":
        torch.cuda.empty_cache()
    
    os._exit(0)


if __name__ == "__main__":
    main()