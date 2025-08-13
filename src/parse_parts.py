import os
import re

def parse_10k_parts_and_items(text: str):
    # Match PARTs only when on their own line
    parts_pattern = re.compile(r"^\s*(PART\s+[IVXLC]+)\s*$", re.IGNORECASE | re.MULTILINE)
    items_pattern = re.compile(r"^\s*(Item\s+\d+[A-Z]?\.?\s+.+?)(?=\n|$)", re.IGNORECASE | re.MULTILINE)

    # Find all part headers with their start positions
    raw_parts = [(match.group(1).upper().strip(), match.start()) for match in parts_pattern.finditer(text)]

    # Define desired part order
    valid_order = ["PART I", "PART II", "PART III", "PART IV"]
    part_blocks = {}

    # Slice part text blocks
    for i in range(len(raw_parts)):
        title, start = raw_parts[i]
        end = raw_parts[i + 1][1] if i + 1 < len(raw_parts) else len(text)
        if title in valid_order:
            part_blocks[title] = text[start:end]

    parsed = {}

    # Process parts in correct order
    for part in valid_order:
        if part not in part_blocks:
            continue

        part_text = part_blocks[part]
        item_matches = list(items_pattern.finditer(part_text))

        if not item_matches:
            continue  # skip parts with no items

        parsed[part] = {}

        for j in range(len(item_matches)):
            item_title = item_matches[j].group(1).strip()
            item_start = item_matches[j].end()
            item_end = item_matches[j + 1].start() if j + 1 < len(item_matches) else len(part_text)
            item_content = part_text[item_start:item_end].strip()

            # Normalize title (remove weird spacing or extra dots)
            item_title = re.sub(r'\s{2,}', ' ', item_title).replace('..', '.').strip()
            parsed[part][item_title] = item_content

    return parsed


def save_parsed_to_txt(parsed_data: dict, output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for part in ["PART I", "PART II", "PART III", "PART IV"]:
            if part not in parsed_data:
                continue

            f.write(f"{part}\n{'=' * len(part)}\n\n")
            for item_title, content in parsed_data[part].items():
                f.write(f"{item_title}\n{'-' * len(item_title)}\n")
                f.write(content + "\n\n")


def parse_and_save_all(folder_path: str):
    if not os.path.exists(folder_path):
        print(f"❌ Folder does not exist: {folder_path}")
        return

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".txt") and "_parsed" not in filename:
            file_path = os.path.join(folder_path, filename)
            print(f"📂 Parsing: {filename}")

            with open(file_path, encoding="utf-8") as f:
                text = f.read()

            parsed = parse_10k_parts_and_items(text)

            out_filename = filename.replace(".txt", "_parsed.txt")
            out_path = os.path.join(folder_path, out_filename)

            save_parsed_to_txt(parsed, out_path)
            print(f"✅ Saved structured output to: {out_path}")


if __name__ == "__main__":
    folder = r"C:\Users\Nathan Kong\Downloads\sec_txt"
    parse_and_save_all(folder)
