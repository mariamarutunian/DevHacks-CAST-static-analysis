from transformers import AutoTokenizer, AutoModel
import torch
import argparse
import json
import os

model_name = "microsoft/unixcoder-base-nine"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
model.eval()


def chunk_code(code: str, max_tokens=512, stride=256) -> list[list[int]]:
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
        return torch.zeros(model.config.hidden_size)

    embeddings = []
    with torch.no_grad():
        for chunk in chunks:
            input_ids = torch.tensor([chunk])
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
    args = parser.parse_args()

    results = []

    for root, _, files in os.walk(args.dir):
        print(f"Directory: {root}")
        for file in files:
            print(f"Processing file: {file}")
            filepath = os.path.abspath(str(os.path.join(root, file)))

            if not os.path.isfile(filepath):
                continue  # Skip non-regular files

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"Skipping file {filepath} due to read error: {e}")
                continue

            embedding = get_embedding(content).tolist()
            results.append({
                "path": filepath,
                "embedding": embedding
            })

    output_path = args.dir + args.suffix
    with open(output_path, 'w', encoding='utf-8') as out_file:
        json.dump(results, out_file, indent=2, ensure_ascii=False)

    print(f"Results written to {output_path}")
    os._exit(0)


if __name__ == "__main__":
    main()
