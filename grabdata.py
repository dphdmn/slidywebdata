import os, time, csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re

load_dotenv()
LOGIN_TOKEN = '"' + os.getenv('login_token') + '"'

options = Options()
options.add_experimental_option("detach", True)
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)
driver.get("https://play.slidysim.com/")
time.sleep(1)
driver.execute_script(f"window.localStorage.setItem('login_token', '{LOGIN_TOKEN}');")
driver.refresh()
time.sleep(1)

try:
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Ranking']"))).click()
except:
    for btn in driver.find_elements(By.CSS_SELECTOR, "button.tab"):
        if btn.text == "Ranking":
            btn.click()
            break

def wait_for_stable_ui(seconds=0.5):
    """Brief pause for UI stability"""
    time.sleep(seconds)

def set_input(field, val=""):
    try:
        label = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, f"//label[text()='{field}']"))
        )
        inp = label.find_element(By.XPATH, "./following-sibling::div//input[@class='value padded rounded outlined']")
        inp.clear()
        if val: 
            inp.send_keys(val)
    except: 
        pass

def set_dropdown(field, opt):
    try:
        # Special case for FMC statistic when "Fewest moves" is active
        if field == "Statistic:" and opt == "Number of optimals":
            # Find all statistic selects and use the second one (FMC version)
            selects = driver.find_elements(By.XPATH, "//label[text()='Statistic:']/following-sibling::div//select")
            if len(selects) >= 2:
                sel = selects[1]  # Second statistic dropdown (FMC)
            else:
                sel = selects[0]  # Fallback to first if only one exists
        else:
            label = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, f"//label[text()='{field}']"))
            )
            sel = label.find_element(By.XPATH, "./following-sibling::div//select")
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sel)
        wait_for_stable_ui(0.2)
        
        # Click the select to open dropdown
        sel.click()
        wait_for_stable_ui(0.3)
        
        # Wait for and click the desired option
        option = WebDriverWait(sel, 3).until(
            EC.presence_of_element_located((By.XPATH, f".//option[text()='{opt}']"))
        )
        option.click()
        wait_for_stable_ui(0.2)
    except Exception as e: 
        print(f"Dropdown error ({field}={opt}): {e}")
        pass

