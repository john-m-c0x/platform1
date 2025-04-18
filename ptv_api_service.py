from flask import Flask, jsonify
from flask_cors import CORS
import requests
import hmac
from hashlib import sha1
import json
from datetime import datetime, timedelta
import pytz
import logging
import time
from pathlib import Path
import sys
import os
import threading
import atexit
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# PTV API Configuration
PTV_BASE_URL = "https://timetableapi.ptv.vic.gov.au"
DEV_ID = os.environ.get("PTV_DEV_ID", "")
API_KEY = os.environ.get("PTV_API_KEY", "")
RIVERSDALE_STOP_ID = int(os.environ.get("PTV_STOP_ID", "1166"))  # Riversdale Station ID
MELBOURNE_TZ = pytz.timezone('Australia/Melbourne')

# Check for missing environment variables
if not DEV_ID or not API_KEY:
    logger.error("Missing PTV API credentials in environment variables")
    logger.error("Please set PTV_DEV_ID and PTV_API_KEY in your .env file")
    sys.exit(1)

app = Flask(__name__)
CORS(app)

# Global cache for departure data
cache = {
    'departures': [],
    'last_updated': None,
    'updating': False
}

def get_melbourne_time():
    return datetime.now(MELBOURNE_TZ)

def generate_signature(request_path):
    request_path = request_path + ('&' if ('?' in request_path) else '?')
    raw = f"{request_path}devid={DEV_ID}"
    hashed = hmac.new(API_KEY.encode('utf-8'), raw.encode('utf-8'), sha1)
    return hashed.hexdigest().upper()

def get_ptv_url(endpoint):
    request_path = endpoint
    request_path = request_path + ('&' if ('?' in request_path) else '?')
    raw = f"{request_path}devid={DEV_ID}"
    signature = generate_signature(endpoint)
    return f"{PTV_BASE_URL}{raw}&signature={signature}"

def parse_departure_data(departure, routes, directions, runs, disruptions=None):
    route_id = str(departure.get('route_id', ''))
    direction_id = str(departure.get('direction_id', ''))
    run_id = str(departure.get('run_id', ''))
    
    # Add debugging information for specific run
    run_exists = run_id in runs if runs else False
    if not run_exists and runs:
        logger.debug(f"Run ID {run_id} not found in runs dictionary. Available run IDs: {list(runs.keys())[:5]}...")
    
    route_info = routes.get(route_id, {}) if routes else {}
    direction_info = directions.get(direction_id, {}) if directions else {}
    run_info = runs.get(run_id, {}) if runs else {}
    
    # Get destination information with fallbacks
    destination = 'Unknown'
    if run_info and 'destination_name' in run_info:
        destination = run_info.get('destination_name')
    elif direction_info and 'direction_name' in direction_info:
        destination = direction_info.get('direction_name')
    elif direction_id == '1':  # Hardcoded fallback for direction_id 1
        destination = 'Camberwell'  # Known city-bound destination
    
    # Handle scheduled time
    scheduled_time_utc = departure.get('scheduled_departure_utc')
    if not scheduled_time_utc:
        logger.error(f"Missing scheduled_departure_utc in departure data: {departure}")
        # Use current time as fallback
        scheduled_time = get_melbourne_time()
    else:
        scheduled_time = datetime.fromisoformat(scheduled_time_utc.replace('Z', '+00:00')).astimezone(MELBOURNE_TZ)
    
    estimated_time_utc = departure.get('estimated_departure_utc')
    
    # Get vehicle information safely
    vehicle_info = None
    if run_info and 'vehicle_descriptor' in run_info:
        vehicle_info = run_info['vehicle_descriptor'].get('description', None)
    
    # Get disruption information safely
    disruption_info = []
    if disruptions and departure.get('disruption_ids'):
        for disruption_id in departure.get('disruption_ids', []):
            disruption_id_str = str(disruption_id)
            if disruption_id_str in disruptions:
                disruption_info.append({
                    'title': disruptions[disruption_id_str].get('title', ''),
                    'description': disruptions[disruption_id_str].get('description', '')
                })
    
    # Get route name with fallback
    route_name = 'Unknown'
    if route_info and 'route_name' in route_info:
        route_name = route_info.get('route_name')
    elif route_id == '1':  # Hardcoded fallback for route_id 1
        route_name = 'Alamein'
    
    # Get direction name with fallback
    direction_name = 'Unknown'
    if direction_info and 'direction_name' in direction_info:
        direction_name = direction_info.get('direction_name')
    elif direction_id == '1':  # Hardcoded fallback for direction_id 1
        direction_name = 'City'
    
    formatted_departure = {
        'scheduled_time': scheduled_time.strftime('%H:%M'),
        'live_time': None,
        'destination': destination,
        'platform': departure.get('platform_number', 'Unknown'),
        'at_platform': departure.get('at_platform', False),
        'vehicle': vehicle_info,
        'direction': direction_name,
        'disruptions': disruption_info,
        'route_name': route_name
    }
    
    if estimated_time_utc:
        try:
            estimated_time = datetime.fromisoformat(estimated_time_utc.replace('Z', '+00:00')).astimezone(MELBOURNE_TZ)
            formatted_departure['live_time'] = estimated_time.strftime('%H:%M')
        except Exception as e:
            logger.error(f"Error parsing estimated time {estimated_time_utc}: {e}")
    
    return formatted_departure

