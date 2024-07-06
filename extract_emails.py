import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urljoin, urlparse
import logging
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataExtractor(ABC):
    @abstractmethod
    def extract(self, text):
        pass

class EmailExtractor(DataExtractor):
    def extract(self, text):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return set(re.findall(email_pattern, text))

class PhoneExtractor(DataExtractor):
    def extract(self, text):
        phone_pattern = r'\+?\d{1,4}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        return set(re.findall(phone_pattern, text))

class URLVisitor:
    def __init__(self, base_url):
        self.base_url = base_url
        self.visited = set()
    
    def visit(self, url):
        emails = set()
        phones = set()
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return emails, phones

        soup = BeautifulSoup(response.text, 'html.parser')
        
        email_extractor = EmailExtractor()
        phone_extractor = PhoneExtractor()
        
        emails.update(email_extractor.extract(response.text))
        phones.update(phone_extractor.extract(response.text))
        
        self.visited.add(url)
        logging.info(f"Visited: {url}")
        
        for link in soup.find_all('a', href=True):
            link_url = urljoin(url, link['href'])
            if urlparse(link_url).netloc == urlparse(self.base_url).netloc and link_url not in self.visited:
                new_emails, new_phones = self.visit(link_url)
                emails.update(new_emails)
                phones.update(new_phones)

        return emails, phones

class DataCleaner:
    @staticmethod
    def clean_phone_number(phone):
        phone = re.sub(r'[^0-9+]', '', phone)
        return phone if re.match(r'^\+?\d{10,15}$', phone) else ''

class DataSaver:
    def save(self, emails, phones):
        cleaned_phones = [DataCleaner.clean_phone_number(phone) for phone in phones]
        valid_phones = [phone for phone in cleaned_phones if phone]
        
        data = {
            'Email': [],
            'Phone': []
        }
        
        max_length = max(len(emails), len(valid_phones))
        
        for i in range(max_length):
            email = emails.pop() if emails else ''
            phone = valid_phones.pop() if valid_phones else ''
            
            data['Email'].append(email)
            data['Phone'].append(phone)
        
        df = pd.DataFrame(data)
        df = df[(df['Email'] != '') | (df['Phone'] != '')]
        df.to_csv('extracted_data.csv', index=False)
        logging.info("Data saved to extracted_data.csv")

def main():
    url = 'https://accelx.net/'
    visitor = URLVisitor(url)
    emails, phones = visitor.visit(url)
    saver = DataSaver()
    saver.save(emails, phones)

if __name__ == "__main__":
    main()