def set_multi(field, opts):
    try:
        label = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, f"//label[text()='{field}']"))
        )
        cont = label.find_element(By.XPATH, "./following-sibling::div//div[@class='multi-select-container value']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cont)
        wait_for_stable_ui(0.3)
        
        btn = cont.find_element(By.CLASS_NAME, "multi-select-button")
        driver.execute_script("arguments[0].click();", btn)
        wait_for_stable_ui(0.5)
        
        content = cont.find_element(By.CLASS_NAME, "multi-select-content")
        # Deselect all checkboxes first
        checkboxes = content.find_elements(By.XPATH, ".//input[@type='checkbox']")
        for cb in checkboxes:
            if cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
                wait_for_stable_ui(0.05)
        
        # Select desired options
        for opt in opts:
            try:
                cb = content.find_element(By.XPATH, f".//input[@value='{opt}']")
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
                    wait_for_stable_ui(0.05)
            except: 
                pass
        
        # Close the multi-select
        driver.execute_script("arguments[0].click();", btn)
        wait_for_stable_ui(0.3)
    except Exception as e: 
        print(f"Multi-select error ({field}={opts}): {e}")
        pass

def set_check(field, val=True):
    try:
        label = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, f"//label[text()='{field}']"))
        )
        cb = label.find_element(By.XPATH, "./following-sibling::div//input[@type='checkbox']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cb)
        wait_for_stable_ui(0.2)
        if (val and not cb.is_selected()) or (not val and cb.is_selected()):
            driver.execute_script("arguments[0].click();", cb)
            wait_for_stable_ui(0.2)
    except: 
        pass

def get_expected_row_count():
    """Extract the expected number of rows from the value container"""
    try:
        # Try multiple selectors for the value container
        selectors = [
            ".value-container .value",
            ".value-container", 
            "[class*='value-container']",
            "div.value"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if "Fetching" in text or "fetching" in text:
                        return None, "fetching"
                    
                    if "Fetched" in text or "fetched" in text:
                        match = re.search(r'(\d+)', text)
                        if match:
                            return int(match.group(1)), "ready"
            except:
                continue
        
        # If we can't find the container, check if table exists with rows
        try:
            table = driver.find_element(By.CLASS_NAME, "ranking-table")
            tbody = table.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            if len(rows) > 0:
                return len(rows), "ready"  # Table already has data
        except:
            pass
            
        return None, "unknown"
    except:
        return None, "error"

def wait_for_table_load(expected_count=None, timeout=10):
    """Wait for table to finish loading and verify row count"""
    start_time = time.time()
    last_row_count = 0
    stable_count = 0
    
    while time.time() - start_time < timeout:
        try:
            # Check the value container
            count, status = get_expected_row_count()
            
            if status == "fetching":
                print(f"  Still loading... ({time.time()-start_time:.1f}s)")
                time.sleep(0.3)
                continue
            
            # Check if table is present
            try:
                table = driver.find_element(By.CLASS_NAME, "ranking-table")
                tbody = table.find_element(By.TAG_NAME, "tbody")
                rows = tbody.find_elements(By.TAG_NAME, "tr")
                actual_count = len(rows)
                
                # If we have a count from the container, verify it matches
                if count is not None and status == "ready":
                    if actual_count == count and actual_count > 0:
                        print(f"  ✓ Table loaded: {actual_count} rows match expected {count}")
                        return True
                    elif actual_count > count:
                        # More rows than expected, but table is loaded
                        print(f"  ✓ Table loaded: {actual_count} rows (expected {count})")
                        return True
                    elif actual_count == 0 and count > 0:
                        # Hasn't loaded yet
                        pass
                    elif actual_count == count == 0:
                        # Legitimate empty result
                        print(f"  ℹ No results found (0 rows)")
                        return True
                    else:
                        print(f"  Mismatch: got {actual_count} rows, expected {count}")
                
                # No count reference available or count not matching
                if actual_count > 0:
                    # Check if row count is stable (same for 3 consecutive checks)
                    if actual_count == last_row_count:
                        stable_count += 1
                        if stable_count >= 2:  # Stable for 2 checks
                            print(f"  ✓ Table loaded: {actual_count} rows (stable)")
                            return True
                    else:
                        stable_count = 0
                        last_row_count = actual_count
                
            except:
                pass
                
        except (StaleElementReferenceException, Exception) as e:
            pass
        
        time.sleep(0.5)
    
    # Timeout - final check
    try:
        table = driver.find_element(By.CLASS_NAME, "ranking-table")
        tbody = table.find_element(By.TAG_NAME, "tbody")
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        actual_count = len(rows)
        print(f"  ⚠ Timeout - got {actual_count} rows")
        return True  # Return whatever we have
    except:
        print(f"  ⚠ Timeout - no table found")
        return False

def get_data(stat, device, is_fmc=False):
    try:
        btn = driver.find_element(By.XPATH, "//button[text()='Submit']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        wait_for_stable_ui(0.3)
        driver.execute_script("arguments[0].click();", btn)
        
        # Wait for table to fully load with retry mechanism
        max_retries = 1  # Reduced retries to avoid excessive delays
        for attempt in range(max_retries + 1):
            if wait_for_table_load(timeout=8):
                break
            else:
                if attempt < max_retries:
                    print(f"  Retrying submission...")
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
        
        # Get the table
        try:
            table = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ranking-table"))
            )
            soup = BeautifulSoup(table.get_attribute('outerHTML'), 'html.parser')
        except:
            print(f"  No table found")
            return []
        
        rows = []
        
        if is_fmc:
            # FMC table headers: Username, Time, Moves, Optimals, Size, Average length, Relay type, Show optimal length, Time limit, Solved state, Scrambler, Move set, Timestamp
            for tr in soup.select('tbody tr'):
                td = tr.find_all('td')
                if len(td) >= 13:
                    rows.append({
                        'Device': device,
                        'Statistic': stat,
                        'Username': td[0].get_text(strip=True),
                        'Time': td[1].get_text(strip=True),
                        'Moves': td[2].get_text(strip=True),
                        'Optimals': td[3].get_text(strip=True),
                        'Size': td[4].get_text(strip=True),
                        'Average length': td[5].get_text(strip=True),
                        'Relay type': td[6].get_text(strip=True),
                        'Show optimal length': td[7].get_text(strip=True),
                        'Time limit': td[8].get_text(strip=True),
                        'Solved state': td[9].get_text(strip=True),
                        'Scrambler': td[10].get_text(strip=True),
                        'Move set': td[11].get_text(strip=True),
                        'Timestamp': td[12].get_text(strip=True),
                        # Standard fields set to -1 for FMC rows
                        'TPS': '-1',
                        'Display type': '-1'
                    })
        else:
            # Standard table headers
            for tr in soup.select('tbody tr'):
                td = tr.find_all('td')
                if len(td) >= 12:
                    rows.append({
                        'Device': device,
                        'Statistic': stat,
                        'Username': td[0].get_text(strip=True),
                        'Time': td[1].get_text(strip=True),
                        'Moves': td[2].get_text(strip=True),
                        'TPS': td[3].get_text(strip=True),
                        'Size': td[4].get_text(strip=True),
                        'Average length': td[5].get_text(strip=True),
                        'Relay type': td[6].get_text(strip=True),
                        'Display type': td[7].get_text(strip=True),
                        'Solved state': td[8].get_text(strip=True),
                        'Scrambler': td[9].get_text(strip=True),
                        'Move set': td[10].get_text(strip=True),
                        'Timestamp': td[11].get_text(strip=True),
                        # FMC fields set to -1 for standard rows
                        'Optimals': '-1',
                        'Show optimal length': '-1',
                        'Time limit': '-1'
                    })
        return rows
    except Exception as e:
        print(f"  Error getting data: {e}")
        return []

print("Setting form...")
# Set defaults faster by removing unnecessary scroll waits
set_input("Username:")
set_input("Size:")
set_dropdown("Solve type:", "Standard")
wait_for_stable_ui(0.3)

set_multi("Display type:", ["Standard","Minimal","RowMinimal","FringeMinimal","Inverse","Manhattan","Arrows","IncrementalArrows","InverseArrows","Rgb","Chess","Flashlight","AdjacentSum","LastMove","Fading","Vanishing","Minesweeper","MinimalUnsolved","MaximalUnsolved","RowsAndColumns","Cyclic","Divisible"])
wait_for_stable_ui(0.3)
set_multi("Device moves:", ["Single","Multi","Lines"])
set_multi("Move set:", ["Standard", "VerticalMultiTile"])
set_multi("Solved state:", ["Standard", "Rows", "SquareFringe", "SplitSquareFringe", "Checkerboard"])
wait_for_stable_ui(0.3)
set_multi("Average length:", ["1","5","12","25","50","100","250","500","1000","2500","5000","10000","25000","50000","100000","250000","500000","1000000"])

relay_configs = [
    {
        "relay_types": ["Single", "Marathon"],
        "include_subcategory": True
    },
    {
        "relay_types": ["Square", "Width", "Height", "WidthHeight"],
        "include_subcategory": False
    }
]

devices = ["MouseHover", "MouseClick", "Touch", "Keyboard"]
all_data = []

# ============ STANDARD RUNS (Time, Moves, TPS) ============
print("\n" + "="*60)
print("STARTING STANDARD DATA COLLECTION")
print("="*60)

for device in devices:
    print(f"\n=== Processing device: {device} ===")
    set_multi("Device:", [device])
    wait_for_stable_ui(0.3)
    
    for config in relay_configs:
        print(f"\n--- Processing config: {config} with device {device} ---")
        
        set_multi("Relay type:", config["relay_types"])
        set_input("Marathon length:")
        set_check("Include subcategory PBs:", config["include_subcategory"])
        wait_for_stable_ui(0.5)
        
        for stat in ["Time", "Moves", "TPS"]:
            print(f"  Getting {stat}...")
            set_dropdown("Statistic:", stat)
            wait_for_stable_ui(0.5)
            
            data = get_data(stat, device, is_fmc=False)
            all_data.extend(data)
            print(f"  ✓ Retrieved {len(data)} records for {stat} on {device}")
            wait_for_stable_ui(0.3)

# ============ FMC RUNS ============
print("\n" + "="*60)
print("STARTING FMC DATA COLLECTION")
print("="*60)

# Set Solve type to FewestMoves
set_dropdown("Solve type:", "Fewest moves")
wait_for_stable_ui(0.5)

# Set Show optimal length to Stm and Mtm
set_multi("Show optimal length:", ["Stm", "Mtm"])
wait_for_stable_ui(0.5)

# Set Statistic to NumOptimalsThenSolveTime (only statistic needed for FMC)
set_dropdown("Statistic:", "Number of optimals")
wait_for_stable_ui(0.5)

for device in devices:
    print(f"\n=== Processing FMC for device: {device} ===")
    set_multi("Device:", [device])
    wait_for_stable_ui(0.3)
    
    for config in relay_configs:
        print(f"\n--- Processing FMC config: {config} with device {device} ---")
        
        set_multi("Relay type:", config["relay_types"])
        set_input("Marathon length:")
        set_check("Include subcategory PBs:", config["include_subcategory"])
        wait_for_stable_ui(0.5)
        
        print(f"  Getting Number of optimals...")
        # Only one statistic for FMC
        data = get_data("Number of optimals", device, is_fmc=True)
        all_data.extend(data)
        print(f"  ✓ Retrieved {len(data)} FMC records for {device}")
        wait_for_stable_ui(0.3)

# Define all possible fields for CSV (union of standard and FMC fields)
fieldnames = [
    'Device', 'Statistic', 'Username', 'Time', 'Moves', 'TPS', 'Optimals',
    'Size', 'Average length', 'Relay type', 'Display type', 'Show optimal length',
    'Time limit', 'Solved state', 'Scrambler', 'Move set', 'Timestamp'
]

if all_data:
    with open("ranking_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval='-1')
        writer.writeheader()
        writer.writerows(all_data)
    print(f"\n✅ Saved {len(all_data)} total rows to ranking_data.csv")
    standard_count = len([r for r in all_data if r.get('TPS') != '-1'])
    fmc_count = len([r for r in all_data if r.get('Optimals') != '-1'])
    print(f"   - Standard records: {standard_count}")
    print(f"   - FMC records: {fmc_count}")
else:
    print("No data collected")

driver.quit()