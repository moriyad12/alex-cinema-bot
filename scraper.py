import requests
from bs4 import BeautifulSoup
import re

# The list of Cinema IDs you provided
CINEMA_IDS = [
    "3101026", "3101027", "3101048", "3101049", 
    "3101175", "3101032", "3101041"
]

def get_movies_for_cinema(cinema_id):
    url = f"https://elcinema.com/en/theater/{cinema_id}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Extract Cinema Name from the Page Title
        page_title = soup.title.string if soup.title else f"Cinema {cinema_id}"
        cinema_name = page_title.split('-')[0].strip()

        movies_data = []

        # Find movie rows
        rows = soup.find_all('div', class_='row')

        for row in rows:
            # A. Get Movie Title
            title_tag = row.find('h3')
            if not title_tag:
                continue 
            
            movie_name = title_tag.text.strip()

            # B. Get Showtimes AND Prices
            shows_list = []
            showtime_table = row.find('table', class_='showtimes')
            
            if showtime_table:
                for tr in showtime_table.find_all('tr'):
                    time_tag = tr.find('strong')
                    price_tag = tr.find('span', class_='price')
                    
                    if time_tag:
                        time_text = time_tag.text.strip()
                        price_text = price_tag.text.strip() if price_tag else "Unknown Price"
                        shows_list.append(f"{time_text} ({price_text})")
            
            # Only add if we found shows
            if shows_list and movie_name:
                movies_data.append({
                    "movie": movie_name,
                    "shows": shows_list
                })

        return {
            "cinema_name": cinema_name,
            "movies": movies_data
        }

    except Exception as e:
        print(f"Error scraping {cinema_id}: {e}")
        return None

def get_all_cinemas_data():
    """Loops through all IDs and returns a huge list of data"""
    all_data = []
    print("🔄 Scanning all Alexandria cinemas...")
    
    for cid in CINEMA_IDS:
        data = get_movies_for_cinema(cid)
        if data:
            all_data.append(data)
            print(f"✅ Found data for: {data['cinema_name']}")
        else:
            print(f"❌ No data for ID {cid}")
            
    return all_data

# --- MODIFIED: Save to File Block ---
if __name__ == "__main__":
    results = get_all_cinemas_data()
    
    # We will build the entire text string here
    file_content = ""
    
    for cinema in results:
        file_content += f"📍 {cinema['cinema_name'].upper()}\n"
        file_content += "="*40 + "\n"
        for m in cinema['movies']:
            file_content += f"🎬 {m['movie']}\n"
            file_content += f"💵 {', '.join(m['shows'])}\n"
            file_content += "-" * 20 + "\n"
        file_content += "\n" # Extra space between cinemas

    # Open the file in 'write' mode ('w') and save the content
    with open("cinema_data.txt", "w", encoding="utf-8") as f:
        f.write(file_content)
        
    print("\n✅ DONE! Data has been saved to 'cinema_data.txt'")