import requests
from bs4 import BeautifulSoup
import re
import os
import time

# Global header required by SEC
HEADERS = {
    "User-Agent": "Nathan Kong - SEC Parser - 1nathankong@gmail.com"
}

def get_cik_from_ticker(ticker: str) -> str:
    """
    Get the 10-digit CIK for a given stock ticker using the SEC index.
    """
    ticker = ticker.lower()
    index_url = "https://www.sec.gov/files/company_tickers.json"
    print("Fetching CIK index from SEC...")
    r = requests.get(index_url, headers=HEADERS)
    if r.status_code != 200:
        raise Exception(f"Could not fetch ticker index: {r.status_code}")
    cik_map = {v['ticker'].lower(): str(v['cik_str']).zfill(10) for v in r.json().values()}

    if ticker not in cik_map:
        raise Exception(f"Ticker {ticker} not found in SEC index")
    return cik_map[ticker]


def get_latest_10k_htm_url(cik: str) -> str:
    """
    Get the latest 10-K .htm URL for the given 10-digit CIK.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"Fetching recent filings for CIK {cik}...")
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        raise Exception(f"Could not fetch filing metadata: {r.status_code}")
    filings = r.json()['filings']['recent']
    for i in range(len(filings['form'])):
        if filings['form'][i] == "10-K":
            acc_no = filings['accessionNumber'][i].replace("-", "")
            primary_doc = filings['primaryDocument'][i]
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no}/{primary_doc}"
    raise Exception("No 10-K filing found for this CIK.")


def download_and_clean_filing(url: str, output_txt_path: str):
    """
    Download and clean the HTML 10-K filing into a plain .txt file.
    """
    print(f"Downloading filing: {url}")
    for attempt in range(3):
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            break
        elif r.status_code == 403:
            print("403 Forbidden - retrying in 5 seconds...")
            time.sleep(5)
        else:
            raise Exception(f"Failed with status: {r.status_code}")
    else:
        raise Exception("Failed after 3 retries due to 403")

    soup = BeautifulSoup(r.content, 'html.parser')
    for tag in soup(['script', 'style', 'head', 'meta', 'table']):
        tag.decompose()

    raw_lines = soup.get_text(separator="\n").splitlines()
    clean_lines = []
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not re.fullmatch(r'\d{1,4}', stripped) and not re.search(r'table of contents', stripped, re.IGNORECASE):
            clean_lines.append(stripped)

    text = "\n".join(clean_lines)

    os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Cleaned 10-K saved to: {output_txt_path}")


def run_pipeline_for_ticker(ticker: str):
    """
    End-to-end: Ticker → CIK → .htm → .txt cleaned
    """
    try:
        print(f"\nProcessing {ticker.upper()}...")
        cik = get_cik_from_ticker(ticker)
        url = get_latest_10k_htm_url(cik)
        out_path = f"sec_txt/{ticker.lower()}_10k.txt"
        download_and_clean_filing(url, out_path)
    except Exception as e:
        print(f"Error for {ticker.upper()}: {e}")


if __name__ == "__main__":
    # High-impact companies across major industries
    tickers = {
        # AI/Semiconductors
        "AMD": "Advanced Micro Devices - AI/GPU",
        "NVDA": "NVIDIA - AI/GPU Leader", 
        "QCOM": "Qualcomm - Mobile/AI Chips",
        
        # Cloud/Enterprise Software
        "MSFT": "Microsoft - Cloud/AI/Enterprise",
        "GOOGL": "Alphabet - Search/Cloud/AI",
        "AMZN": "Amazon - Cloud/E-commerce",
        "CRM": "Salesforce - Enterprise Software",
        "PLTR": "Palantir - Data Analytics",
        
        # Electric Vehicles/Energy
        "TSLA": "Tesla - EVs/Energy Storage",
        "RIVN": "Rivian - Electric Trucks",
        "ENPH": "Enphase - Solar Energy",
        
        # Biotechnology/Healthcare
        "MRNA": "Moderna - mRNA Technology",
        "GILD": "Gilead Sciences - Biotech",
        "TDOC": "Teladoc - Digital Health",
        "VEEV": "Veeva Systems - Healthcare Software",
        
        # Fintech/Payments
        "PYPL": "PayPal - Digital Payments", 
        "COIN": "Coinbase - Cryptocurrency",
        "AFRM": "Affirm - Buy Now Pay Later",
        
        # Aerospace/Defense
        "LMT": "Lockheed Martin - Defense",
        "BA": "Boeing - Aerospace",
        "SPCE": "Virgin Galactic - Space Tourism",
        
        # Cybersecurity
        "CRWD": "CrowdStrike - Endpoint Security",
        "ZS": "Zscaler - Cloud Security",
        "OKTA": "Okta - Identity Management",
        
        # Food/Consumer Tech
        "BYND": "Beyond Meat - Plant-based Food",
        "ROKU": "Roku - Streaming Platform",
        "UBER": "Uber - Ride Sharing/Delivery",
        "ABNB": "Airbnb - Home Sharing",
        
        # Traditional Tech Giants
        "AAPL": "Apple - Consumer Electronics",
        "META": "Meta - Social Media/VR",
        "NFLX": "Netflix - Streaming",
        "ORCL": "Oracle - Enterprise Database"
    }
    
    print(f"Processing {len(tickers)} companies across high-impact industries:")
    for ticker, description in tickers.items():
        print(f"  • {ticker}: {description}")
    print()
    
    # Process all tickers
    for ticker in tickers.keys():
        run_pipeline_for_ticker(ticker)
        time.sleep(2)  # Rate limiting to be respectful to SEC servers
