import os, time, csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
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
# Minimal initialisation
driver.execute_script(f"window.localStorage.setItem('login_token', '{LOGIN_TOKEN}');")
driver.refresh()
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.tab")))

# Click Ranking tab
try:
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Ranking']"))).click()
except:
    for btn in driver.find_elements(By.CSS_SELECTOR, "button.tab"):
        if btn.text == "Ranking":
            btn.click()
            break

# ===== HELPERS (optimised for speed) =====
def set_input(field, val=""):
    try:
        label = WebDriverWait(driver, 2).until(
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
        if field == "Statistic:" and opt == "Number of optimals":
            selects = driver.find_elements(By.XPATH, "//label[text()='Statistic:']/following-sibling::div//select")
            sel = selects[1] if len(selects) >= 2 else selects[0]
        else:
            label = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, f"//label[text()='{field}']"))
            )
            sel = label.find_element(By.XPATH, "./following-sibling::div//select")
        Select(sel).select_by_visible_text(opt)
    except Exception as e:
        print(f"Dropdown error ({field}={opt}): {e}")

def set_multi(field, opts):
    """Open multi‑select, deselect all, select desired – all via JS – then close."""
    try:
        label = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, f"//label[text()='{field}']"))
        )
        cont = label.find_element(By.XPATH, "./following-sibling::div//div[@class='multi-select-container value']")
        btn = cont.find_element(By.CLASS_NAME, "multi-select-button")
        # Open dropdown via JS (no scroll)
        driver.execute_script("arguments[0].click();", btn)
        # Wait for dropdown to appear (very short)
        WebDriverWait(cont, 2).until(EC.visibility_of_element_located((By.CLASS_NAME, "multi-select-content")))
        content = cont.find_element(By.CLASS_NAME, "multi-select-content")
        # Deselect all checkboxes using JS
        checkboxes = content.find_elements(By.XPATH, ".//input[@type='checkbox']")
        for cb in checkboxes:
            if cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
        # Select desired options
        for opt in opts:
            try:
                cb = content.find_element(By.XPATH, f".//input[@value='{opt}']")
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
            except:
                pass
        # Close dropdown
        driver.execute_script("arguments[0].click();", btn)
        # No sleep – the JS toggle handles it
    except Exception as e:
        print(f"Multi-select error ({field}={opts}): {e}")

def set_check(field, val=True):
    try:
        label = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, f"//label[text()='{field}']"))
        )
        cb = label.find_element(By.XPATH, "./following-sibling::div//input[@type='checkbox']")
        if (val and not cb.is_selected()) or (not val and cb.is_selected()):
            driver.execute_script("arguments[0].click();", cb)
    except:
        pass

def get_expected_row_count():
    """Return (count, status) by inspecting the value container."""
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
    # Fallback: if table already populated
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, ".ranking-table tbody tr")
        if rows:
            return len(rows), "ready"
    except:
        pass
    return None, "unknown"

def wait_for_table_load(timeout=10):
    """Poll until table rows match expected count, or timeout."""
    start = time.time()
    last_count = 0
    stable = 0
    while time.time() - start < timeout:
        count, status = get_expected_row_count()
        if status == "fetching":
            time.sleep(0.1)
            continue
        if status == "ready" and count is not None:
            try:
                actual = len(driver.find_elements(By.CSS_SELECTOR, ".ranking-table tbody tr"))
                if actual == count and actual > 0:
                    print(f"  ✓ Table loaded: {actual} rows")
                    return True
                if actual > count:
                    print(f"  ✓ Table loaded: {actual} rows (expected {count})")
                    return True
                if count == 0 and actual == 0:
                    print(f"  ℹ No results found (0 rows)")
                    return True
                # Possibly still loading
                if actual > 0:
                    if actual == last_count:
                        stable += 1
                        if stable >= 2:
                            print(f"  ✓ Table loaded: {actual} rows (stable)")
                            return True
                    else:
                        stable = 0
                        last_count = actual
            except:
                pass
        time.sleep(0.2)
    # Timeout – accept whatever is present
    try:
        actual = len(driver.find_elements(By.CSS_SELECTOR, ".ranking-table tbody tr"))
        print(f"  ⚠ Timeout - got {actual} rows")
        return True
    except:
        print("  ⚠ Timeout - no table found")
        return False

