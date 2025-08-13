# SEC API-Based Consulting Analyzer
# Uses official SEC data.sec.gov APIs for clean, structured data access

import asyncio
import aiohttp
import requests
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import logging
from bs4 import BeautifulSoup
import time

# === SEC OFFICIAL API CLIENT ===

class SECOfficialAPI:
    """Client for official SEC data.sec.gov APIs"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.headers = {
            'User-Agent': 'ConsultingBot research@yourcompany.com',  # SEC requires identification
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Rate limiting - SEC allows 10 requests per second
        self.last_request_time = 0
        self.min_request_interval = 0.11
        
        # Cache for CIK lookups
        self.ticker_to_cik_cache = {}
        
        # Hardcoded database of notable company CIKs for efficient lookup
        self.hardcoded_ciks = {
            # Technology
            'AAPL': '0000320193',  # Apple Inc
            'MSFT': '0000789019',  # Microsoft Corporation
            'GOOGL': '0001652044', # Alphabet Inc Class A
            'GOOG': '0001652044',  # Alphabet Inc Class C
            'AMZN': '0001018724',  # Amazon.com Inc
            'META': '0001326801',  # Meta Platforms Inc
            'TSLA': '0001318605',  # Tesla Inc
            'NVDA': '0001045810',  # NVIDIA Corporation
            'NFLX': '0001065280',  # Netflix Inc
            'ADBE': '0000796343',  # Adobe Inc
            'CRM': '0001108524',   # Salesforce Inc
            'ORCL': '0001341439',  # Oracle Corporation
            'INTC': '0000050863',  # Intel Corporation
            'IBM': '0000051143',   # International Business Machines
            'CSCO': '0000858877',  # Cisco Systems Inc
            'UBER': '0001543151',  # Uber Technologies Inc
            'ZOOM': '0001585521',  # Zoom Video Communications
            'PTON': '0001639825',  # Peloton Interactive Inc
            'SPOT': '0001639920',  # Spotify Technology SA
            'SNAP': '0001564408',  # Snap Inc
            'TWTR': '0001418091',  # Twitter Inc (Legacy)
            'SQ': '0001512673',    # Block Inc (Square)
            'PYPL': '0001633917',  # PayPal Holdings Inc
            'AMD': '0000002488',   # Advanced Micro Devices
            
            # Financial Services
            'JPM': '0000019617',   # JPMorgan Chase & Co
            'BAC': '0000070858',   # Bank of America Corp
            'WFC': '0000072971',   # Wells Fargo & Company
            'GS': '0000886982',    # Goldman Sachs Group Inc
            'MS': '0000895421',    # Morgan Stanley
            'C': '0000831001',     # Citigroup Inc
            'V': '0001403161',     # Visa Inc
            'MA': '0001141391',    # Mastercard Inc
            'AXP': '0000004962',   # American Express Company
            'BLK': '0001364742',   # BlackRock Inc
            'COF': '0000927628',   # Capital One Financial Corp
            'SCHW': '0000316709',  # Charles Schwab Corporation
            
            # Healthcare & Pharmaceuticals
            'JNJ': '0000200406',   # Johnson & Johnson
            'UNH': '0000731766',   # UnitedHealth Group Inc
            'PFE': '0000078003',   # Pfizer Inc
            'ABBV': '0001551152',  # AbbVie Inc
            'MRK': '0000310158',   # Merck & Co Inc
            'TMO': '0000097745',   # Thermo Fisher Scientific
            'ABT': '0000001800',   # Abbott Laboratories
            'LLY': '0000059478',   # Eli Lilly and Company
            'BMY': '0000014272',   # Bristol Myers Squibb
            'AMGN': '0000318154',  # Amgen Inc
            'GILD': '0000882095',  # Gilead Sciences Inc
            'CVS': '0000064803',   # CVS Health Corporation
            
            # Consumer & Retail
            'WMT': '0000104169',   # Walmart Inc
            'PG': '0000080424',    # Procter & Gamble Company
            'KO': '0000021344',    # Coca-Cola Company
            'PEP': '0000077476',   # PepsiCo Inc
            'COST': '0000909832',  # Costco Wholesale Corp
            'NKE': '0000320187',   # Nike Inc
            'MCD': '0000063908',   # McDonald's Corporation
            'SBUX': '0000829224',  # Starbucks Corporation
            'TGT': '0000027419',   # Target Corporation
            'HD': '0000354950',    # Home Depot Inc
            'LOW': '0000060667',   # Lowe's Companies Inc
            'DIS': '0000001744',   # Walt Disney Company
            
            # Industrial & Manufacturing
            'BA': '0000012927',    # Boeing Company
            'CAT': '0000018230',   # Caterpillar Inc
            'GE': '0000040545',    # General Electric Company
            'MMM': '0000066740',   # 3M Company
            'HON': '0000773840',   # Honeywell International
            'UPS': '0001090727',   # United Parcel Service
            'FDX': '0000354950',   # FedEx Corporation
            'LMT': '0000936468',   # Lockheed Martin Corp
            'RTX': '0000101829',   # Raytheon Technologies
            'DE': '0000315189',    # Deere & Company
            
            # Energy & Utilities
            'XOM': '0000034088',   # Exxon Mobil Corporation
            'CVX': '0000093410',   # Chevron Corporation
            'COP': '0001163165',   # ConocoPhillips
            'SLB': '0000087347',   # Schlumberger NV
            'OXY': '0000797468',   # Occidental Petroleum
            'KMI': '0001506307',   # Kinder Morgan Inc
            'EPD': '0001061165',   # Enterprise Products Partners
            'NEE': '0000753308',   # NextEra Energy Inc
            'SO': '0000092122',    # Southern Company
            'DUK': '0001326160',   # Duke Energy Corporation
            
            # Real Estate & REITs
            'AMT': '0001053507',   # American Tower Corporation
            'PLD': '0001045609',   # Prologis Inc
            'CCI': '0001051470',   # Crown Castle International
            'EQIX': '0001101239',  # Equinix Inc
            'SPG': '0001063761',   # Simon Property Group
            'O': '0000726728',     # Realty Income Corporation
            
            # Telecommunications
            'VZ': '0000732712',    # Verizon Communications
            'T': '0000732717',     # AT&T Inc
            'TMUS': '0001283699',  # T-Mobile US Inc
            'CMCSA': '0001166691', # Comcast Corporation
            'CHTR': '0001091667',  # Charter Communications
            
            # Materials & Chemicals
            'LIN': '0001707925',   # Linde plc
            'APD': '0000002969',   # Air Products and Chemicals
            'SHW': '0000089800',   # Sherwin-Williams Company
            'ECL': '0000031462',   # Ecolab Inc
            'FCX': '0000831259',   # Freeport-McMoRan Inc
            'NEM': '0001164727',   # Newmont Corporation
            
            # Consumer Discretionary
            'AMZN': '0001018724',  # Amazon (also in tech)
            'TSLA': '0001318605',  # Tesla (also in tech)
            'GM': '0001467858',    # General Motors Company
            'F': '0000037996',     # Ford Motor Company
            'CCL': '0000815097',   # Carnival Corporation
            'RCL': '0000884887',   # Royal Caribbean Group
            'MAR': '0001048286',   # Marriott International
            'HLT': '0001585689',   # Hilton Worldwide Holdings
            
            # Software & Cloud
            'NOW': '0001373715',   # ServiceNow Inc
            'SNOW': '0001640147',  # Snowflake Inc
            'DDOG': '0001561550',  # Datadog Inc
            'ZM': '0001585521',    # Zoom Video (duplicate)
            'OKTA': '0001660134',  # Okta Inc
            'PLTR': '0001321655',  # Palantir Technologies
            'CRWD': '0001535527',  # CrowdStrike Holdings
            
            # Biotech & Life Sciences
            'BIIB': '0000875045',  # Biogen Inc
            'REGN': '0000872589',  # Regeneron Pharmaceuticals
            'VRTX': '0000617558',  # Vertex Pharmaceuticals
            'MRNA': '0001682852',  # Moderna Inc
            'BNTX': '0001776985',  # BioNTech SE
            
            # Semiconductors
            'TSM': '0001046179',   # Taiwan Semiconductor
            'ASML': '0000937966',  # ASML Holding NV
            'QCOM': '0000804328',  # Qualcomm Inc
            'AVGO': '0001730168',  # Broadcom Inc
            'TXN': '0000097476',   # Texas Instruments
            'MU': '0000723125',    # Micron Technology
            'LRCX': '0000707549',  # Lam Research Corp
            'AMAT': '0000006951',  # Applied Materials Inc
            
            # Airlines & Transportation
            'DAL': '0000027904',   # Delta Air Lines Inc
            'AAL': '0000006201',   # American Airlines Group
            'UAL': '0000100517',   # United Airlines Holdings
            'LUV': '0000092380',   # Southwest Airlines Co
            'JBLU': '0001158463',  # JetBlue Airways Corp
            
            # Gaming & Entertainment
            'NFLX': '0001065280',  # Netflix (duplicate)
            'DIS': '0001001039',   # Disney (duplicate)
            'EA': '0000712515',    # Electronic Arts Inc
            'ATVI': '0000718877',  # Activision Blizzard
            'TTWO': '0000946581',  # Take-Two Interactive
            'ROKU': '0001594948',  # Roku Inc
        }
    
    def _rate_limit(self):
        """Ensure compliance with SEC rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def get_company_cik(self, ticker: str) -> Optional[str]:
        """Get CIK (Central Index Key) for a ticker symbol"""
        
        ticker_upper = ticker.upper()
        
        # Check cache first
        if ticker_upper in self.ticker_to_cik_cache:
            return self.ticker_to_cik_cache[ticker_upper]
        
        # Check hardcoded database for instant lookup
        if ticker_upper in self.hardcoded_ciks:
            cik = self.hardcoded_ciks[ticker_upper]
            self.ticker_to_cik_cache[ticker_upper] = cik
            print(f"Found {ticker_upper} in hardcoded database: {cik}")
            return cik
        
        print(f"Looking up CIK for {ticker_upper} via SEC API...")
        
        # Use company tickers JSON file for lookup as fallback
        self._rate_limit()
        
        try:
            # SEC provides a JSON file with all company tickers
            tickers_url = f"{self.base_url}/files/company_tickers.json"
            response = self.session.get(tickers_url)
            response.raise_for_status()
            
            tickers_data = response.json()
            
            # Find matching ticker
            for entry in tickers_data.values():
                if entry.get('ticker', '').upper() == ticker_upper:
                    cik = str(entry['cik_str']).zfill(10)  # Pad with leading zeros
                    self.ticker_to_cik_cache[ticker_upper] = cik
                    print(f"   Found CIK via SEC API: {cik}")
                    return cik
            
            print(f"   Ticker {ticker_upper} not found in SEC database")
            return None
            
        except Exception as e:
            print(f"   Error looking up CIK via SEC API: {e}")
            return None
    
    def get_company_submissions(self, cik: str) -> Dict[str, Any]:
        """Get company filing submissions using official API"""
        
        print(f"Fetching submissions for CIK {cik}...")
        
        self._rate_limit()
        
        try:
            # Official SEC submissions API
            submissions_url = f"{self.base_url}/submissions/CIK{cik}.json"
            response = self.session.get(submissions_url)
            response.raise_for_status()
            
            submissions_data = response.json()
            
            print(f"   Retrieved {len(submissions_data.get('filings', {}).get('recent', {}).get('form', []))} recent filings")
            
            return submissions_data
            
        except Exception as e:
            print(f"   Error fetching submissions: {e}")
            return {}
    
    def get_recent_filings(self, cik: str, form_types: List[str] = ['10-K', '10-Q'], limit: int = 5) -> List[Dict]:
        """Get recent filings of specific types"""
        
        submissions = self.get_company_submissions(cik)
        if not submissions:
            return []
        
        recent_filings = submissions.get('filings', {}).get('recent', {})
        
        if not recent_filings:
            return []
        
        # Extract filing arrays
        forms = recent_filings.get('form', [])
        filing_dates = recent_filings.get('filingDate', [])
        accession_numbers = recent_filings.get('accessionNumber', [])
        primary_documents = recent_filings.get('primaryDocument', [])
        
        # Find matching form types
        filtered_filings = []
        
        for i, form in enumerate(forms):
            if form in form_types and len(filtered_filings) < limit:
                filing_info = {
                    'form_type': form,
                    'filing_date': filing_dates[i] if i < len(filing_dates) else '',
                    'accession_number': accession_numbers[i] if i < len(accession_numbers) else '',
                    'primary_document': primary_documents[i] if i < len(primary_documents) else '',
                    'cik': cik
                }
                
                # Build document URLs
                accession_clean = filing_info['accession_number'].replace('-', '')
                filing_info['document_url'] = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{filing_info['primary_document']}"
                filing_info['txt_url'] = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{filing_info['accession_number']}.txt"
                
                filtered_filings.append(filing_info)
        
        print(f"   Found {len(filtered_filings)} {'/'.join(form_types)} filings")
        
        return filtered_filings
    
    def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """Get company facts (financial data) using official API"""
        
        print(f"Fetching company facts for CIK {cik}...")
        
        self._rate_limit()
        
        try:
            # Official company facts API
            facts_url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik}.json"
            response = self.session.get(facts_url)
            response.raise_for_status()
            
            facts_data = response.json()
            
            print(f"   Retrieved financial facts")
            return facts_data
            
        except Exception as e:
            print(f"   Company facts not available: {e}")
            return {}

