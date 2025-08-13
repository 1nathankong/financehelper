import json
import re
import os

# Directory paths
INPUT_PATH = r"C:\Users\Nathan Kong\Downloads\finished_reasoning"
OUTPUT_PATH = r"C:\Users\Nathan Kong\Downloads\structured_reasoning"

def extract_bold_sections(text):
    """
    Extract and organize bold formatted sections from analysis text
    """
    if not isinstance(text, str):
        return {}
    
    sections = {}
    
    # Pattern to match section headers like **1. Business Model Analysis**
    section_pattern = r'\*\*(\d+\.\s*[^*]+?)\*\*'
    section_matches = list(re.finditer(section_pattern, text))
    
    # Extract major sections
    for i, match in enumerate(section_matches):
        section_title = match.group(1).strip()
        start_pos = match.end()
        
        # Find the end of this section (start of next section or end of text)
        if i + 1 < len(section_matches):
            end_pos = section_matches[i + 1].start()
        else:
            end_pos = len(text)
        
        section_content = text[start_pos:end_pos].strip()
        
        # Parse subsections within this section
        subsections = extract_bold_subsections(section_content)
        
        sections[section_title] = {
            "full_content": section_content,
            "subsections": subsections,
            "key_points": extract_bullet_points(section_content),
            "metrics": extract_financial_metrics(section_content)
        }
    
    return sections

def extract_bold_subsections(text):
    """
    Extract bold subsections like **Core Revenue Streams:**
    """
    subsections = {}
    
    # Pattern for subsections (bold text ending with colon)
    subsection_pattern = r'\*\*([^*]+?):\*\*'
    subsection_matches = list(re.finditer(subsection_pattern, text))
    
    for i, match in enumerate(subsection_matches):
        subsection_title = match.group(1).strip()
        start_pos = match.end()
        
        # Find content until next subsection or reasonable break
        if i + 1 < len(subsection_matches):
            end_pos = subsection_matches[i + 1].start()
        else:
            # Look for next major break (double newline or end)
            next_break = text.find('\n\n', start_pos)
            end_pos = next_break if next_break != -1 else len(text)
        
        content = text[start_pos:end_pos].strip()
        
        # Clean up content
        content = re.sub(r'^\s*', '', content)  # Remove leading whitespace
        content = re.sub(r'\s*$', '', content)  # Remove trailing whitespace
        
        if content:
            subsections[subsection_title] = {
                "content": content,
                "bullet_points": extract_bullet_points(content),
                "key_terms": extract_key_terms(content)
            }
    
    return subsections