def fetch_departures_from_ptv():
    route_type = 0  # 0 is for train
    url = get_ptv_url(f"/v3/departures/route_type/{route_type}/stop/{RIVERSDALE_STOP_ID}?expand=All&max_results=100")
    
    logger.info(f"Fetching from PTV API: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            logger.error("PTV API returned empty data")
            return []
            
        # Log data structure for debugging
        logger.info(f"API response contains keys: {', '.join(data.keys())}")
        
        routes = data.get('routes', {})
        directions = data.get('directions', {})
        runs = data.get('runs', {})
        disruptions = data.get('disruptions', {})
        
        departures = []
        
        raw_departures = data.get('departures', [])
        logger.info(f"Retrieved {len(raw_departures)} total departures from API")
        
        platform1_count = 0
        error_count = 0
        enhancement_errors = 0
        
        for departure in raw_departures:
            # Ensure platform is in string format for comparison
            platform = str(departure.get('platform_number', ''))
            
            if platform != '1':
                continue
                
            platform1_count += 1
            
            # Create a basic departure structure that will work even if the API data is incomplete
            try:
                route_id = str(departure.get('route_id', ''))
                direction_id = str(departure.get('direction_id', ''))
                scheduled_time_utc = departure.get('scheduled_departure_utc')
                
                # Use safer defaults if API data is missing fields
                if direction_id == '1':  # City-bound
                    destination = 'Camberwell'
                else:
                    destination = 'Unknown'
                
                if not scheduled_time_utc:
                    # Use current time + random offset as fallback
                    scheduled_time = get_melbourne_time() + timedelta(minutes=random.randint(15, 120))
                else:
                    scheduled_time = datetime.fromisoformat(scheduled_time_utc.replace('Z', '+00:00')).astimezone(MELBOURNE_TZ)
                
                formatted_departure = {
                    'scheduled_time': scheduled_time.strftime('%H:%M'),
                    'live_time': None,
                    'destination': destination,
                    'platform': platform,
                    'at_platform': departure.get('at_platform', False),
                    'vehicle': None,
                    'direction': 'City' if direction_id == '1' else 'Unknown',
                    'disruptions': [],
                    'route_name': 'Alamein' if route_id == '1' else 'Unknown'
                }
                
                # Try to add live time if available
                estimated_time_utc = departure.get('estimated_departure_utc')
                if estimated_time_utc:
                    try:
                        estimated_time = datetime.fromisoformat(estimated_time_utc.replace('Z', '+00:00')).astimezone(MELBOURNE_TZ)
                        formatted_departure['live_time'] = estimated_time.strftime('%H:%M')
                    except Exception as e:
                        logger.error(f"Error parsing estimated time: {e}")
                
                # Only after creating a valid basic departure, try to enhance it with additional data
                try:
                    enhanced_departure = parse_departure_data(
                        departure, routes, directions, runs, disruptions
                    )
                    # Merge the enhanced data with our basic structure (keeps basic as fallback)
                    formatted_departure.update(enhanced_departure)
                except Exception as e:
                    # Just count enhancement errors rather than logging each one
                    enhancement_errors += 1
                    if enhancement_errors <= 2:  # Only log the first few errors with details
                        logger.warning(f"Could not enhance departure data: {e}")
                
                departures.append(formatted_departure)
            except Exception as e:
                logger.error(f"Error parsing departure data: {e}")
                logger.error(f"Problematic departure data: {departure}")
                error_count += 1
        
        if enhancement_errors > 0:
            logger.warning(f"Could not enhance {enhancement_errors} departures due to missing data in PTV API response")
        
        logger.info(f"Found {platform1_count} platform 1 departures, successfully parsed {len(departures)}, errors: {error_count}")
        
        departures.sort(key=lambda x: x['scheduled_time'])
        return departures
    
    except Exception as e:
        logger.error(f"Error fetching from PTV API: {e}")
        if 'response' in locals():
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response text: {response.text[:500]}")
        return []

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
        
        status = "🟢 AT PLATFORM" if dep.get('at_platform') else ""
        
        train_info = []
        if dep.get('vehicle'):
            train_info.append(dep['vehicle'])
        
        disruption_str = ""
        if dep.get('disruptions'):
            disruption_str = "⚠️ DISRUPTION"
        
        logger.info(f"   {time_str} → {dep['destination']} {status} {disruption_str}")
        if train_info:
            logger.info(f"      {' | '.join(train_info)}")
    
    logger.info("\n" + "=" * 45)
    logger.info(f"Total trains: {len(departures)}")
    logger.info(f"Scraped at: {get_melbourne_time().strftime('%H:%M')} Melbourne time")

def save_to_json(departures):
    if not departures:
        return None
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    filename = data_dir / f"departures_{get_melbourne_time().strftime('%Y%m%d_%H%M')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(departures, f, indent=2)
    
    return filename

def update_cache():
    while True:
        try:
            logger.info("Starting cache update")
            cache['updating'] = True
            departures = fetch_departures_from_ptv()
            if departures:
                cache['departures'] = departures
                cache['last_updated'] = get_melbourne_time().strftime("%H:%M")
                logger.info(f"Cache updated at {cache['last_updated']}")
                print_timetable(departures)
                save_to_json(departures)
            cache['updating'] = False
            time.sleep(300)  # Update every 5 minutes
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
            cache['updating'] = False
            time.sleep(60)  # Wait 1 minute before retrying if there's an error

def test_api_call():
    print("\n===== TESTING PTV API CONNECTION =====")
    print(f"API Base URL: {PTV_BASE_URL}")
    print(f"Using Dev ID: {DEV_ID}")
    print(f"Station ID: {RIVERSDALE_STOP_ID}")
    
    print("\nFetching departures from Riversdale Station Platform 1 (city-bound)...")
    
    try:
        departures = fetch_departures_from_ptv()
        
        if departures:
            print("\n🚂 PLATFORM 1 CITY-BOUND DEPARTURES:")
            print("=" * 60)
            print(f"{'Time':<10} {'Live':<10} {'Destination':<30} {'Status'}")
            print("-" * 60)
            
            for dep in departures:
                time_str = dep['scheduled_time']
                live_str = dep['live_time'] if dep['live_time'] else 'N/A'
                dest_str = dep['destination']
                status = "AT PLATFORM" if dep.get('at_platform') else ""
                
                print(f"{time_str:<10} {live_str:<10} {dest_str:<30} {status}")
            
            print("-" * 60)
            print(f"Total trains: {len(departures)}")
            print(f"Retrieved at: {get_melbourne_time().strftime('%H:%M')} Melbourne time")
            print("\n✅ Departures fetch successful!")
            return departures
        else:
            print("⚠️ No Platform 1 departures found. This could be normal (e.g., late night) or an error.")
            return []
    except Exception as e:
        print(f"❌ Departures fetch failed: {e}")
        return []

def start_background_thread():
    thread = threading.Thread(target=update_cache, daemon=True)
    thread.start()
    return thread

@app.route('/api/health')
def health_check():
    health_url = get_ptv_url("/v3/version")
    try:
        response = requests.get(health_url)
        response.raise_for_status()
        return jsonify({"status": "healthy", "ptv_status": response.json()})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

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
    return jsonify(response_data)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'test':
        test_api_call()
        sys.exit(0)
    
    logger.info("Starting Platform 1 Cafe Train Departures API")
    background_thread = start_background_thread()
    atexit.register(lambda: setattr(background_thread, "_stop", True))
    
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"API Server starting on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port)