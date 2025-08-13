import json
import glob
import os

# Set the working directory and output directory
DIRECTORY_PATH = r"C:\Users\Nathan Kong\Downloads\sec_processed"
OUTPUT_PATH = r"C:\Users\Nathan Kong\Downloads\condensed_files"

def contains_apology_phrases(text):
    """
    Check if the text contains apology or "can't help" phrases
    """
    if not isinstance(text, str):
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # List of phrases that indicate the AI couldn't help or provide information
    apology_phrases = [
        "sorry",
        "unfortunately",
        "i can't help",
        "i cannot help",
        "i don't have access",
        "i cannot access",
        "i'm unable to",
        "i am unable to",
        "no content provided",
        "doesn't contain any key facts",
        "does not contain any key facts",
        "brief section:",
        "not applicable",
        "the provided text does not contain",
        "the text does not contain",
        "if you could provide",
        "please provide",
        "can i help you with something else"
    ]
    
    # Check if any apology phrase is in the text
    for phrase in apology_phrases:
        if phrase in text_lower:
            return True
    
    return False

def filter_to_summaries_only(input_file_path):
    """
    Process a single JSON file to keep only the summary fields and filter out apology summaries
    """
    try:
        # Read the original JSON file
        with open(input_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Create new structure with only summaries
        filtered_data = {
            "company": data.get("company", ""),
            "sections": {}
        }
        
        removed_items = []
        
        # Process each part (PART I, PART II, etc.)
        for part_name, part_content in data.get("sections", {}).items():
            filtered_data["sections"][part_name] = {}
            
            # Process each item within the part
            for item_name, item_content in part_content.items():
                if isinstance(item_content, dict) and "summary" in item_content:
                    summary_text = item_content["summary"]
                    
                    # Check if summary contains apology phrases
                    if contains_apology_phrases(summary_text):
                        removed_items.append(f"{part_name} -> {item_name}")
                        # Skip this item (don't add it to filtered_data)
                        continue
                    
                    # Keep only the summary field if it's not an apology
                    filtered_data["sections"][part_name][item_name] = {
                        "summary": summary_text
                    }
                else:
                    # Handle cases where the structure might be different
                    # Only keep if it doesn't contain apology phrases
                    if not contains_apology_phrases(str(item_content)):
                        filtered_data["sections"][part_name][item_name] = item_content
                    else:
                        removed_items.append(f"{part_name} -> {item_name}")
            
            # Remove empty parts
            if not filtered_data["sections"][part_name]:
                del filtered_data["sections"][part_name]
        
        # Copy metadata if it exists
        if "metadata" in data:
            filtered_data["metadata"] = data["metadata"]
        
        return filtered_data, removed_items
    
    except Exception as e:
        print(f"Error processing {input_file_path}: {str(e)}")
        return None, []

def process_all_summary_files():
    """
    Find all files matching the pattern and process them
    """
    # Change to the specified directory
    original_cwd = os.getcwd()
    
    try:
        if not os.path.exists(DIRECTORY_PATH):
            print(f"Source directory not found: {DIRECTORY_PATH}")
            return
            
        # Create output directory if it doesn't exist
        if not os.path.exists(OUTPUT_PATH):
            os.makedirs(OUTPUT_PATH)
            print(f"Created output directory: {OUTPUT_PATH}")
        
        os.chdir(DIRECTORY_PATH)
        print(f"Reading from: {DIRECTORY_PATH}")
        print(f"Saving to: {OUTPUT_PATH}")
        
        # Find all files matching the pattern *_processed_summaries.json
        pattern = "*_processed_summaries.json"
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            print(f"No files found matching pattern: {pattern}")
            print("Files in directory:")
            all_files = [f for f in os.listdir('.') if f.endswith('.json')]
            for f in all_files[:10]:  # Show first 10 files
                print(f"  - {f}")
            if len(all_files) > 10:
                print(f"  ... and {len(all_files) - 10} more files")
            return
        
        print(f"Found {len(matching_files)} files to process:")
        for file in matching_files:
            print(f"  - {file}")
        
        # Process each file
        for input_file in matching_files:
            print(f"\nProcessing: {input_file}")
            
            # Filter the data
            result = filter_to_summaries_only(input_file)
            
            if result is None or result[0] is None:
                print(f"Failed to process {input_file}")
                continue
            
            filtered_data, removed_items = result
            
            # Create output filename in the condensed_files directory
            base_name = os.path.splitext(input_file)[0]  # Remove .json extension
            output_filename = f"{base_name}_summaries_only.json"
            output_file = os.path.join(OUTPUT_PATH, output_filename)
            
            try:
                # Write the filtered data to new file in output directory
                with open(output_file, 'w', encoding='utf-8') as file:
                    json.dump(filtered_data, file, indent=2, ensure_ascii=False)
                
                print(f"Created: {output_filename}")
                print(f"Saved to: {OUTPUT_PATH}")
                
                # Print some statistics
                total_sections = sum(len(part) for part in filtered_data["sections"].values())
                print(f"Processed {len(filtered_data['sections'])} parts with {total_sections} total items")
                
                # Show removed items
                if removed_items:
                    print(f"Removed {len(removed_items)} items with apology/unhelpful content:")
                    for item in removed_items[:5]:  # Show first 5 removed items
                        print(f"        - {item}")
                    if len(removed_items) > 5:
                        print(f"        ... and {len(removed_items) - 5} more")
                else:
                    print(f"No items removed (all summaries were helpful)")
                
            except Exception as e:
                print(f"Error writing {output_file}: {str(e)}")
    
    finally:
        # Return to original directory
        os.chdir(original_cwd)

def preview_structure(file_path, max_items=3):
    """
    Preview the structure of a processed file
    """
    try:
        # Use full path for preview
        full_path = os.path.join(DIRECTORY_PATH, file_path) if not os.path.isabs(file_path) else file_path
        
        with open(full_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        print(f"\nPreview of {os.path.basename(file_path)}:")
        print(f"Company: {data.get('company', 'Unknown')}")
        print("Structure:")
        
        for part_name, part_content in data.get("sections", {}).items():
            print(f"  {part_name}:")
            items_shown = 0
            for item_name, item_content in part_content.items():
                if items_shown < max_items:
                    if isinstance(item_content, dict) and "summary" in item_content:
                        summary_preview = item_content["summary"][:100] + "..." if len(item_content["summary"]) > 100 else item_content["summary"]
                        print(f"    {item_name}:")
                        print(f"      summary: \"{summary_preview}\"")
                    items_shown += 1
                else:
                    remaining = len(part_content) - max_items
                    if remaining > 0:
                        print(f"    ... and {remaining} more items")
                    break
                    
    except Exception as e:
        print(f"Error previewing {file_path}: {str(e)}")

if __name__ == "__main__":
    print("=== JSON Summary Filter Tool ===")
    print("This script will process all *_processed_summaries.json files")
    print("and create new files with only the summary fields.\n")
    
    # Process all files
    process_all_summary_files()
    
    # Ask if user wants to preview a result
    try:
        output_files = glob.glob(os.path.join(OUTPUT_PATH, "*_summaries_only.json"))
        if output_files:
            print(f"\n=== Preview ===")
            preview_structure(output_files[0], max_items=2)
    except Exception as e:
        print(f"Could not preview results: {str(e)}")
        
    print("\n=== Complete ===")
    print("All files have been processed!")
    print(f"Source files: {DIRECTORY_PATH}")
    print(f"Output files saved in: {OUTPUT_PATH}")