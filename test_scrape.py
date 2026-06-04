from curl_cffi import requests
from bs4 import BeautifulSoup

r = requests.get('https://leagueoflegends.fandom.com/wiki/Yone/LoL/Audio', impersonate='chrome120')
soup = BeautifulSoup(r.content, 'html.parser')

# Tìm headings
headings = soup.find_all(['h2', 'h3', 'h4'])
print(f"Headings: {len(headings)}")
for h in headings[:20]:
    print(f"  {h.name}: {h.get_text(strip=True)[:60]}")
