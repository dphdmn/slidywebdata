import csv
import re
from datetime import datetime

def convert_size_to_n_m(size_str):
    """Convert '2x2' or '20x20' to (n, m) integers"""
    parts = size_str.lower().split('x')
    return int(parts[0]), int(parts[1])

def convert_relay_type(relay_str):
    """Convert relay type from CSV to target format"""
    if relay_str == "Single":
        return "Standard"
    elif relay_str == "Square relay":
        return "2-N relay"
    elif relay_str == "Width relay":
        return "Width relay"
    elif relay_str == "Height relay":
        return "Height relay"
    elif relay_str == "Width + height relay":
        return "Everything-up-to relay"
    elif "Marathon" in relay_str:
        # Extract number from "x42 Marathon" or similar
        match = re.search(r'x(\d+)\s+Marathon', relay_str)
        if match:
            return f"Marathon {match.group(1)}"
        return relay_str
    else:
        return relay_str

def convert_display_type(display_str):
    """Convert display type from CSV to target format"""
    mapping = {
        "Standard": "Standard",
        "Minimal": "Minimal",
        "Row minimal": "Row minimal",
        "Fringe minimal": "Fringe minimal",
        "Inverse": "Inverse permuation",
        "Manhattan": "Manhattan",
        "Arrows": "Vectors",
        "Incremental arrows": "Incremental vectors",
        "Inverse arrows": "Inverse vectors",
        "RGB": "RGB",
        "Chess": "Chess",
        "Flashlight": "Adjacent tiles",
        "Adjacent sum": "Adjacent sum",
        "Last move": "Last move",
        "Fading": "Fading tiles",
        "Vanishing": "Vanish on solved",
        "Minesweeper": "Minesweeper",
        "Minimal unsolved": "Minimal unsolved",
        "Maximal unsolved": "Maximal unsolved",
        "Rows and columns": "Rows and columns",
        "Cyclic": "Cyclic",
        "Divisible": "Divisible"
    }
    return mapping.get(display_str, display_str)

def convert_statistic(stat_str, show_optimal_length=None):
    """Convert statistic column to target format with FMC support"""
    if stat_str == "Time":
        return "time"
    elif stat_str == "Moves":
        return "move"
    elif stat_str == "TPS":
        return "tps"
    elif stat_str == "Number of optimals":
        if show_optimal_length == "STM":
            return "FMC"
        elif show_optimal_length == "MTM":
            return "FMC MTM"
        else:
            return "fmc"
    else:
        return stat_str.lower()

def check_optimals_valid(optimals_str, relay_str, n, m):
    """Check if optimals value meets requirements for the relay type"""
    try:
        # If it's a floating point number, always bad
        if '.' in str(optimals_str):
            return False
        
        optimals = int(float(optimals_str))
        
        if relay_str == "Single":
            return optimals == 1
        elif relay_str == "Square relay":
            return optimals == (n - 1)
        elif relay_str == "Width relay":
            return optimals == (n - 1)
        elif relay_str == "Height relay":
            return optimals == (m - 1)
        elif relay_str == "Width + height relay":
            return optimals == (m - 1) * (n - 1)
        elif "Marathon" in relay_str:
            # Extract marathon length
            match = re.search(r'x(\d+)\s+Marathon', relay_str)
            if match:
                marathon_length = int(match.group(1))
                return optimals == marathon_length
            return False
        else:
            return True
    except (ValueError, TypeError):
        return False

def convert_tps(tps_str, moves=None, time_ms=None, is_fmc=False):
    """Convert TPS value, with special handling for FMC"""
    if is_fmc:
        # Calculate TPS manually: moves / time (in seconds)
        if moves and time_ms and time_ms > 0:
            tps_float = moves / (time_ms / 1000)  # moves / seconds
            return int(tps_float * 1000)  # Multiply by 1000 and ignore decimals
        return -1
    else:
        if tps_str == "∞" or tps_str == "inf":
            return 2147483647
        try:
            return int(float(tps_str) * 1000)
        except (ValueError, TypeError):
            return 2147483647

def convert_average_length(avg_str):
    return 1 if avg_str == "Single" else int(avg_str.replace("Average of ", ""))

def convert_timestamp(timestamp_str):
    """Convert timestamp string to Unix timestamp in milliseconds"""
    try:
        # Parse format like "2026-04-05 12:44:58 PM"
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %I:%M:%S %p")
        # Convert to Unix timestamp in milliseconds
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return -1

