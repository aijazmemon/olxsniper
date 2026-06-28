import os
import requests
from playwright.sync_api import sync_playwright

OLX_WEB_URL = "https://www.olx.in/mira-road_g5460046/scooters_c1413?filter=make_eq_suzuki-scooter%2Cmodel_eq_scooters-suzuki-burgman%2Cprice_max_64000&sorting=desc-creation"
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

def send_telegram_alert(title, price, details, link):
    message = (
        f"🚨 **NEW BURGMAN DEAL SPOTTED** 🚨\n\n"
        f"🏍️ **Model:** {title}\n"
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
        
        try:
            page.goto(OLX_WEB_URL, timeout=45000, wait_until="domcontentloaded")
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
                    if numeric_price <= 30000: continue
                except ValueError:
                    continue

                if ad_id not in seen_listings:
                    details_text = " | ".join(lines)
                    print(f"🔥 Live ad caught: {price_text}")
                    if seen_listings:
                        send_telegram_alert("Burgman Listing", price_text, details_text, full_link)
                    
                    seen_listings.add(ad_id)
                    new_finds = True

        except Exception as e:
            print(f"Scrape Error: {e}")
        finally:
            browser.close()

    # Fixed and cleanly aligned status logic block
    if new_finds:
        save_seen(seen_listings)
        print("✅ New listings found and saved.")
    else:
        print("🔍 Scan complete: Checked OLX successfully, but no new Burgman listings found.")

if __name__ == "__main__":
    main()