# === SMART DOCUMENT ANALYZER ===

class SECDocumentAnalyzer:
    """Analyze SEC documents downloaded via official API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ConsultingBot research@yourcompany.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
    
    def download_filing_text(self, filing_url: str) -> str:
        """Download and clean filing text"""
        
        print(f"Downloading filing content...")
        
        try:
            response = self.session.get(filing_url)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unnecessary elements
            for element in soup(['script', 'style', 'table', 'img']):
                element.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean up text
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r'\s+', ' ', text)
            
            print(f"   Downloaded {len(text):,} characters")
            return text.strip()
            
        except Exception as e:
            print(f"   Error downloading filing: {e}")
            return ""
    
    def extract_key_sections(self, filing_text: str) -> Dict[str, str]:
        """Extract key business sections from filing"""
        
        print("Extracting key sections...")
        
        # Define section patterns for different types of content
        section_patterns = {
            'business_overview': [
                r'(?i)item\s*1\.?\s*business\b',
                r'(?i)item\s*1\.?\s*general\b',
                r'(?i)\bbusiness\s*overview\b',
                r'(?i)\bour\s*business\b'
            ],
            'risk_factors': [
                r'(?i)item\s*1a\.?\s*risk\s*factors\b',
                r'(?i)\brisk\s*factors\b',
                r'(?i)\bprincipal\s*risks\b'
            ],
            'financial_performance': [
                r'(?i)item\s*7\.?\s*management.s?\s*discussion\s*and\s*analysis\b',
                r'(?i)\bmd&a\b',
                r'(?i)\bresults\s*of\s*operations\b'
            ],
            'liquidity_capital': [
                r'(?i)\bliquidity\s*and\s*capital\s*resources\b',
                r'(?i)\bfinancial\s*condition\b',
                r'(?i)\bcash\s*flows?\b'
            ],
            'controls_procedures': [
                r'(?i)item\s*9a\.?\s*controls\s*and\s*procedures\b',
                r'(?i)\binternal\s*control\b',
                r'(?i)\bdisclosure\s*controls\b'
            ]
        }
        
        sections = {}
        
        for section_name, patterns in section_patterns.items():
            section_text = self._find_section_by_patterns(filing_text, patterns)
            if section_text:
                sections[section_name] = section_text
                print(f"   Extracted {section_name}: {len(section_text):,} chars")
            else:
                print(f"   {section_name}: not found")
        
        return sections
    
    def _find_section_by_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """Find section text using multiple patterns"""
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._extract_section_text(text, match)
        
        return None
    
    def _extract_section_text(self, text: str, start_match) -> str:
        """Extract section text from start point to next major section"""
        
        start_pos = start_match.start()
        
        # Look for next major section (Item X)
        next_section_pattern = r'(?i)\bitem\s*\d+[a-z]?\.?\s'
        next_match = re.search(next_section_pattern, text[start_pos + 200:])
        
        if next_match:
            end_pos = start_pos + 200 + next_match.start()
            section_text = text[start_pos:end_pos]
        else:
            # Take next 12k characters if no next section
            section_text = text[start_pos:start_pos + 12000]
        
        return section_text.strip()

# === GEMMA LLM ANALYZER ===

class GemmaConsultingAnalyzer:
    """Gemma-powered analyzer for SEC content"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma3:latest"):
        self.base_url = base_url
        self.model = model
        self.session = None
        
        self.default_options = {
            "temperature": 0.2,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_ctx": 6144,
            "num_predict": 700
        }
    
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120))
        return self.session
    
    async def generate(self, prompt: str, system_prompt: str = None, **options) -> str:
        """Generate response using Gemma"""
        
        session = await self._get_session()
        
        if system_prompt:
            full_prompt = f"<s>{system_prompt}</s>\n\n<user>{prompt}</user>\n\n<assistant>"
        else:
            full_prompt = prompt
        
        request_options = {**self.default_options, **options}
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "options": request_options,
            "stream": False
        }
        
        try:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "").strip()
                else:
                    return f"Error: {response.status}"
        except Exception as e:
            return f"Connection error: {str(e)}"
    
    async def analyze_comprehensive(self, company_ticker: str, sections: Dict[str, str], 
                                   company_facts: Dict[str, Any] = None) -> Dict[str, Any]:
        """Comprehensive analysis of all sections"""
        
        print("🤖 Running comprehensive AI analysis...")
        
        # Combine relevant sections for different analysis types
        business_text = self._combine_sections(sections, ['business_overview', 'risk_factors'])
        financial_text = self._combine_sections(sections, ['financial_performance', 'liquidity_capital'])
        
        analysis_results = {}
        
        # Analyze business problems
        if business_text:
            print("   🔍 Analyzing business challenges...")
            analysis_results['business_problems'] = await self._analyze_business_problems(
                business_text, company_ticker)
        
        # Analyze financial issues
        if financial_text:
            print("   💰 Analyzing financial challenges...")
            analysis_results['financial_issues'] = await self._analyze_financial_issues(
                financial_text, company_ticker, company_facts)
        
        # Analyze transformation needs
        if business_text or financial_text:
            print("   🚀 Identifying transformation opportunities...")
            combined_text = business_text + "\n\n" + financial_text
            analysis_results['transformation_needs'] = await self._analyze_transformation_needs(
                combined_text, company_ticker)
        
        # Analyze urgent priorities
        risk_text = sections.get('risk_factors', '')
        if risk_text:
            print("   🚨 Identifying urgent priorities...")
            analysis_results['urgent_priorities'] = await self._analyze_urgent_priorities(
                risk_text, company_ticker)
        
        # Generate opportunity summary
        print("   📊 Generating opportunity summary...")
        opportunity_summary = await self._generate_opportunity_summary(
            company_ticker, analysis_results, company_facts)
        
        return {
            'company_ticker': company_ticker,
            'analysis_date': datetime.now().isoformat(),
            'sections_analyzed': list(sections.keys()),
            'business_problems': analysis_results.get('business_problems', []),
            'financial_issues': analysis_results.get('financial_issues', []),
            'transformation_needs': analysis_results.get('transformation_needs', []),
            'urgent_priorities': analysis_results.get('urgent_priorities', []),
            'opportunity_summary': opportunity_summary
        }
    
    def _combine_sections(self, sections: Dict[str, str], section_keys: List[str]) -> str:
        """Combine multiple sections into one text"""
        combined = []
        for key in section_keys:
            if key in sections and sections[key]:
                combined.append(sections[key])
        return "\n\n".join(combined)
    
    async def _analyze_business_problems(self, text: str, company_ticker: str) -> List[str]:
        """Extract business problems"""
        
        # Truncate if too long
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        system_prompt = "You are a business consultant identifying specific operational and strategic problems."
        
        user_prompt = f"""
Analyze {company_ticker}'s SEC filing content for specific business problems:

{text}

List concrete business problems that consulting firms could address:

BUSINESS_PROBLEMS:
- [specific operational challenge 1]
- [specific competitive issue 2]
- [specific market challenge 3]
- [specific strategic problem 4]

Focus on actionable problems, not general market conditions.
"""
        
        response = await self.generate(user_prompt, system_prompt)
        return self._extract_bullet_points(response, "BUSINESS_PROBLEMS:")
    
    async def _analyze_financial_issues(self, text: str, company_ticker: str, 
                                       facts: Dict[str, Any] = None) -> List[str]:
        """Extract financial issues"""
        
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        # Add financial facts context if available
        facts_context = ""
        if facts:
            facts_context = self._extract_key_financial_metrics(facts)
        
        system_prompt = "You are a financial consultant identifying specific financial challenges."
        
        user_prompt = f"""
Analyze {company_ticker}'s financial information for consulting opportunities:

SEC FILING CONTENT:
{text}

{facts_context}

Identify specific financial issues that consulting could address:

FINANCIAL_ISSUES:
- [specific cost/margin problem 1]
- [specific cash flow challenge 2]
- [specific capital allocation issue 3]
- [specific financial process inefficiency 4]

Focus on financial problems, not market conditions.
"""
        
        response = await self.generate(user_prompt, system_prompt)
        return self._extract_bullet_points(response, "FINANCIAL_ISSUES:")
    
    async def _analyze_transformation_needs(self, text: str, company_ticker: str) -> List[str]:
        """Extract transformation opportunities"""
        
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        system_prompt = "You are a transformation consultant identifying modernization opportunities."
        
        user_prompt = f"""
Analyze {company_ticker}'s SEC filing for transformation opportunities:

{text}

Identify transformation needs where consulting adds value:

TRANSFORMATION_NEEDS:
- [specific technology modernization need 1]
- [specific process improvement opportunity 2]
- [specific digital transformation requirement 3]
- [specific operational upgrade need 4]

Focus on concrete transformation projects.
"""
        
        response = await self.generate(user_prompt, system_prompt)
        return self._extract_bullet_points(response, "TRANSFORMATION_NEEDS:")
    
    async def _analyze_urgent_priorities(self, text: str, company_ticker: str) -> List[str]:
        """Extract urgent priorities from risk factors"""
        
        if len(text) > 4000:
            text = text[:4000] + "..."
        
        system_prompt = "You are a crisis management consultant identifying urgent business priorities."
        
        user_prompt = f"""
Analyze {company_ticker}'s risk factors for urgent priorities:

{text}

Identify time-sensitive issues requiring immediate consulting attention:

URGENT_PRIORITIES:
- [urgent regulatory/compliance issue 1]
- [immediate operational problem 2]
- [time-critical strategic challenge 3]

Focus only on urgent, time-sensitive matters.
"""
        
        response = await self.generate(user_prompt, system_prompt)
        return self._extract_bullet_points(response, "URGENT_PRIORITIES:")
    
    async def _generate_opportunity_summary(self, company_ticker: str, 
                                          analysis: Dict[str, List[str]], 
                                          facts: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate comprehensive opportunity summary"""
        
        # Count total issues
        total_business = len(analysis.get('business_problems', []))
        total_financial = len(analysis.get('financial_issues', []))
        total_transformation = len(analysis.get('transformation_needs', []))
        total_urgent = len(analysis.get('urgent_priorities', []))
        
        # Create summary of findings
        findings_summary = f"""
Business Problems: {total_business} identified
Financial Issues: {total_financial} identified  
Transformation Needs: {total_transformation} identified
Urgent Priorities: {total_urgent} identified

Top Issues:
{'; '.join(analysis.get('business_problems', [])[:2])}
{'; '.join(analysis.get('financial_issues', [])[:2])}
{'; '.join(analysis.get('urgent_priorities', [])[:1])}
"""
        
        system_prompt = "You are a senior consulting partner evaluating opportunities."
        
        user_prompt = f"""
Assess the consulting opportunity for {company_ticker}:

{findings_summary}

Provide scores (1-10) and estimates:

OPPORTUNITY_SCORE: [1-10] - Overall attractiveness
PROJECT_VALUE: [1-10] - Potential project size
URGENCY: [1-10] - How urgent are their needs
COMPLEXITY: [1-10] - Engagement complexity

ESTIMATED_VALUE: $[amount] - Total consulting potential
TIMELINE: [months] - Expected sales cycle
FOCUS_AREAS: [top 2-3 consulting areas]

Be concise.
"""
        
        response = await self.generate(user_prompt, system_prompt, temperature=0.3)
        return self._parse_opportunity_summary(response, company_ticker, total_business + total_financial + total_urgent)
    
    def _extract_key_financial_metrics(self, facts: Dict[str, Any]) -> str:
        """Extract key financial metrics from company facts"""
        
        try:
            # Navigate the facts structure to find key metrics
            us_gaap = facts.get('facts', {}).get('us-gaap', {})
            
            metrics = []
            
            # Look for common financial metrics
            key_metrics = {
                'Revenues': 'revenues',
                'NetIncomeLoss': 'net_income',
                'Assets': 'total_assets',
                'Liabilities': 'total_liabilities',
                'CashAndCashEquivalentsAtCarryingValue': 'cash'
            }
            
            for gaap_key, display_name in key_metrics.items():
                if gaap_key in us_gaap:
                    metric_data = us_gaap[gaap_key]
                    # Get most recent value
                    if 'units' in metric_data and 'USD' in metric_data['units']:
                        recent_values = metric_data['units']['USD']
                        if recent_values:
                            latest = recent_values[-1]
                            value = latest.get('val', 0)
                            metrics.append(f"{display_name}: ${value:,}")
            
            if metrics:
                return f"\nKEY FINANCIAL METRICS:\n" + "\n".join(metrics) + "\n"
            
        except Exception as e:
            print(f"   ⚠️  Could not extract financial metrics: {e}")
        
        return ""
    
    def _extract_bullet_points(self, response: str, section_header: str) -> List[str]:
        """Extract bullet points from response"""
        
        points = []
        found_section = False
        
        for line in response.split('\n'):
            line = line.strip()
            
            if line.startswith(section_header):
                found_section = True
                continue
            
            if found_section and line.startswith('-'):
                point = line[1:].strip()
                if point and len(point) > 10:
                    points.append(point)
            elif found_section and line and not line.startswith('-'):
                break
        
        return points
    
    def _parse_opportunity_summary(self, response: str, company_ticker: str, total_issues: int) -> Dict[str, Any]:
        """Parse opportunity summary response"""
        
        # Extract scores
        patterns = {
            'opportunity_score': r'OPPORTUNITY_SCORE:\s*(\d+(?:\.\d+)?)',
            'project_value': r'PROJECT_VALUE:\s*(\d+(?:\.\d+)?)',
            'urgency': r'URGENCY:\s*(\d+(?:\.\d+)?)',
            'complexity': r'COMPLEXITY:\s*(\d+(?:\.\d+)?)'
        }
        
        scores = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, response)
            scores[key] = float(match.group(1)) if match else 5.0
        
        # Extract estimated value
        value_match = re.search(r'ESTIMATED_VALUE:\s*\$?([\d,]+(?:\.\d+)?[KM]?)', response, re.IGNORECASE)
        estimated_value = 500000
        
        if value_match:
            value_str = value_match.group(1).replace(',', '').upper()
            try:
                if 'K' in value_str:
                    estimated_value = float(value_str.replace('K', '')) * 1000
                elif 'M' in value_str:
                    estimated_value = float(value_str.replace('M', '')) * 1000000
                else:
                    estimated_value = float(value_str)
            except:
                pass
        
        # Extract timeline and focus areas
        timeline_match = re.search(r'TIMELINE:\s*(\d+)', response)
        timeline = int(timeline_match.group(1)) if timeline_match else 6
        
        focus_match = re.search(r'FOCUS_AREAS:\s*([^\n]+)', response)
        focus_areas = focus_match.group(1).strip() if focus_match else ""
        
        # Calculate overall score
        overall_score = (scores['opportunity_score'] * 0.4 + scores['urgency'] * 0.3 + scores['project_value'] * 0.3)
        
        return {
            'company': company_ticker,
            'overall_score': round(overall_score, 1),
            'individual_scores': scores,
            'estimated_value': estimated_value,
            'timeline_months': timeline,
            'focus_areas': focus_areas,
            'total_issues_found': total_issues,
            'analysis_quality': 'high' if total_issues >= 5 else 'medium' if total_issues >= 3 else 'low'
        }
    
    async def close(self):
        if self.session:
            await self.session.close()

# === COMPLETE SEC API PIPELINE ===

class SECAPIConsultingPipeline:
    """Complete pipeline using official SEC APIs"""
    
    def __init__(self, model: str = "gemma3:latest"):
        self.sec_api = SECOfficialAPI()
        self.doc_analyzer = SECDocumentAnalyzer()
        self.llm_analyzer = GemmaConsultingAnalyzer(model=model)
        self.db = self.setup_database()
    
    def setup_database(self):
        """Setup database for results"""
        conn = sqlite3.connect('sec_api_consulting.db')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_analyses (
                id INTEGER PRIMARY KEY,
                company_ticker TEXT,
                company_cik TEXT,
                filing_type TEXT,
                filing_date TEXT,
                analysis_date TEXT,
                business_problems TEXT,
                financial_issues TEXT,
                transformation_needs TEXT,
                urgent_priorities TEXT,
                opportunity_summary TEXT,
                total_issues INTEGER,
                overall_score REAL,
                estimated_value REAL,
                raw_data TEXT
            )
        ''')
        
        conn.commit()
        return conn
    
    async def analyze_company_complete(self, ticker: str) -> Dict[str, Any]:
        """Complete company analysis using SEC APIs"""
        
        print(f"🏢 SEC API Analysis for {ticker.upper()}")
        print("="*60)
        
        # Step 1: Get CIK
        cik = self.sec_api.get_company_cik(ticker)
        if not cik:
            return {"error": f"Could not find CIK for ticker {ticker}"}
        
        # Step 2: Get recent filings
        filings = self.sec_api.get_recent_filings(cik, ['10-K', '10-Q'], 2)
        if not filings:
            return {"error": f"No recent 10-K/10-Q filings found for {ticker}"}
        
        latest_filing = filings[0]
        print(f"📄 Analyzing {latest_filing['form_type']} from {latest_filing['filing_date']}")
        
        # Step 3: Get company financial facts (optional)
        company_facts = self.sec_api.get_company_facts(cik)
        
        # Step 4: Download and analyze filing
        filing_text = self.doc_analyzer.download_filing_text(latest_filing['document_url'])
        if not filing_text:
            return {"error": "Could not download filing content"}
        
        # Step 5: Extract key sections
        sections = self.doc_analyzer.extract_key_sections(filing_text)
        if not sections:
            return {"error": "Could not extract key sections from filing"}
        
        print(f"📋 Extracted {len(sections)} sections: {', '.join(sections.keys())}")
        
        # Step 6: AI analysis
        print("🤖 Running AI analysis...")
        analysis = await self.llm_analyzer.analyze_comprehensive(
            ticker.upper(), sections, company_facts)
        
        # Step 7: Compile final result
        final_result = {
            'company_ticker': ticker.upper(),
            'company_cik': cik,
            'filing_info': latest_filing,
            'sections_extracted': list(sections.keys()),
            'has_financial_facts': bool(company_facts),
            **analysis
        }
        
        # Store in database
        self._store_analysis(final_result)
        
        print("✅ SEC API analysis complete!")
        return final_result
    
    def _store_analysis(self, result: Dict[str, Any]):
        """Store analysis in database"""
        
        summary = result.get('opportunity_summary', {})
        
        self.db.execute('''
            INSERT INTO api_analyses 
            (company_ticker, company_cik, filing_type, filing_date, analysis_date,
             business_problems, financial_issues, transformation_needs, urgent_priorities,
             opportunity_summary, total_issues, overall_score, estimated_value, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['company_ticker'],
            result['company_cik'],
            result['filing_info']['form_type'],
            result['filing_info']['filing_date'],
            result['analysis_date'],
            json.dumps(result.get('business_problems', [])),
            json.dumps(result.get('financial_issues', [])),
            json.dumps(result.get('transformation_needs', [])),
            json.dumps(result.get('urgent_priorities', [])),
            json.dumps(result.get('opportunity_summary', {})),
            summary.get('total_issues_found', 0),
            summary.get('overall_score', 0),
            summary.get('estimated_value', 0),
            json.dumps(result)
        ))
        self.db.commit()
    
    def display_results(self, result: Dict[str, Any]):
        """Display comprehensive results"""
        
        if "error" in result:
            print(f"\n❌ {result['error']}")
            return
        
        ticker = result['company_ticker']
        filing = result['filing_info']
        summary = result['opportunity_summary']
        
        print(f"\n" + "="*80)
        print(f"📊 SEC API CONSULTING ANALYSIS: {ticker}")
        print("="*80)
        
        # Company and filing info
        print(f"\n🏢 COMPANY INFORMATION:")
        print(f"   Ticker: {ticker}")
        print(f"   CIK: {result['company_cik']}")
        print(f"   Has Financial Data: {'Yes' if result['has_financial_facts'] else 'No'}")
        
        print(f"\n📄 SOURCE FILING:")
        print(f"   Type: {filing['form_type']}")
        print(f"   Date: {filing['filing_date']}")
        print(f"   Sections Analyzed: {', '.join(result['sections_extracted'])}")
        
        # Analysis results
        categories = [
            ("🔍 BUSINESS PROBLEMS", "business_problems"),
            ("💰 FINANCIAL ISSUES", "financial_issues"), 
            ("🚀 TRANSFORMATION OPPORTUNITIES", "transformation_needs"),
            ("🚨 URGENT PRIORITIES", "urgent_priorities")
        ]
        
        for title, key in categories:
            items = result.get(key, [])
            if items:
                print(f"\n{title}:")
                for i, item in enumerate(items[:4], 1):
                    print(f"   {i}. {item}")
            else:
                print(f"\n{title}: None identified")
        
        # Opportunity assessment
        scores = summary.get('individual_scores', {})
        print(f"\n📈 CONSULTING OPPORTUNITY ASSESSMENT:")
        print(f"   Overall Opportunity Score: {summary.get('overall_score', 0):.1f}/10")
        print(f"   • Opportunity Attractiveness: {scores.get('opportunity_score', 0):.1f}/10")
        print(f"   • Project Value Potential: {scores.get('project_value', 0):.1f}/10")
        print(f"   • Urgency Level: {scores.get('urgency', 0):.1f}/10")
        print(f"   • Complexity Score: {scores.get('complexity', 0):.1f}/10")
        
        print(f"\n💰 PROJECT ESTIMATES:")
        print(f"   Estimated Total Value: ${summary.get('estimated_value', 0):,.0f}")
        print(f"   Expected Sales Cycle: {summary.get('timeline_months', 0)} months")
        print(f"   Total Issues Identified: {summary.get('total_issues_found', 0)}")
        print(f"   Analysis Quality: {summary.get('analysis_quality', 'unknown').title()}")
        
        focus_areas = summary.get('focus_areas', '')
        if focus_areas:
            print(f"   Priority Focus Areas: {focus_areas}")
        
        # Recommendation
        overall_score = summary.get('overall_score', 0)
        if overall_score >= 8.0:
            recommendation = "🔥 HIGH PRIORITY - Immediate outreach strongly recommended"
        elif overall_score >= 6.5:
            recommendation = "⚡ MEDIUM PRIORITY - Strong consulting opportunity, pursue actively"
        elif overall_score >= 5.0:
            recommendation = "📋 LOW PRIORITY - Monitor for developments, consider targeted approach"
        else:
            recommendation = "❌ POOR FIT - Limited consulting potential based on current analysis"
        
        print(f"\n🎯 RECOMMENDATION: {recommendation}")
        
        print("="*80)
    
    async def close(self):
        """Cleanup resources"""
        await self.llm_analyzer.close()
        self.db.close()

# === INTERACTIVE INTERFACE ===

class SECAPIInterface:
    """Interactive interface for SEC API-based analysis"""
    
    def __init__(self, model: str = "gemma3:latest"):
        self.pipeline = SECAPIConsultingPipeline(model)
        self.model = model
    
    def print_header(self):
        print("\n" + "="*80)
        print("🏛️  OFFICIAL SEC API CONSULTING ANALYZER")
        print("   Using official data.sec.gov APIs + AI analysis")
        print(f"   Powered by {self.model}")
        print("="*80)
        print("\n🔧 How it works:")
        print("1. 🔍 Looks up company CIK using official SEC ticker database")
        print("2. 📋 Fetches recent filings via official submissions API")
        print("3. 💰 Retrieves financial facts via official company facts API")
        print("4. 📄 Downloads and parses latest 10-K/10-Q filing")
        print("5. 🎯 Extracts key business sections intelligently")
        print("6. 🤖 AI analyzes each section for consulting opportunities")
        print("7. 📊 Generates comprehensive opportunity assessment")
        print("\n✅ Benefits: Clean data, no rate limiting issues, real-time updates")
    
    async def run_interactive(self):
        """Run interactive analysis"""
        
        self.print_header()
        
        print(f"\n" + "="*60)
        print("Enter company ticker symbols for SEC API analysis")
        print("Examples: AAPL, TSLA, NFLX, UBER, ZOOM, PTON")
        print("Type 'demo' for sample analysis, 'batch' for multiple, 'quit' to exit")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n🎯 Enter ticker symbol: ").strip().upper()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                elif user_input.lower() == 'demo':
                    await self.run_demo()
                    continue
                
                elif user_input.lower() == 'batch':
                    await self.run_batch_mode()
                    continue
                
                elif not user_input or len(user_input) > 10:
                    print("❌ Please enter a valid ticker symbol")
                    continue
                
                print(f"\n🔄 Starting SEC API analysis for {user_input}...")
                print("This may take 60-90 seconds...")
                
                result = await self.pipeline.analyze_company_complete(user_input)
                self.pipeline.display_results(result)
                
                # Additional options
                await self.post_analysis_options(result)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue
        
        await self.pipeline.close()
    
    async def post_analysis_options(self, result: Dict[str, Any]):
        """Additional options after analysis"""
        
        if "error" in result:
            return
        
        print(f"\n" + "="*50)
        print("📋 ADDITIONAL OPTIONS:")
        print("1. Generate detailed outreach strategy")
        print("2. Create executive briefing document")
        print("3. Export analysis to JSON file")
        print("4. Compare with industry benchmarks")
        print("5. Continue to next company")
        
        try:
            choice = input("Select option (1-5) or press Enter to continue: ").strip()
            
            if choice == '1':
                await self.generate_outreach_strategy(result)
            elif choice == '2':
                await self.generate_executive_briefing(result)
            elif choice == '3':
                self.export_analysis(result)
            elif choice == '4':
                await self.industry_comparison(result)
            
        except:
            pass
    
    async def generate_outreach_strategy(self, result: Dict[str, Any]):
        """Generate comprehensive outreach strategy"""
        
        print("\n📧 Generating outreach strategy...")
        
        ticker = result['company_ticker']
        summary = result['opportunity_summary']
        
        # Get top issues across all categories
        top_issues = []
        for category in ['business_problems', 'financial_issues', 'urgent_priorities']:
            issues = result.get(category, [])
            top_issues.extend(issues[:2])
        
        system_prompt = "You are a senior consulting partner developing an outreach strategy."
        
        user_prompt = f"""
Develop a comprehensive outreach strategy for {ticker}:

OPPORTUNITY SCORE: {summary.get('overall_score', 0):.1f}/10
ESTIMATED VALUE: ${summary.get('estimated_value', 0):,}
KEY ISSUES: {'; '.join(top_issues[:4])}
FOCUS AREAS: {summary.get('focus_areas', '')}

Create a strategy covering:
1. APPROACH: How to initiate contact (email, LinkedIn, warm intro, etc.)
2. MESSAGING: Key value propositions to emphasize
3. TIMING: When to reach out and follow up
4. STAKEHOLDERS: Who to target (C-suite, VP level, etc.)
5. PROOF POINTS: Relevant case studies/examples to mention

Make it actionable and specific to their situation.
"""
        
        strategy = await self.pipeline.llm_analyzer.generate(user_prompt, system_prompt, temperature=0.6)
        
        print(f"\n" + "="*70)
        print(f"📧 OUTREACH STRATEGY FOR {ticker}")
        print("="*70)
        print(strategy)
        print("="*70)
    
    async def generate_executive_briefing(self, result: Dict[str, Any]):
        """Generate executive briefing document"""
        
        print("\n📋 Generating executive briefing...")
        
        ticker = result['company_ticker']
        filing = result['filing_info']
        summary = result['opportunity_summary']
        
        # Count issues by category
        business_count = len(result.get('business_problems', []))
        financial_count = len(result.get('financial_issues', []))
        transform_count = len(result.get('transformation_needs', []))
        urgent_count = len(result.get('urgent_priorities', []))
        
        system_prompt = "You are creating an executive briefing for senior consulting partners."
        
        user_prompt = f"""
Create an executive briefing for the {ticker} opportunity:

COMPANY: {ticker}
FILING ANALYZED: {filing['form_type']} from {filing['filing_date']}
OPPORTUNITY SCORE: {summary.get('overall_score', 0):.1f}/10
ESTIMATED VALUE: ${summary.get('estimated_value', 0):,}

ISSUES IDENTIFIED:
• Business Problems: {business_count}
• Financial Issues: {financial_count}  
• Transformation Needs: {transform_count}
• Urgent Priorities: {urgent_count}

Create a structured executive briefing with:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. KEY FINDINGS (bullet points of main issues)
3. CONSULTING OPPORTUNITY (specific services we could provide)
4. FINANCIAL IMPACT (potential project value and timeline)
5. NEXT STEPS (recommended actions)

Keep professional and concise.
"""
        
        briefing = await self.pipeline.llm_analyzer.generate(user_prompt, system_prompt, temperature=0.4)
        
        print(f"\n" + "="*70)
        print(f"📋 EXECUTIVE BRIEFING: {ticker}")
        print("="*70)
        print(briefing)
        print("="*70)
    
    def export_analysis(self, result: Dict[str, Any]):
        """Export analysis to JSON file"""
        
        ticker = result['company_ticker']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{ticker}_sec_api_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"\n💾 Analysis exported to: {filename}")
            print(f"   File size: {len(json.dumps(result)):,} characters")
            
        except Exception as e:
            print(f"\n❌ Export failed: {e}")
    
    async def industry_comparison(self, result: Dict[str, Any]):
        """Generate industry comparison insights"""
        
        print("\n📊 Generating industry comparison...")
        
        ticker = result['company_ticker']
        summary = result['opportunity_summary']
        
        # Get recent analysis from database for comparison
        cursor = self.pipeline.db.execute('''
            SELECT company_ticker, overall_score, estimated_value, total_issues
            FROM api_analyses 
            WHERE analysis_date > date('now', '-30 days')
            AND company_ticker != ?
            ORDER BY overall_score DESC
            LIMIT 10
        ''', (ticker,))
        
        recent_analyses = cursor.fetchall()
        
        if recent_analyses:
            avg_score = sum(row[1] for row in recent_analyses) / len(recent_analyses)
            avg_value = sum(row[2] for row in recent_analyses) / len(recent_analyses)
            avg_issues = sum(row[3] for row in recent_analyses) / len(recent_analyses)
            
            print(f"\n📈 INDUSTRY COMPARISON ({len(recent_analyses)} recent analyses):")
            print(f"   {ticker} Opportunity Score: {summary.get('overall_score', 0):.1f}/10")
            print(f"   Industry Average: {avg_score:.1f}/10")
            print(f"   Percentile Rank: {self._calculate_percentile(summary.get('overall_score', 0), [r[1] for r in recent_analyses])}")
            
            print(f"\n💰 VALUE COMPARISON:")
            print(f"   {ticker} Estimated Value: ${summary.get('estimated_value', 0):,.0f}")
            print(f"   Industry Average: ${avg_value:,.0f}")
            
            print(f"\n🔍 COMPLEXITY COMPARISON:")
            print(f"   {ticker} Issues Found: {summary.get('total_issues_found', 0)}")
            print(f"   Industry Average: {avg_issues:.1f}")
            
            # Show top performers
            print(f"\n🏆 TOP RECENT OPPORTUNITIES:")
            for i, (comp_ticker, score, value, issues) in enumerate(recent_analyses[:3], 1):
                print(f"   {i}. {comp_ticker}: {score:.1f}/10 (${value:,.0f})")
        else:
            print(f"\n📊 No recent analyses available for comparison")
    
    def _calculate_percentile(self, score: float, scores: List[float]) -> str:
        """Calculate percentile rank"""
        if not scores:
            return "N/A"
        
        scores_sorted = sorted(scores)
        rank = sum(1 for s in scores_sorted if s <= score) / len(scores_sorted) * 100
        
        if rank >= 90:
            return f"{rank:.0f}th percentile (Excellent)"
        elif rank >= 75:
            return f"{rank:.0f}th percentile (Above Average)"
        elif rank >= 50:
            return f"{rank:.0f}th percentile (Average)"
        elif rank >= 25:
            return f"{rank:.0f}th percentile (Below Average)"
        else:
            return f"{rank:.0f}th percentile (Poor)"
    
    async def run_demo(self):
        """Run demo with interesting companies"""
        
        demo_companies = ['PTON', 'ZOOM', 'UBER']
        
        print(f"\n🎬 RUNNING SEC API DEMO with {len(demo_companies)} companies")
        print("="*60)
        
        for i, ticker in enumerate(demo_companies, 1):
            print(f"\n📊 Demo {i}/{len(demo_companies)}: {ticker}")
            
            try:
                result = await self.pipeline.analyze_company_complete(ticker)
                self.pipeline.display_results(result)
                
                if i < len(demo_companies):
                    input(f"\nPress Enter to continue to next company...")
                
            except Exception as e:
                print(f"❌ Demo failed for {ticker}: {e}")
                continue
    
    async def run_batch_mode(self):
        """Run batch analysis mode"""
        
        tickers_input = input("\nEnter ticker symbols (comma-separated): ").strip()
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
        
        if not tickers:
            print("No valid tickers provided.")
            return
        
        print(f"\n🚀 BATCH SEC API ANALYSIS: {len(tickers)} companies")
        print("="*60)
        
        results = []
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n📊 Progress: {i}/{len(tickers)} - {ticker}")
            
            try:
                result = await self.pipeline.analyze_company_complete(ticker)
                if "error" not in result:
                    results.append(result)
                    print(f"   ✅ Analysis complete")
                else:
                    print(f"   ❌ {result['error']}")
                
                # Small delay between companies
                if i < len(tickers):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                continue
        
        # Batch summary
        if results:
            self._display_batch_summary(results)
    
    def _display_batch_summary(self, results: List[Dict[str, Any]]):
        """Display batch analysis summary"""
        
        print(f"\n" + "="*70)
        print(f"📈 BATCH ANALYSIS SUMMARY ({len(results)} companies)")
        print("="*70)
        
        # Rank by opportunity score
        ranked = sorted(results, 
                       key=lambda x: x['opportunity_summary'].get('overall_score', 0), 
                       reverse=True)
        
        print(f"\n🏆 OPPORTUNITY RANKING:")
        for i, result in enumerate(ranked, 1):
            ticker = result['company_ticker']
            summary = result['opportunity_summary']
            score = summary.get('overall_score', 0)
            value = summary.get('estimated_value', 0)
            issues = summary.get('total_issues_found', 0)
            
            priority = "🔥" if score >= 8 else "⚡" if score >= 6.5 else "📋" if score >= 5 else "❌"
            
            print(f"   {i:2d}. {priority} {ticker}: {score:.1f}/10 | ${value:,.0f} | {issues} issues")
        
        # Calculate totals
        total_value = sum(r['opportunity_summary'].get('estimated_value', 0) for r in results)
        total_issues = sum(r['opportunity_summary'].get('total_issues_found', 0) for r in results)
        avg_score = sum(r['opportunity_summary'].get('overall_score', 0) for r in results) / len(results)
        
        high_priority = len([r for r in results if r['opportunity_summary'].get('overall_score', 0) >= 8])
        medium_priority = len([r for r in results if 6.5 <= r['opportunity_summary'].get('overall_score', 0) < 8])
        
        print(f"\n📊 PORTFOLIO SUMMARY:")
        print(f"   Total Pipeline Value: ${total_value:,.0f}")
        print(f"   Average Opportunity Score: {avg_score:.1f}/10")
        print(f"   Total Issues Identified: {total_issues}")
        print(f"   High Priority Companies: {high_priority}")
        print(f"   Medium Priority Companies: {medium_priority}")
        
        if high_priority > 0:
            print(f"\n🎯 IMMEDIATE ACTION ITEMS:")
            for result in ranked[:high_priority]:
                ticker = result['company_ticker']
                focus = result['opportunity_summary'].get('focus_areas', '')
                print(f"   • {ticker}: {focus}")

# === MAIN EXECUTION ===

async def main():
    """Main execution function"""
    
    print("🏛️  SEC Official API Consulting Analysis System")
    print("Using official data.sec.gov APIs for clean, real-time data")
    
    print("\n🔧 Available modes:")
    print("1. Interactive single company analysis")
    print("2. Batch analysis (multiple companies)")
    print("3. Demo mode (sample companies)")
    
    try:
        choice = input("\nSelect mode (1-3): ").strip()
        
        if choice == '1':
            interface = SECAPIInterface()
            await interface.run_interactive()
            
        elif choice == '2':
            interface = SECAPIInterface()
            await interface.run_batch_mode()
            
        elif choice == '3':
            interface = SECAPIInterface()
            await interface.run_demo()
            
        else:
            print("Invalid choice.")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())