def extract_bullet_points(text):
    """
    Extract bullet points and nested lists
    """
    bullet_points = []
    
    # Pattern for different bullet types
    patterns = [
        r'^\s*\*\s*\*\*([^*]+?)\*\*:\s*(.+?)(?=^\s*\*|\Z)',  # * **Bold**: content
        r'^\s*\*\s*\*\*([^*]+?)\*\*\s*(.+?)(?=^\s*\*|\Z)',   # * **Bold** content
        r'^\s*\*\s*([^*\n]+?)(?=^\s*\*|\Z)',                 # * regular bullet
        r'^\s*•\s*([^•\n]+?)(?=^\s*•|\Z)',                   # • bullet
        r'^\s*-\s*([^-\n]+?)(?=^\s*-|\Z)',                   # - bullet
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
        for match in matches:
            if len(match.groups()) == 2:  # Bold title with content
                bullet_points.append({
                    "type": "bold_bullet",
                    "title": match.group(1).strip(),
                    "content": match.group(2).strip()
                })
            else:  # Regular bullet
                bullet_points.append({
                    "type": "regular_bullet",
                    "content": match.group(1).strip()
                })
    
    return bullet_points

def extract_financial_metrics(text):
    """
    Extract financial data, percentages, and monetary values
    """
    metrics = {}
    
    # Dollar amounts
    dollar_pattern = r'\$(\d+(?:,\d+)*(?:\.\d+)?)\s*(billion|million|thousand|B|M|K)?'
    dollar_matches = re.findall(dollar_pattern, text, re.IGNORECASE)
    if dollar_matches:
        metrics['dollar_amounts'] = [f"${amount}{' ' + unit if unit else ''}" for amount, unit in dollar_matches]
    
    # Percentages
    percentage_pattern = r'(\d+(?:\.\d+)?%)'
    percentages = re.findall(percentage_pattern, text)
    if percentages:
        metrics['percentages'] = percentages
    
    # Years
    year_pattern = r'(20\d{2})'
    years = re.findall(year_pattern, text)
    if years:
        metrics['years'] = list(set(years))  # Remove duplicates
    
    # Growth/decrease indicators
    growth_pattern = r'(increased?|decreased?|grown?|declined?)\s+(?:by\s+)?(\d+(?:\.\d+)?%?)'
    growth_matches = re.findall(growth_pattern, text, re.IGNORECASE)
    if growth_matches:
        metrics['growth_indicators'] = [f"{direction} {amount}" for direction, amount in growth_matches]
    
    return metrics

def extract_key_terms(text):
    """
    Extract important business terms and concepts
    """
    # Common business/financial terms to look for
    business_terms = [
        'revenue', 'profit', 'margin', 'cash flow', 'debt', 'equity',
        'market share', 'competition', 'growth', 'expansion', 'innovation',
        'technology', 'manufacturing', 'supply chain', 'brand', 'customer',
        'regulatory', 'risk', 'opportunity', 'investment', 'valuation'
    ]
    
    found_terms = []
    text_lower = text.lower()
    
    for term in business_terms:
        if term in text_lower:
            # Find context around the term
            pattern = rf'([^.!?]*{re.escape(term)}[^.!?]*[.!?])'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_terms.append({
                    "term": term,
                    "contexts": matches[:2]  # First 2 contexts
                })
    
    return found_terms

def parse_analysis_sections(text):
    """
    Parse the entire analysis text and organize by sections
    """
    # Split by major analysis parts
    parts = re.split(r'=== ANALYSIS PART \d+ ===|=== COMPREHENSIVE SYNTHESIS ===', text)
    
    organized_content = {}
    
    for i, part in enumerate(parts):
        if not part.strip():
            continue
            
        part_name = f"Analysis_Part_{i}" if i > 0 else "Introduction"
        
        # Extract bold sections from this part
        bold_sections = extract_bold_sections(part)
        
        organized_content[part_name] = {
            "raw_content": part.strip(),
            "bold_sections": bold_sections,
            "overall_metrics": extract_financial_metrics(part),
            "word_count": len(part.split()),
            "key_topics": extract_analysis_topics(part)
        }
    
    return organized_content

def extract_analysis_topics(text):
    """
    Extract main topics being discussed
    """
    topics = []
    
    # Look for common analysis topics
    topic_patterns = [
        r'Business Model',
        r'Financial Health',
        r'Risk Assessment',
        r'Growth Opportunities',
        r'Investment Thesis',
        r'Competitive Advantage',
        r'Revenue Stream',
        r'Market Position'
    ]
    
    for pattern in topic_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            topics.append(pattern)
    
    return topics

def process_analysis_file(file_path):
    """
    Process a single analysis file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get the reasoning analysis text
        reasoning_text = data.get('reasoning_analysis', '')
        
        if not reasoning_text:
            print(f"No reasoning_analysis found in {file_path}")
            return None, 0
        
        # Parse the analysis
        organized_analysis = parse_analysis_sections(reasoning_text)
        
        # Create structured output
        structured_data = {
            "company": data.get("company", "Unknown"),
            "original_metadata": data.get("metadata", {}),
            "structured_analysis": organized_analysis,
            "analysis_summary": {
                "total_parts": len(organized_analysis),
                "total_word_count": sum(part.get("word_count", 0) for part in organized_analysis.values()),
                "major_topics": list(set([topic for part in organized_analysis.values() 
                                        for topic in part.get("key_topics", [])]))
            }
        }
        
        return structured_data, len(organized_analysis)
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return None, 0

def process_all_analysis_files():
    """
    Find and process all analysis files
    """
    # Create output directory
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)
        print(f"📁 Created output directory: {OUTPUT_PATH}")
    
    # Find analysis files (looking for files with "analysis" or "reasoning" in name)
    analysis_files = []
    for file in os.listdir(INPUT_PATH):
        if ('analysis' in file.lower() or 'reasoning' in file.lower()) and file.endswith('.json'):
            analysis_files.append(os.path.join(INPUT_PATH, file))
    
    if not analysis_files:
        print(f"No analysis files found in: {INPUT_PATH}")
        return
    
    print(f"Found {len(analysis_files)} analysis files to process:")
    for file in analysis_files:
        print(f"  - {os.path.basename(file)}")
    
    # Process each file
    for input_file in analysis_files:
        filename = os.path.basename(input_file)
        print(f"\nProcessing: {filename}")
        
        structured_data, parts_count = process_analysis_file(input_file)
        
        if structured_data is None:
            print(f"  ❌ Failed to process {filename}")
            continue
        
        # Create output filename
        base_name = filename.replace('.json', '')
        output_filename = f"{base_name}_structured.json"
        output_file = os.path.join(OUTPUT_PATH, output_filename)
        
        try:
            # Save structured file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
            
            print(f"  ✅ Created: {output_filename}")
            print(f"     📊 Processed {parts_count} analysis parts")
            print(f"     📈 Total word count: {structured_data['analysis_summary']['total_word_count']}")
            print(f"     🎯 Major topics: {', '.join(structured_data['analysis_summary']['major_topics'])}")
            
        except Exception as e:
            print(f"  ❌ Error saving {output_filename}: {str(e)}")

def preview_structured_analysis(file_path):
    """
    Preview the structured analysis
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n=== Preview of {os.path.basename(file_path)} ===")
        print(f"Company: {data.get('company', 'Unknown')}")
        print(f"Analysis Parts: {data['analysis_summary']['total_parts']}")
        print(f"Total Words: {data['analysis_summary']['total_word_count']}")
        print(f"Major Topics: {', '.join(data['analysis_summary']['major_topics'])}")
        
        # Show first analysis part structure
        first_part = list(data['structured_analysis'].values())[0]
        print(f"\nFirst Part Structure:")
        print(f"  Bold Sections: {len(first_part.get('bold_sections', {}))}")
        
        # Show a few bold sections
        for i, (section_name, section_data) in enumerate(first_part.get('bold_sections', {}).items()):
            if i < 2:  # Show first 2 sections
                print(f"    📋 {section_name}")
                print(f"       Subsections: {len(section_data.get('subsections', {}))}")
                print(f"       Key Points: {len(section_data.get('key_points', []))}")
                if section_data.get('metrics'):
                    print(f"       Metrics: {list(section_data['metrics'].keys())}")
        
    except Exception as e:
        print(f"Error previewing: {str(e)}")

if __name__ == "__main__":
    print("=== Analysis File Bold Formatting Parser ===")
    print("This script will parse **bold formatted** sections in analysis files")
    print("and organize them into structured data.\n")
    
    process_all_analysis_files()
    
    # Show preview
    structured_files = [f for f in os.listdir(OUTPUT_PATH) if f.endswith("_structured.json")]
    if structured_files:
        preview_file = os.path.join(OUTPUT_PATH, structured_files[0])
        preview_structured_analysis(preview_file)
    
    print(f"\n=== Complete ===")
    print(f"📁 Structured files saved in: {OUTPUT_PATH}")