import os, time, csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
LOGIN_TOKEN = '"' + os.getenv('login_token') + '"'

options = Options()
options.add_experimental_option("detach", True)
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)
driver.get("https://play.slidysim.com/")
time.sleep(1)
driver.execute_script(f"window.localStorage.setItem('login_token', '{LOGIN_TOKEN}');")
driver.refresh()
time.sleep(1)

try:
    WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Ranking']"))).click()
except:
    for btn in driver.find_elements(By.CSS_SELECTOR, "button.tab"):
        if btn.text == "Ranking":
            btn.click()
            break

def set_input(field, val=""):
    try:
        label = driver.find_element(By.XPATH, f"//label[text()='{field}']")
        inp = label.find_element(By.XPATH, "./following-sibling::div//input[@class='value padded rounded outlined']")
        inp.clear()
        if val: inp.send_keys(val)
    except: pass

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
            label = driver.find_element(By.XPATH, f"//label[text()='{field}']")
            sel = label.find_element(By.XPATH, "./following-sibling::div//select")
        
        driver.execute_script("arguments[0].scrollIntoView(true);", sel)
        time.sleep(0.3)
        sel.click()
        time.sleep(0.3)
        sel.find_element(By.XPATH, f".//option[text()='{opt}']").click()
    except: 
        pass

def set_multi(field, opts):
    try:
        label = driver.find_element(By.XPATH, f"//label[text()='{field}']")
        cont = label.find_element(By.XPATH, "./following-sibling::div//div[@class='multi-select-container value']")
        driver.execute_script("arguments[0].scrollIntoView(true);", cont)
        time.sleep(0.5)
        btn = cont.find_element(By.CLASS_NAME, "multi-select-button")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)
        content = cont.find_element(By.CLASS_NAME, "multi-select-content")
        for cb in content.find_elements(By.XPATH, ".//input[@type='checkbox']"):
            if cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
        for opt in opts:
            try:
                cb = content.find_element(By.XPATH, f".//input[@value='{opt}']")
                driver.execute_script("arguments[0].click();", cb)
            except: pass
        driver.execute_script("arguments[0].click();", btn)
    except: pass

def set_check(field, val=True):
    try:
        label = driver.find_element(By.XPATH, f"//label[text()='{field}']")
        cb = label.find_element(By.XPATH, "./following-sibling::div//input[@type='checkbox']")
        driver.execute_script("arguments[0].scrollIntoView(true);", cb)
        time.sleep(0.3)
        if (val and not cb.is_selected()) or (not val and cb.is_selected()):
            driver.execute_script("arguments[0].click();", cb)
    except: pass

def get_data(stat, device, is_fmc=False):
    try:
        btn = driver.find_element(By.XPATH, "//button[text()='Submit']")
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)
        table = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.CLASS_NAME, "ranking-table")))
        soup = BeautifulSoup(table.get_attribute('outerHTML'), 'html.parser')
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
    except: return []

print("Setting form...")
set_input("Username:")
set_input("Size:")
set_dropdown("Solve type:", "Standard")
set_multi("Display type:", ["Standard","Minimal","RowMinimal","FringeMinimal","Inverse","Manhattan","Arrows","IncrementalArrows","InverseArrows","Rgb","Chess","Flashlight","AdjacentSum","LastMove","Fading","Vanishing" "Minesweeper","MinimalUnsolved","MaximalUnsolved","RowsAndColumns","Cyclic","Divisible"])
set_multi("Moves:", ["Single","Multi","Lines"])
set_multi("Move set:", ["Standard", "VerticalMultiTile"])
set_multi("Solved state:", ["Standard", "Rows", "SquareFringe", "SplitSquareFringe", "Checkerboard"])
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
    
    for config in relay_configs:
        print(f"\n--- Processing config: {config} with device {device} ---")
        
        set_multi("Relay type:", config["relay_types"])
        set_input("Marathon length:")
        
        set_check("Include subcategory PBs:", config["include_subcategory"])
        
        time.sleep(1)
        
        for stat in ["Time", "Moves", "TPS"]:
            set_dropdown("Statistic:", stat)
            time.sleep(1)
            
            data = get_data(stat, device, is_fmc=False)
            all_data.extend(data)
            print(f"Retrieved {len(data)} records for {stat} on {device}")
            
            time.sleep(1)

# ============ FMC RUNS ============
print("\n" + "="*60)
print("STARTING FMC DATA COLLECTION")
print("="*60)

# Set Solve type to FewestMoves
set_dropdown("Solve type:", "Fewest moves")
time.sleep(1)

# Set Show optimal length to Stm and Mtm
set_multi("Show optimal length:", ["Stm", "Mtm"])
time.sleep(1)

# Set Statistic to NumOptimalsThenSolveTime (only statistic needed for FMC)
set_dropdown("Statistic:", "Number of optimals")
time.sleep(1)

for device in devices:
    print(f"\n=== Processing FMC for device: {device} ===")
    set_multi("Device:", [device])
    
    for config in relay_configs:
        print(f"\n--- Processing FMC config: {config} with device {device} ---")
        
        set_multi("Relay type:", config["relay_types"])
        set_input("Marathon length:")
        
        set_check("Include subcategory PBs:", config["include_subcategory"])
        
        time.sleep(1)
        
        # Only one statistic for FMC
        data = get_data("Number of optimals", device, is_fmc=True)
        all_data.extend(data)
        print(f"Retrieved {len(data)} FMC records for {device}")
        
        time.sleep(1)

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
    print(f"   - Standard records: {len([r for r in all_data if r.get('TPS') != '-1'])}")
    print(f"   - FMC records: {len([r for r in all_data if r.get('Optimals') != '-1'])}")
else:
    print("No data")

driver.quit()