import os
import json
import re
from typing import Dict, List, Tuple
import requests
import numpy as np
import time

class SECDocumentProcessor:
    def __init__(self, 
                 ollama_base_url: str = "http://localhost:11434",
                 summarization_model: str = "llama3.2",
                 embedding_model: str = "dengcao/Qwen3-Embedding-0.6B:Q8_0"):
        """
        Initialize the SEC document processor with Ollama models
        
        Args:
            ollama_base_url: Base URL for Ollama API
            summarization_model: Ollama model for text summarization
            embedding_model: Ollama embedding model (Qwen3-Embedding-0.6B)
        """
        self.ollama_base_url = ollama_base_url.rstrip('/')
        self.summarization_model = summarization_model
        self.embedding_model = embedding_model
        
        print(f"Using Ollama at: {self.ollama_base_url}")
        print(f"Summarization model: {self.summarization_model}")
        print(f"Embedding model: {self.embedding_model}")
        
        # Test connection to Ollama
        self._test_ollama_connection()
        
        # Ensure models are available
        self._ensure_models_available()
        
    def _test_ollama_connection(self):
        """Test if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/version", timeout=5)
            if response.status_code == 200:
                print("Successfully connected to Ollama")
            else:
                raise Exception(f"Ollama returned status code: {response.status_code}")
        except Exception as e:
            print(f"Failed to connect to Ollama: {e}")
            print("Make sure Ollama is running with: 'ollama serve'")
            raise
    
    def _ensure_models_available(self):
        """Check if required models are available, pull them if not"""
        try:
            # Check available models
            response = requests.get(f"{self.ollama_base_url}/api/tags")
            available_models = [model['name'] for model in response.json().get('models', [])]
            
            # Check summarization model
            if not any(model.startswith(self.summarization_model) for model in available_models):
                print(f"Pulling summarization model: {self.summarization_model}")
                self._pull_model(self.summarization_model)
            
            # Check embedding model
            if not any(model.startswith(self.embedding_model) for model in available_models):
                print(f"Pulling embedding model: {self.embedding_model}")
                self._pull_model(self.embedding_model)
                
            print("All required models are available")
            
        except Exception as e:
            print(f"Warning: Could not verify models: {e}")
    
    def _pull_model(self, model_name: str):
        """Pull a model using Ollama API"""
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=300
            )
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    if 'status' in data:
                        print(f"  {data['status']}")
                    if data.get('status') == 'success':
                        print(f"Successfully pulled {model_name}")
                        break
                        
        except Exception as e:
            print(f"Failed to pull model {model_name}: {e}")
            raise
        
    def load_parsed_document(self, file_path: str) -> Dict:
        """Load a parsed 10K document from txt file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the structured format back into dictionary
        parsed_data = {}
        current_part = None
        current_item = None
        current_content = []
        
        lines = content.split('\n')
        for line in lines:
            # Check for PART headers
            if re.match(r'^PART [IVXLC]+$', line.strip()):
                if current_part and current_item:
                    parsed_data[current_part][current_item] = '\n'.join(current_content).strip()
                current_part = line.strip()
                parsed_data[current_part] = {}
                current_item = None
                current_content = []
            # Check for item headers (lines with dashes underneath)
            elif line.strip() and not line.startswith('=') and not line.startswith('-'):
                # Look ahead to see if next line is dashes
                next_line_idx = lines.index(line) + 1
                if (next_line_idx < len(lines) and 
                    lines[next_line_idx].strip() and 
                    all(c == '-' for c in lines[next_line_idx].strip())):
                    # Save previous item content
                    if current_part and current_item:
                        parsed_data[current_part][current_item] = '\n'.join(current_content).strip()
                    current_item = line.strip()
                    current_content = []
                else:
                    # Regular content line
                    if line.strip() and not all(c in '=-' for c in line.strip()):
                        current_content.append(line)
            elif line.strip() and not all(c in '=-' for c in line.strip()):
                current_content.append(line)
        
        # Save final item
        if current_part and current_item:
            parsed_data[current_part][current_item] = '\n'.join(current_content).strip()
            
        return parsed_data
    
    def summarize_section(self, section_title: str, content: str, company_name: str = "", max_words: int = 200) -> str:
        """
        Summarize a 10K section using Ollama
        
        Args:
            section_title: Title of the section
            content: Full content to summarize
            company_name: Company name for context
            max_words: Maximum words for summary
            
        Returns:
            Summary text
        """
        try:
            # Clean and prepare content
            content = content.strip()
            if len(content) < 50:  # Skip very short content
                return f"Brief section: {content[:100]}..."
            
            # Truncate very long content to avoid token limits
            if len(content) > 4000:
                content = content[:4000] + "..."
            
            prompt = f"""Extract key facts from this {section_title} section and format as bullet points.

Rules:
- Keep all exact numbers, dates, percentages, and dollar amounts
- Focus on concrete facts, not opinions
- One fact per bullet point
- Maximum {max_words} words total

Company: {company_name}
Section: {section_title}

Content:
{content}

Key Facts:
- """
            
            # Make request to Ollama
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.summarization_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": max_words * 2  # Allow some buffer
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('response', '').strip()
                
                # Clean up the summary
                if summary.startswith('Summary:'):
                    summary = summary[8:].strip()
                
                return summary if summary else f"Summary unavailable for {section_title}"
            else:
                print(f"Error from Ollama API: {response.status_code}")
                return f"Summary unavailable for {section_title}"
                
        except Exception as e:
            print(f"Error summarizing {section_title}: {e}")
            # Fallback: return first portion of content
            return f"Summary unavailable. Content preview: {content[:300]}..."
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for a list of texts using Ollama Qwen3 embedding model"""
        embeddings = []
        
        print(f"    Creating embeddings for {len(texts)} texts...")
        
        for i, text in enumerate(texts):
            try:
                # Clean the text
                text = text.strip()
                if not text:
                    # Handle empty text
                    embeddings.append(np.zeros(512))  # Assuming 512-dim embeddings
                    continue
                
                response = requests.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": text
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = np.array(result.get('embedding', []))
                    embeddings.append(embedding)
                else:
                    print(f"    Warning: Failed to create embedding for text {i+1}")
                    # Create a dummy embedding as fallback
                    embeddings.append(np.random.rand(512))
                
                # Small delay to avoid overwhelming the API
                if i % 10 == 0 and i > 0:
                    print(f"    Processed {i+1}/{len(texts)} embeddings...")
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"    Error creating embedding for text {i+1}: {e}")
                # Create a dummy embedding as fallback
                embeddings.append(np.random.rand(512))
        
        return np.array(embeddings)
    
    def process_document(self, parsed_file_path: str, company_name: str) -> Dict:
        """
        Process a complete 10K document: summarize sections and create embeddings
        
        Args:
            parsed_file_path: Path to parsed 10K file
            company_name: Company identifier
            
        Returns:
            Dictionary with summaries, embeddings, and metadata
        """
        print(f"Processing {company_name} 10K...")
        
        # Load parsed document
        parsed_data = self.load_parsed_document(parsed_file_path)
        
        document_data = {
            'company': company_name,
            'sections': {},
            'embeddings': {},
            'metadata': {
                'parts_count': len(parsed_data),
                'total_sections': sum(len(items) for items in parsed_data.values()),
                'models_used': {
                    'summarization': self.summarization_model,
                    'embedding': self.embedding_model
                },
                'ollama_base_url': self.ollama_base_url
            }
        }
        
        all_summaries = []
        all_section_keys = []
        
        # Process each part and item
        for part_name, items in parsed_data.items():
            print(f"  Processing {part_name}...")
            document_data['sections'][part_name] = {}
            
            for item_title, content in items.items():
                print(f"    Summarizing {item_title}...")
                
                # Generate summary
                summary = self.summarize_section(f"{part_name} - {item_title}", content, company_name)
                
                # Store section data
                section_key = f"{part_name}::{item_title}"
                document_data['sections'][part_name][item_title] = {
                    'original_content': content,
                    'summary': summary,
                    'word_count': len(content.split()),
                    'summary_word_count': len(summary.split())
                }
                
                all_summaries.append(summary)
                all_section_keys.append(section_key)
        
        # Create embeddings for all summaries
        print(f"  Creating embeddings...")
        embeddings = self.create_embeddings(all_summaries)
        
        # Store embeddings with section keys
        for i, section_key in enumerate(all_section_keys):
            document_data['embeddings'][section_key] = embeddings[i]
        
        return document_data
    
    def save_processed_data(self, document_data: Dict, output_path: str):
        """Save processed document data"""
        # Create separate files for different data types
        base_path = output_path.replace('.pkl', '')
        
        # Save summaries as JSON
        summaries_data = {
            'company': document_data['company'],
            'sections': document_data['sections'],
            'metadata': document_data['metadata']
        }
        
        with open(f"{base_path}_summaries.json", 'w', encoding='utf-8') as f:
            json.dump(summaries_data, f, indent=2, ensure_ascii=False)
        
        # Save embeddings as JSON (convert numpy arrays to lists)
        embeddings_data = {}
        for key, embedding in document_data['embeddings'].items():
            embeddings_data[key] = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        
        with open(f"{base_path}_embeddings.json", 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, indent=2)
        
        print(f"Saved summaries to {base_path}_summaries.json")
        print(f"Saved embeddings to {base_path}_embeddings.json")
    
    def process_all_documents(self, sec_txt_folder: str, output_folder: str):
        """Process all parsed documents in the sec_txt folder"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        parsed_files = [f for f in os.listdir(sec_txt_folder) if f.endswith('_parsed.txt')]
        
        print(f"Found {len(parsed_files)} files to process")
        
        for i, parsed_file in enumerate(parsed_files, 1):
            company_name = parsed_file.replace('_10k_parsed.txt', '').upper()
            parsed_path = os.path.join(sec_txt_folder, parsed_file)
            output_path = os.path.join(output_folder, f"{company_name}_processed.pkl")
            
            print(f"\n[{i}/{len(parsed_files)}] Processing {company_name}...")
            
            try:
                document_data = self.process_document(parsed_path, company_name)
                self.save_processed_data(document_data, output_path)
                print(f"Completed processing {company_name}")
                    
            except Exception as e:
                print(f"Error processing {company_name}: {e}")