def get_data(stat, device, is_fmc=False):
    """Click Submit once and wait for table."""
    try:
        btn = driver.find_element(By.XPATH, "//button[text()='Submit']")
        driver.execute_script("arguments[0].click();", btn)
        wait_for_table_load(timeout=10)
        # Give a tiny moment for rendering (can be 0 if consistently works)
        time.sleep(0.05)
        try:
            table = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ranking-table"))
            )
            soup = BeautifulSoup(table.get_attribute('outerHTML'), 'html.parser')
        except:
            print("  No table found")
            return []

        rows = []
        if is_fmc:
            for tr in soup.select('tbody tr'):
                td = tr.find_all('td')
                if len(td) >= 13:
                    rows.append({
                        'Device': device, 'Statistic': stat,
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
                        'TPS': '-1', 'Display type': '-1'
                    })
        else:
            for tr in soup.select('tbody tr'):
                td = tr.find_all('td')
                if len(td) >= 12:
                    rows.append({
                        'Device': device, 'Statistic': stat,
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
                        'Optimals': '-1', 'Show optimal length': '-1', 'Time limit': '-1'
                    })
        return rows
    except Exception as e:
        print(f"  Error getting data: {e}")
        return []

# ===== SET FILTERS (once, instant) =====
print("Setting up filters...")
set_input("Username:")
set_input("Size:")
set_dropdown("Solve type:", "Standard")

set_multi("Display type:", ["Standard","Minimal","RowMinimal","FringeMinimal","Inverse","Manhattan","Arrows","IncrementalArrows","InverseArrows","Rgb","Chess","Flashlight","AdjacentSum","LastMove","Fading","Vanishing","Minesweeper","MinimalUnsolved","MaximalUnsolved","RowsAndColumns","Cyclic","Divisible"])
set_multi("Device moves:", ["Single","Multi","Lines"])
set_multi("Move set:", ["Standard", "VerticalMultiTile"])
set_multi("Solved state:", ["Standard", "Rows", "SquareFringe", "SplitSquareFringe", "Checkerboard"])
set_multi("Average length:", ["1","5","12","25","50","100","250","500","1000","2500","5000","10000","25000","50000","100000","250000","500000","1000000"])

relay_configs = [
    {"relay_types": ["Single", "Marathon"], "include_subcategory": True},
    {"relay_types": ["Square", "Width", "Height", "WidthHeight"], "include_subcategory": False}
]
devices = ["MouseHover", "MouseClick", "Touch", "Keyboard"]
all_data = []

# ============ STANDARD LOOP ============
print("\n" + "="*60)
print("STANDARD DATA COLLECTION")
print("="*60)
for device in devices:
    set_multi("Device:", [device])
    for config in relay_configs:
        set_multi("Relay type:", config["relay_types"])
        print(f"\n=== Config: {device} {config} ===")
        set_input("Marathon length:")
        set_check("Include subcategory PBs:", config["include_subcategory"])
        # Slight pause only to let the UI settle after relay type change (empirical)
        time.sleep(0.05)
        for stat in ["Time", "Moves", "TPS"]:
            print(f"  {stat} ...")
            set_dropdown("Statistic:", stat)
            time.sleep(0.05)
            data = get_data(stat, device, is_fmc=False)
            all_data.extend(data)
            print(f"    {len(data)} records")

# ============ FMC LOOP ============
print("\n" + "="*60)
print("FMC DATA COLLECTION")
print("="*60)
set_dropdown("Solve type:", "Fewest moves")
set_multi("Show optimal length:", ["Stm", "Mtm"])
# Statistic dropdown for FMC is handled specially inside set_dropdown
set_dropdown("Statistic:", "Number of optimals")
time.sleep(0.1)

for device in devices:
    print(f"\n=== FMC Device: {device} ===")
    set_multi("Device:", [device])
    for config in relay_configs:
        set_multi("Relay type:", config["relay_types"])
        set_input("Marathon length:")
        set_check("Include subcategory PBs:", config["include_subcategory"])
        time.sleep(0.05)
        print("  Number of optimals ...")
        data = get_data("Number of optimals", device, is_fmc=True)
        all_data.extend(data)
        print(f"    {len(data)} records")

# ============ SAVE ============
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
    standard_count = sum(1 for r in all_data if r.get('TPS') != '-1')
    fmc_count = sum(1 for r in all_data if r.get('Optimals') != '-1')
    print(f"\n✅ Saved {len(all_data)} rows ({standard_count} standard, {fmc_count} FMC)")
else:
    print("No data collected")

driver.quit()