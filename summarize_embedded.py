import os
import json
import re
from typing import Dict, List, Tuple
import requests
import numpy as np
import pickle

class SECDocumentReasoner:
    def __init__(self, ollama_url: str = "http://localhost:11434", embedding_model: str = "gemma3:1b"):
        """
        Initialize the SEC document reasoner for contextual analysis
        
        Args:
            ollama_url: Ollama server URL for reasoning and embeddings
            embedding_model: Ollama model for embeddings (gemma3:1b)
        """
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model
        
    def load_condensed_summaries(self, file_path: str) -> Dict:
        """Load condensed summaries from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def chunk_summaries(self, all_summaries: str, chunk_size: int = 6000) -> List[str]:
        """
        Split summaries into chunks for processing
        
        Args:
            all_summaries: Combined summaries text
            chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(all_summaries) <= chunk_size:
            return [all_summaries]
        
        chunks = []
        sections = all_summaries.split('=== ')
        current_chunk = ""
        
        for section in sections:
            if not section.strip():
                continue
                
            section_text = f"=== {section}" if section != sections[0] else section
            
            if len(current_chunk + section_text) <= chunk_size:
                current_chunk += section_text
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section_text
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def generate_reasoning_for_chunk(self, company: str, chunk: str, chunk_num: int, total_chunks: int, max_tokens: int = 1000) -> str:
        """
        Generate reasoning for a single chunk focusing on specific analysis points
        
        Args:
            company: Company ticker
            chunk: Text chunk to analyze
            chunk_num: Current chunk number (1-indexed)
            total_chunks: Total number of chunks
            max_tokens: Maximum tokens for reasoning
            
        Returns:
            Reasoning analysis text for this chunk
        """
        chunk_focus = ""
        if chunk_num == 1:
            chunk_focus = "Focus primarily on: Business Model Analysis and Financial Health Assessment"
        elif chunk_num == 2:
            chunk_focus = "Focus primarily on: Risk Assessment and Growth Opportunities"
        else:
            chunk_focus = "Focus on: Investment Thesis and synthesis of previous analysis"
        
        prompt = f"""
        Based on this portion of the comprehensive 10-K filing summaries for {company} (Part {chunk_num} of {total_chunks}), provide detailed analysis that includes:
        
        1. **Business Model Analysis**: How does this company make money and what are their core competitive advantages?
        2. **Financial Health Assessment**: What do the financial metrics and performance indicators tell us?
        3. **Risk Assessment**: What are the most significant risks facing this company?
        4. **Growth Opportunities**: What potential growth drivers and strategic initiatives are mentioned?
        5. **Investment Thesis**: Based on available information, what would be key investment considerations?
        
        {chunk_focus}
        
        Please provide specific, actionable insights that synthesize information rather than just repeating bullet points.
        
        Company: {company}
        10-K Summary Data (Part {chunk_num}/{total_chunks}):
        {chunk}
        
        Analysis for Part {chunk_num}:
        """
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "gemma3:1b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "num_predict": max_tokens
                    }
                }
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except Exception as e:
            print(f"Error generating reasoning for {company} chunk {chunk_num}: {e}")
            return f"Analysis unavailable for chunk {chunk_num}"

    def generate_reasoning(self, company: str, all_summaries: str, max_tokens: int = 1000) -> str:
        """
        Generate contextual reasoning based on all company summaries using chunking
        
        Args:
            company: Company ticker
            all_summaries: Combined summaries from all sections
            max_tokens: Maximum tokens for reasoning per chunk
            
        Returns:
            Combined reasoning analysis text
        """
        chunks = self.chunk_summaries(all_summaries)
        print(f"  Processing {len(chunks)} chunks for comprehensive analysis...")
        
        chunk_analyses = []
        for i, chunk in enumerate(chunks, 1):
            print(f"    Analyzing chunk {i}/{len(chunks)}...")
            analysis = self.generate_reasoning_for_chunk(company, chunk, i, len(chunks), max_tokens)
            chunk_analyses.append(f"=== ANALYSIS PART {i} ===\n{analysis}")
        
        # Generate final synthesis if multiple chunks
        if len(chunks) > 1:
            print(f"    Creating final synthesis...")
            combined_analysis = "\n\n".join(chunk_analyses)
            synthesis_prompt = f"""
            Based on the following multi-part analysis of {company}, create a comprehensive final synthesis that covers all 5 key areas:
            
            1. **Business Model Analysis**: Complete overview of how the company makes money
            2. **Financial Health Assessment**: Overall financial position and performance
            3. **Risk Assessment**: All significant risks identified
            4. **Growth Opportunities**: All growth drivers and strategic initiatives
            5. **Investment Thesis**: Final recommendation based on complete analysis
            
            Previous Analysis Parts:
            {combined_analysis[:7000]}
            
            Comprehensive Final Analysis:
            """
            
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "gemma3:1b",
                        "prompt": synthesis_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": max_tokens * 2
                        }
                    }
                )
                response.raise_for_status()
                final_synthesis = response.json()["response"].strip()
                return f"{combined_analysis}\n\n=== COMPREHENSIVE SYNTHESIS ===\n{final_synthesis}"
            except Exception as e:
                print(f"Error generating final synthesis for {company}: {e}")
                return combined_analysis
        else:
            return chunk_analyses[0]
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for a list of texts using Ollama"""
        embeddings = []
        for text in texts:
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
            except Exception as e:
                print(f"Error creating embedding: {e}")
                # Return a zero vector as fallback
                embeddings.append([0.0] * 384)  # Typical embedding dimension
        return np.array(embeddings)
    
    def process_condensed_document(self, condensed_file_path: str, company_name: str) -> Dict:
        """
        Process condensed summaries and generate contextual reasoning
        
        Args:
            condensed_file_path: Path to condensed summaries JSON file
            company_name: Company identifier
            
        Returns:
            Dictionary with reasoning analysis and metadata
        """
        print(f"Generating reasoning for {company_name}...")
        
        # Load condensed summaries
        condensed_data = self.load_condensed_summaries(condensed_file_path)
        
        # Combine all summaries into one context
        all_summaries_text = ""
        section_count = 0
        
        for part_name, items in condensed_data['sections'].items():
            all_summaries_text += f"\n\n=== {part_name} ===\n"
            for item_title, item_data in items.items():
                all_summaries_text += f"\n--- {item_title} ---\n"
                all_summaries_text += item_data['summary'] + "\n"
                section_count += 1
        
        # Generate contextual reasoning
        print(f"  Analyzing {section_count} sections for comprehensive reasoning...")
        reasoning_analysis = self.generate_reasoning(company_name, all_summaries_text)
        
        # Create embeddings for the full reasoning
        print(f"  Creating embeddings for reasoning analysis...")
        reasoning_embedding = self.create_embeddings([reasoning_analysis])[0]
        
        reasoning_data = {
            'company': company_name,
            'reasoning_analysis': reasoning_analysis,
            'reasoning_embedding': reasoning_embedding,
            'source_sections': section_count,
            'metadata': {
                'generated_timestamp': str(os.path.getctime(condensed_file_path)),
                'source_file': condensed_file_path,
                'reasoning_word_count': len(reasoning_analysis.split())
            }
        }
        
        return reasoning_data
    
    def save_reasoning_data(self, reasoning_data: Dict, output_path: str):
        """Save reasoning analysis data"""
        base_path = output_path.replace('.json', '')
        
        # Save reasoning analysis as JSON (without embeddings for readability)
        reasoning_json = {
            'company': reasoning_data['company'],
            'reasoning_analysis': reasoning_data['reasoning_analysis'],
            'source_sections': reasoning_data['source_sections'],
            'metadata': reasoning_data['metadata']
        }
        
        with open(f"{base_path}_reasoning.json", 'w', encoding='utf-8') as f:
            json.dump(reasoning_json, f, indent=2, ensure_ascii=False)
        
        # Save reasoning embedding as pickle
        with open(f"{base_path}_reasoning_embedding.pkl", 'wb') as f:
            pickle.dump(reasoning_data['reasoning_embedding'], f)
        
        print(f"✅ Saved reasoning analysis to {base_path}_reasoning.json")
        print(f"✅ Saved reasoning embedding to {base_path}_reasoning_embedding.pkl")
    
    def process_all_condensed_documents(self, condensed_folder: str, output_folder: str):
        """Process all condensed summary files and generate reasoning"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        condensed_files = [f for f in os.listdir(condensed_folder) if f.endswith('_summaries_only.json')]
        
        for condensed_file in condensed_files:
            company_name = condensed_file.replace('_processed_summaries_summaries_only.json', '').upper()
            condensed_path = os.path.join(condensed_folder, condensed_file)
            output_path = os.path.join(output_folder, f"{company_name}_analysis.json")
            
            try:
                reasoning_data = self.process_condensed_document(condensed_path, company_name)
                self.save_reasoning_data(reasoning_data, output_path)
                print(f"✅ Completed reasoning analysis for {company_name}\n")
            except Exception as e:
                print(f"❌ Error processing {company_name}: {e}\n")


def main():
    # Configuration
    OLLAMA_URL = "http://localhost:11434"  # Ollama server URL
    CONDENSED_FOLDER = r"C:\Users\Nathan Kong\Downloads\condensed_files"
    OUTPUT_FOLDER = r"C:\Users\Nathan Kong\Downloads\finished_reasoning"
    
    # Initialize reasoner
    reasoner = SECDocumentReasoner(OLLAMA_URL)
    
    # Process all condensed documents and generate reasoning
    reasoner.process_all_condensed_documents(CONDENSED_FOLDER, OUTPUT_FOLDER)


if __name__ == "__main__":
    main()