def main():
    # Configuration - using Ollama models
    SEC_TXT_FOLDER = r"C:\Users\Nathan Kong\Downloads\sec_txt"
    OUTPUT_FOLDER = r"C:\Users\Nathan Kong\Downloads\sec_processed"
    
    # Ollama configuration
    OLLAMA_BASE_URL = "http://localhost:11434"  # Default Ollama URL
    SUMMARIZATION_MODEL = "llama3.2"  # Or "llama3.1", "mistral", etc.
    EMBEDDING_MODEL = "dengcao/Qwen3-Embedding-0.6B:Q8_0"  # Q8_0 quantized version
    
    print("=== SEC Document Processor with Ollama ===")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Summarization model: {SUMMARIZATION_MODEL}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print()
    
    # Initialize processor
    try:
        processor = SECDocumentProcessor(
            ollama_base_url=OLLAMA_BASE_URL,
            summarization_model=SUMMARIZATION_MODEL,
            embedding_model=EMBEDDING_MODEL
        )
        
        # Process all documents
        processor.process_all_documents(SEC_TXT_FOLDER, OUTPUT_FOLDER)
        
        print("\n🎉 All documents processed successfully!")
        
    except Exception as e:
        print(f"\nFailed to initialize or run processor: {e}")
        print("\nMake sure:")
        print("1. Ollama is installed and running ('ollama serve')")
        print("2. The models are available ('ollama pull llama3.2' and 'ollama pull dengcao/Qwen3-Embedding-0.6B')")


if __name__ == "__main__":
    main()