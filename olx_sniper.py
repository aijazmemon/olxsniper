import os
import requests
from playwright.sync_api import sync_playwright

# --- CONFIGURATION MAP ---
# Contains all 4 vehicles and their specific OLX filter links
TARGETS = {
    "Burgman": "https://www.olx.in/en-in/mira-road_g5460046/scooters_c1413?filter=make_eq_suzuki-scooter%2Cmodel_eq_scooters-suzuki-burgman%2Cprice_max_78000&sorting=desc-creation",
    "Unicorn": "https://www.olx.in/en-in/mira-road_g5460046/motorcycles_c81?filter=make_eq_honda%2Cmodel_eq_honda-cb-unicorn-150_and_honda-cb-unicorn&sorting=desc-creation",
    "Access 125": "https://www.olx.in/en-in/mira-road_g5460046/scooters_c1413?filter=make_eq_suzuki-scooter%2Cmodel_eq_suzuki-scooter-access-125%2Cprice_max_54000%2Cyear_between_2020_to_2024&sorting=desc-creation",
    "Honda City I-vtec": "https://www.olx.in/en-in/mira-road_g5460046/cars_c84?filter=make_eq_cars-honda%2Cmodel_eq_cars-honda-city%2Cprice_max_130000%2Cyear_between_2009_to_2012"
}

TELEGRAM_CHAT_ID = "-5318874682"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") 
SEEN_FILE = "seen_ids.txt"

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_seen(seen_set):
    with open(SEEN_FILE, "w") as f:
        for ad_id in seen_set:
            f.write(f"{ad_id}\n")

# Updated to accept target_name so the message changes automatically
def send_telegram_alert(target_name, title, price, details, link):
    # Use a car emoji for Honda City, bike emoji for the rest
    icon = "🚗" if "honda city" in target_name.lower() else "🏍️"
    
    message = (
        f"🚨 **NEW {target_name.upper()} DEAL SPOTTED** 🚨\n\n"
        f"{icon} **Model:** {title}\n"
        f"💰 **Price:** {price}\n"
        f"📋 **Details:** {details}\n\n"
        f"🔗 **Open Listing:** {link}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=10)

def main():
    seen_listings = load_seen()
    new_finds = False

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
        )
        page = context.new_page()
        
        # Loop through all 4 vehicles
        for target_name, target_url in TARGETS.items():
            print(f"🔍 Scanning market for: {target_name}...")
            try:
                page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                
                ad_links = page.locator("a[href*='/item/']").all()
                
                for link_element in ad_links:
                    href = link_element.get_attribute("href")
                    if not href: continue
                    
                    full_link = f"https://www.olx.in{href}" if href.startswith("/") else href
                    ad_id = href.split("-iid-")[-1] if "-iid-" in href else href.split("/")[-1]
                    raw_text = link_element.inner_text()
                    
                    if len(raw_text.strip()) < 5: continue
                    
                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    price_text = next((line for line in lines if "₹" in line), "0")
                    
                    try:
                        numeric_price = int(price_text.replace("₹", "").replace(",", "").strip())
                        # Universal safeguard baseline filter
                        if numeric_price <= 15000: continue
                    except ValueError:
                        continue

                    if ad_id not in seen_listings:
                        details_text = " | ".join(lines)
                        print(f"🔥 Live {target_name} ad caught: {price_text}")
                        
                        # Only fire the alert if this isn't the initial setup run
                        if seen_listings:
                            # Pass the target_name to the alert function!
                            send_telegram_alert(target_name, lines[0] if lines else target_name, price_text, details_text, full_link)
                        
                        seen_listings.add(ad_id)
                        new_finds = True

            except Exception as e:
                print(f"Scrape Error while processing {target_name}: {e}")
                
        browser.close()

    # Status update logic
    if new_finds:
        save_seen(seen_listings)
        print("✅ New listings found and saved.")
    else:
        print("🔍 Scan complete: No new vehicle updates across all target lists.")
        # Consolidated hourly heartbeat message
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": "🔍 *Update:* No new Burgman, Access, Unicorn, or Honda City listings in the last 1 hour.", 
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Failed to send empty run alert: {e}")

if __name__ == "__main__":
    main()
