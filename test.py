import argparse
import csv
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def fetch_pubmed_ids(query: str) -> List[str]:
    """Fetch PubMed IDs based on a search query."""
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": 10}
    response = requests.get(f"{BASE_URL}esearch.fcgi", params=params)
    response.raise_for_status()
    
    # Debugging: Print the raw response
    print("API Response:", response.json())

    return response.json().get("esearchresult", {}).get("idlist", [])


def fetch_paper_details(pubmed_id: str) -> Optional[Dict]:
    """Fetch detailed information for a given PubMed ID."""
    params = {"db": "pubmed", "id": pubmed_id, "retmode": "xml"}
    response = requests.get(f"{BASE_URL}efetch.fcgi", params=params)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    
    title = root.find(".//ArticleTitle")
    pub_date = root.find(".//PubDate/Year")
    authors = root.findall(".//Author")
    
    company_authors = []
    company_affiliations = []
    corresponding_email = None
    
    for author in authors:
        affiliation = author.find("AffiliationInfo/Affiliation")
        if affiliation is not None:
            if is_company_affiliation(affiliation.text):
                name = author.find("LastName")
                if name is not None:
                    company_authors.append(name.text)
                    company_affiliations.append(affiliation.text)
            email = author.find("AffiliationInfo/Affiliation/Email")
            if email is not None:
                corresponding_email = email.text
    
    return {
        "PubmedID": pubmed_id,
        "Title": title.text if title is not None else "N/A",
        "Publication Date": pub_date.text if pub_date is not None else "N/A",
        "Non-academic Author(s)": ", ".join(company_authors),
        "Company Affiliation(s)": ", ".join(company_affiliations),
        "Corresponding Author Email": corresponding_email or "N/A",
    }

def is_company_affiliation(affiliation: str) -> bool:
    """Determine if an affiliation belongs to a non-academic institution."""
    company_keywords = ["Inc", "Ltd", "Biotech", "Pharma", "Laboratories"]
    academic_keywords = ["University", "College", "Institute", "Hospital"]
    
    if any(word in affiliation for word in company_keywords) and not any(word in affiliation for word in academic_keywords):
        return True
    return False

def save_to_csv(results: List[Dict], filename: str):
    """Save results to a CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

def main():
    parser = argparse.ArgumentParser(description="Fetch research papers from PubMed.")
    parser.add_argument("query", type=str, help="Search query for PubMed.")
    parser.add_argument("-f", "--file", type=str, help="Filename to save results.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode.")
    args = parser.parse_args()
    
    pubmed_ids = fetch_pubmed_ids(args.query)
    if args.debug:
        print(f"Fetched PubMed IDs: {pubmed_ids}")
    
    results = [fetch_paper_details(pid) for pid in pubmed_ids]
    
    if args.file:
        save_to_csv(results, args.file)
        print(f"Results saved to {args.file}")
    else:
        for result in results:
            print(result)

if __name__ == "__main__":
    main()