def read_and_convert_csv(input_file, output_file):
    """Read CSV and convert to target format"""
    results = []
    
    with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            # Check if this is FMC data
            is_fmc = row['Statistic'] == "Number of optimals"
            
            # ITEM 2 & 3: N and M from Size (needed early for optimals check)
            n, m = convert_size_to_n_m(row['Size'])
            
            # ITEM 4: relay type
            item4 = convert_relay_type(row['Relay type'])
            
            # For FMC: Check if optimals are valid before processing
            if is_fmc:
                optimals_valid = check_optimals_valid(
                    row['Optimals'], 
                    row['Relay type'], 
                    n, m
                )
                if not optimals_valid:
                    continue  # Skip invalid FMC entries
            
            # ITEM 1: statistic type (with FMC support)
            if is_fmc:
                show_optimal_length = row.get('Show optimal length', '')
                item1 = convert_statistic(row['Statistic'], show_optimal_length)
            else:
                item1 = convert_statistic(row['Statistic'])
            
            # ITEM 5: display type - modified logic with Solved state
            move_set = row.get('Move set', '')
            display_type = row.get('Display type', '')
            solved_state = row.get('Solved state', '')

            non_standard_states = ["Rows", "Square fringe", "Split square fringe", "Checkerboard"]

            # Ignore any row with non-standard solved state mixed with anything non-standard
            if solved_state in non_standard_states:
                if move_set != "Standard" or display_type != "Standard":
                    continue
                else:
                    item5 = solved_state
            elif move_set == "Vertical multi-tile":
                if display_type == "Standard":
                    item5 = "Vertical multi-tile"
                else:
                    continue
            else:
                item5 = convert_display_type(display_type)
                
            if display_type == "-1":
                item5 = "Standard" #otherwise fmc breaks

            item6 = row['Username']
            
            # ITEM 7: Time * 1000 (integer)
            try:
                t = row['Time']
                if isinstance(t, str) and ':' in t:
                    parts = list(map(float, t.replace(':', ' ').split()))
                    seconds = parts[-2] * 60 + parts[-1] if len(parts) == 2 else parts[-3] * 3600 + parts[-2] * 60 + parts[-1]
                    item7 = int(seconds * 1000)
                else:
                    item7 = int(float(t) * 1000)
            except (ValueError, TypeError):
                item7 = -1
            
            # ITEM 8: Moves * 1000 (integer)
            try:
                item8 = int(float(row['Moves']) * 1000)
            except (ValueError, TypeError):
                item8 = -1
            
            # ITEM 9: TPS * 1000 (integer)
            if is_fmc:
                # Calculate TPS from moves and time for FMC
                item9 = convert_tps(None, item8/1000, item7, is_fmc=True)
            else:
                item9 = convert_tps(row['TPS'])
            
            # ITEM 10: average length as integer
            item10 = convert_average_length(row['Average length'])
            
            # ITEM 11: based on device column
            device_map = {
                "MouseHover": "Mouse",
                "MouseClick": "Click",
                "Touch": "Touch",
                "Keyboard": "Keyboard"
            }
            item11 = device_map.get(row['Device'], row['Device'])
            
            # ITEM 12: timestamp in milliseconds
            item12 = convert_timestamp(row['Timestamp'])
            
            # Create the converted row
            converted_row = [item1, n, m, item4, item5, item6, item7, item8, item9, item10, item11, item12]
            results.append(converted_row)
    
    # Write results to dumbified.txt
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("[")
        for i, row in enumerate(results):
            # Convert row to string representation
            row_str = "[" + ", ".join([
                f'"{row[0]}"' if isinstance(row[0], str) else str(row[0]),
                str(row[1]),
                str(row[2]),
                f'"{row[3]}"',
                f'"{row[4]}"',
                f'"{row[5]}"',
                str(row[6]),
                str(row[7]),
                str(row[8]),
                str(row[9]),
                f'"{row[10]}"',
                str(row[11])
            ]) + "]"
            
            # Add comma for all but the last row
            if i < len(results) - 1:
                row_str += ","
            
            outfile.write(row_str)
        outfile.write("]")
    
    print(f"Converted {len(results)} rows to {output_file}")

# Run the conversion
if __name__ == "__main__":
    input_csv = "ranking_data.csv"  # Change this to your CSV filename
    output_file = "dumbified.txt"
    
    try:
        read_and_convert_csv(input_csv, output_file)
        print("Conversion completed successfully!")
    except FileNotFoundError:
        print(f"Error: Could not find {input_csv}")
        print("Please make sure the CSV file is in the same directory or update the filename.")
    except Exception as e:
        print(f"An error occurred: {e}")