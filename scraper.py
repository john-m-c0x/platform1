from flask import Flask, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime
import pytz
import threading
import atexit
import logging
import json
from pathlib import Path
import os
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global cache for departure data
cache = {
    'departures': [],
    'last_updated': None,
    'updating': False
}

def get_melbourne_time():
    return datetime.now(pytz.timezone('Australia/Melbourne'))

def clear_chromedriver_cache():
    try:
        cache_path = os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "chromedriver")
        if os.path.exists(cache_path):
            shutil.rmtree(cache_path)
            logger.info("Cleared ChromeDriver cache")
    except Exception as e:
        logger.error(f"Error clearing ChromeDriver cache: {e}")

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    try:
        # First try with basic setup
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logger.error(f"Basic ChromeDriver setup failed: {e}")
        try:
            # Clear cache and try with ChromeDriverManager
            clear_chromedriver_cache()
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager(version="114.0.5735.90").install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as fallback_error:
            logger.error(f"Fallback ChromeDriver setup failed: {fallback_error}")
            raise

def extract_departure_data(card):
    scheduled_time = card.find_element(By.CLASS_NAME, "departure-card__info__time__value").text
    title = card.find_element(By.CLASS_NAME, "departure-card__title").text
    
    if "Alamein" in title:
        return None
    
    live_elements = card.find_elements(By.CLASS_NAME, "DepartureTimeView__text")
    live_time = live_elements[0].text if live_elements else None
    
    return {
        'scheduled_time': scheduled_time,
        'live_time': live_time,
        'destination': title,
        'scraped_at': get_melbourne_time().strftime("%H:%M")
    }

def print_timetable(departures):
    if not departures:
        return
    
    logger.info("\n🚂 RIVERSDALE STATION DEPARTURE TIMES 🚂")
    logger.info("=" * 45)
    logger.info("Platform 1 (City-bound) trains:\n")
    
    for dep in departures:
        time_str = dep['scheduled_time']
        if dep.get('live_time'):
            time_str += f" (LIVE: {dep['live_time']})"
        logger.info(f"   {time_str} → {dep['destination']}")
    
    logger.info("\n" + "=" * 45)
    logger.info(f"Total trains: {len(departures)}")
    logger.info(f"Scraped at: {departures[0]['scraped_at']} Melbourne time")

def save_to_json(departures):
    if not departures:
        return None
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    filename = data_dir / f"departures_{get_melbourne_time().strftime('%Y%m%d_%H%M')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(departures, f, indent=2)
    
    return filename

def scrape_departures():
    driver = None
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Scraping attempt {attempt + 1}/{max_retries}")
            driver = setup_driver()
            driver.get("https://www.ptv.vic.gov.au/stop/1166/riversdale-station/0/train/")
            
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "departure-card"))
            )
            
            departures = []
            for card in driver.find_elements(By.CLASS_NAME, "departure-card"):
                try:
                    departure = extract_departure_data(card)
                    if departure:
                        departures.append(departure)
                except Exception as e:
                    logger.error(f"Error extracting departure: {e}")
                    continue
            
            if departures:
                sorted_departures = sorted(departures, key=lambda x: x['scheduled_time'])
                print_timetable(sorted_departures)  # Print in console for verification
                save_to_json(sorted_departures)     # Save to file for debugging
                return sorted_departures
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    logger.error("All scraping attempts failed")
    return []

def update_cache():
    while True:
        try:
            logger.info("Starting cache update")
            cache['updating'] = True
            departures = scrape_departures()
            if departures:
                cache['departures'] = departures
                cache['last_updated'] = get_melbourne_time().strftime("%H:%M")
                logger.info(f"Cache updated at {cache['last_updated']}")
            cache['updating'] = False
            time.sleep(300)  # Update every 5 minutes
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
            cache['updating'] = False
            time.sleep(60)  # Wait 1 minute before retrying if there's an error

@app.route('/api/health')
def health_check():
    status = {"status": "healthy"}
    logger.info(f"Health check: {status}")
    return jsonify(status)

@app.route('/api/departures')
def get_departures():
    response_data = {
        'departures': cache['departures'],
        'lastUpdated': cache['last_updated'],
        'updating': cache['updating']
    }
    logger.info("API Response:")
    logger.info(f"  Last Updated: {response_data['lastUpdated']}")
    logger.info(f"  Updating: {response_data['updating']}")
    logger.info(f"  Number of departures: {len(response_data['departures'])}")
    if response_data['departures']:
        print_timetable(response_data['departures'])
    return jsonify(response_data)

def ensure_dependencies():
    try:
        import pytz
        from selenium import webdriver
    except ImportError:
        import subprocess
        subprocess.check_call(["pip", "install", "pytz", "selenium"])

def start_background_thread():
    thread = threading.Thread(target=update_cache, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    logger.info("Starting Platform 1 Cafe Train Departures API")
    ensure_dependencies()  # Make sure all dependencies are installed
    
    # Clear ChromeDriver cache on startup
    clear_chromedriver_cache()
    
    background_thread = start_background_thread()
    atexit.register(lambda: setattr(background_thread, "_stop", True))
    logger.info("Server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000) 