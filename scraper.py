import requests
from bs4 import BeautifulSoup
import re

# The list of Cinema IDs you provided
CINEMA_IDS = [
    "3101026", "3101027", "3101048", "3101049", 
    "3101175", "3101032", "3101041"
]

import requests
from bs4 import BeautifulSoup

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
        
        # 1. Extract Cinema Name
        page_title = soup.title.string if soup.title else f"Cinema {cinema_id}"
        cinema_name = page_title.split('-')[0].strip()

        movies_data = []

        # Find movie rows (each movie is in a 'row' div)
        rows = soup.find_all('div', class_='row')

        for row in rows:
            # A. Get Movie Title
            title_tag = row.find('h3')
            if not title_tag:
                continue 
            
            movie_name = title_tag.text.strip()
            shows_list = []

            # B. Find ALL showtime tables (Different experiences are in different tables)
            tables = row.find_all('table', class_='showtimes')

            for table in tables:
                # --- 1. Get Experience Type (e.g., MAX VIP, Standard) ---
                # It is usually in an <h6> tag inside the table
                exp_header = table.find('h6')
                experience_type = exp_header.text.strip() if exp_header else "Standard"

                # --- 2. Iterate through rows in this specific table ---
                for tr in table.find_all('tr'):
                    time_tag = tr.find('strong')
                    
                    if time_tag:
                        time_text = time_tag.text.strip()
                        
                        # Get Price
                        price_tag = tr.find('span', class_='price')
                        price_text = price_tag.text.strip() if price_tag else "Unknown Price"
                        
                        # --- 3. Check for 3D SVG ---
                        # If the SVG with id "3d_svg" exists in this row, it is 3D
                        is_3d = bool(tr.find('svg', id='3d_svg'))
                        format_type = "3D" if is_3d else "2D"

                        # Format the output string
                        # Example: "02:30 pm (160 EGP) - MAX VIP [3D]"
                        shows_list.append(
                            f"{time_text} ({price_text}) - {experience_type} [{format_type}]"
                        )
            
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