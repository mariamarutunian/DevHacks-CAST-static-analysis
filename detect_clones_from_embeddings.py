import argparse
import json
import torch
import torch.nn.functional as F


def compare_a_pair(embedding1, embedding2):
    similarity = F.cosine_similarity(embedding1, embedding2, dim=0).item()
    return similarity


def main():
    parser = argparse.ArgumentParser(description="Compare CVE embeddings with project embeddings.")
    parser.add_argument("--cve", required=True, help="Path to JSON file with CVE embeddings")
    parser.add_argument("--project", required=True, help="Path to JSON file with project embeddings")
    parser.add_argument("--out", default="comparison_results.json", help="Path to output JSON file")
    args = parser.parse_args()

    clones_count = 0

    with open(args.cve, 'r', encoding='utf-8') as f:
        cve_data = json.load(f)

    with open(args.project, 'r', encoding='utf-8') as f:
        project_data = json.load(f)

    results = []

    for cve_entry in cve_data:
        cve_path = cve_entry["path"]
        cve_tensor = torch.tensor(cve_entry["embedding"])

        for project_entry in project_data:
            project_path = project_entry["path"]
            project_tensor = torch.tensor(project_entry["embedding"])

            score = compare_a_pair(cve_tensor, project_tensor)
            
            if score < 0.95:  # Change as needed
                continue

            clones_count += 1

            results.append({
                "cve_function_path": cve_path,
                "project_function_path": project_path,
                "similarity": score
            })

    with open(args.out, 'w', encoding='utf-8') as out_file:
        json.dump(results, out_file, indent=2, ensure_ascii=False)

    print(f"Found {clones_count} clones")
    print(f"Comparison results saved to {args.out}")


if __name__ == "__main__":
    main()
