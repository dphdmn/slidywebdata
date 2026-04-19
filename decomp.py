import zlib
import json
import sys
import os
import lzma
from datetime import datetime
import logging
import sys
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeaderboardCombiner:
    def __init__(self, input_folder):
        self.input_folder = input_folder
        self.base_name = os.path.basename(input_folder).replace('_output', '')
        
    def read_all_files(self):
        """Read all 240 files and combine them into a single data structure"""
        all_data = {}
        successful_reads = 0
        failed_reads = 0
        
        # Parameter ranges (same as what we generated)
        display_types = range(1, 28)  # 1 to 20 (22 now) (27 now)
        control_types = range(0, 6)   # 0 to 3 (5 now)
        pb_types = range(1, 6)        # 1 to 3 (to 5 now)
        
        logger.info(f"Reading files from: {self.input_folder}")
        
        for dt in display_types:
            for ct in control_types:
                for pt in pb_types:
                    # Construct filename
                    filename = f"{dt}_{ct}_{pt}"
                    file_path = os.path.join(self.input_folder, filename)
                    
                    try:
                        # Read the file content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read().strip()
                        
                        # Store the content with the combination key
                        key = f"{dt}_{ct}_{pt}"
                        all_data[key] = file_content
                        successful_reads += 1
                        
                        # Progress update
                        current_progress = successful_reads + failed_reads
                            
                    except Exception as e:
                        failed_reads += 1
                        logger.error(f"Failed to read {filename}: {e}")
        
        logger.info(f"File reading completed: {successful_reads} successful, {failed_reads} failed")
        return all_data
    
    def compress_and_save_archive(self, all_data):
        """Compress all data using LZMA with maximum compression"""
        try:
            # Create archive structure similar to the other project
            archive_data = {
                "timestamp": datetime.now().isoformat(),
                "data": all_data
            }
            
            # Convert to JSON with minimal whitespace
            json_data = json.dumps(archive_data, separators=(',', ':'))
            original_size = len(json_data.encode('utf-8'))
            
            # Create combined_archives directory if it doesn't exist
            output_dir = "combined_archives"
            os.makedirs(output_dir, exist_ok=True)
            
            # Create subfolder based on original filename
            archive_folder = os.path.join(output_dir, self.base_name)
            os.makedirs(archive_folder, exist_ok=True)
            
            # Add date to filename
            current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"combined_leaderboard_{current_date}.lzma"
            archive_path = os.path.join(archive_folder, archive_filename)
            
            # Compress with LZMA using maximum compression
            with lzma.open(archive_path, 'wb', preset=9) as f:
                f.write(json_data.encode('utf-8'))
            
            compressed_size = os.path.getsize(archive_path)
            compression_ratio = (compressed_size / original_size) * 100
            
            logger.info(f"Combined LZMA archive saved: {archive_path}")
            logger.info(f"Compression: {original_size:,} → {compressed_size:,} bytes ({compression_ratio:.1f}%)")
            
            # Also save a JSON version for debugging
            json_filename = f"combined_leaderboard_{current_date}.json"
            json_path = os.path.join(archive_folder, json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=2)
            
            logger.info(f"Debug JSON saved: {json_path}")
            
            return archive_path
            
        except Exception as e:
            logger.error(f"Failed to compress archive: {e}")
            return None
    
    def combine_and_compress(self):
        """Main method to combine all files and create compressed archive"""
        if not os.path.exists(self.input_folder):
            logger.error(f"Input folder not found: {self.input_folder}")
            return False
        
        # Read all files
        all_data = self.read_all_files()
        
        if not all_data:
            logger.error("No data found to compress!")
            return False
        
        # Compress and save
        archive_path = self.compress_and_save_archive(all_data)
        
        if archive_path:
            logger.info(f"Successfully created combined archive: {archive_path}")
            return True
        else:
            logger.error("Failed to create combined archive")
            return False

def load_zlib_file(filename):
    """Load and decompress zlib file, return parsed data"""
    try:
        with open(filename, 'rb') as f:
            compressed_data = f.read()
        
        #decompressed_data = zlib.decompress(compressed_data)
        decompressed_data = compressed_data
        # The data appears to be JSON format based on your example
        json_string = decompressed_data.decode('utf-8')
        raw_data = json.loads(json_string)
        
        return raw_data
        
    except Exception as e:
        print(f"Error loading file {filename}: {e}")
        return None

def generate_user_map(raw_data):
    """Generate unique user IDs for each username"""
    user_map = {}
    user_id_counter = 1
    
    for row in raw_data:
        if len(row) > 5:  # Make sure we have at least the user field
            username = row[5]  # username is at index 5
            if username and username not in user_map:
                user_map[username] = user_id_counter
                user_id_counter += 1
    
    return user_map

def convert_to_dicts(raw_data, user_map):
    """Convert raw data list to list of dictionaries with user IDs instead of usernames"""
    leaderboard = []
    
    for row in raw_data:
        if len(row) >= 12:  # Based on your example structure
            username = row[5]
            user_id = user_map.get(username, 0)  # Use 0 if user not found (shouldn't happen)
            
            entry = {
                "pbtype": row[0] if len(row) > 0 else "tps",  # Use actual pbtype from data
                "width": int(row[1]),           # 9, 10, 8, etc.
                "height": int(row[2]),          # 9, 10, 8, etc.
                "solvetype": row[3],            # "Standard", "Marathon 42"
                "displaytype": row[4],          # "Standard"
                "userid": user_id,              # User ID instead of username
                "time": int(row[6]),            # 63046, 77917, etc.
                "moves": int(row[7]),           # 1392357, 1847663, etc.
                "tps": int(row[8]),             # 22194, 23743, etc.
                "avglen": int(row[9]),          # 100
                "controls": row[10],            # "Mouse", "Keyboard"
                "timestamp": int(row[11])       # 1680200481059, etc.
            }
            leaderboard.append(entry)
    
    return leaderboard

def filter_by_controls(data, controls_type):
    """Filter data by controls type"""
    if controls_type == "both":
        return [entry for entry in data if entry["controls"] in ["Mouse", "Click", "Touch", "Keyboard"]]
    else:
        control_map = {"keyboard": "Keyboard", "mouse": "Mouse", "click": "Click", "touch": "Touch"}
        return [entry for entry in data if entry["controls"] == control_map.get(controls_type, controls_type)]

def filter_by_display_type(data, display_type):
    """Filter data by display type"""
    return [entry for entry in data if entry["displaytype"] == display_type]

def filter_by_pb_type(data, pb_type):
    """Filter data by pb type"""
    return [entry for entry in data if entry["pbtype"] == pb_type]

def is_better_pb(existing_entry, new_entry):
    """Check if new_entry is a better PB than existing_entry based on pbtype"""
    pbtype = new_entry["pbtype"]
    
    if pbtype == "tps":
        # For tps, higher value is better
        return new_entry["tps"] > existing_entry["tps"]
    elif pbtype in ["time", "FMC", "FMC MTM"]:
        # For time, FMC, and FMC MTM, lower value is better
        return new_entry["time"] < existing_entry["time"]
    elif pbtype == "move":
        # For moves, lower value is better
        return new_entry["moves"] < existing_entry["moves"]
    else:
        # Default: assume lower is better
        return new_entry["time"] < existing_entry["time"]

def get_unique_pbs(data):
    """Generate unique PBs - only keep the best entry for each user per configuration"""
    unique_entries = {}
    
    for entry in data:
        # Create a unique key based on these fields (excluding controls and the value fields)
        key = (
            entry["pbtype"],
            entry["width"],
            entry["height"], 
            entry["solvetype"],
            entry["displaytype"],
            entry["userid"],
            entry["avglen"],
        )
        
        if key not in unique_entries:
            # First entry with this key, just add it
            unique_entries[key] = entry
        else:
            # Already have an entry with this key, check if new one is better
            existing_entry = unique_entries[key]
            if is_better_pb(existing_entry, entry):
                unique_entries[key] = entry
    
    return list(unique_entries.values())

def convert_to_final_format(data, user_map, control_type_num):
    """Convert filtered data to the final output format"""
    
    # Define mappings
    pb_type_map = {"time": 1, "move": 2, "tps": 3, "FMC": 4, "FMC MTM": 5}
    
    solve_type_map = {
        "Standard": 1,
        "2-N relay": 2,
        "BLD": 3,
        "Everything-up-to relay": 4,
        "Height relay": 5,
        "Width relay": 6,
        "Marathon": 7
    }
    
    control_type_map = {"Keyboard": 0, "Mouse": 1, "Click": 4, "Touch": 5}
    
    rows = []
    
    for entry in data:
        # Parse solve type and marathon length
        solvetype_str = entry["solvetype"]
        marathon_length = 0
        solve_type_num = 1  # Default to Standard
        
        if solvetype_str.startswith("Marathon"):
            # Handle marathon format like "Marathon 42"
            solve_type_num = 7
            try:
                marathon_length = int(solvetype_str.split()[1])
            except (IndexError, ValueError):
                marathon_length = 0
        else:
            # Look up in solve_type_map
            solve_type_num = solve_type_map.get(solvetype_str, 1)
        
        # Get control type - use the provided control_type_num for "both" and "unique" cases
        # For specific controls, map from the entry's control value
        if control_type_num in [2, 3]:  # both or unique
            control_num = control_type_map.get(entry["controls"], 0)
        else:
            control_num = control_type_num
        
        # Create the row in the final format
        row = [
            entry["width"],                    # size_n
            entry["height"],                   # size_m
            pb_type_map.get(entry["pbtype"], 3),  # pb_type
            control_num,                       # control_type
            entry["userid"],                   # userid
            solve_type_num,                    # solve_type
            marathon_length,                   # marathon_length
            entry["avglen"],                   # average_type
            entry["time"],                     # time
            entry["moves"],                    # moves
            entry["tps"],                      # tps
            entry["timestamp"],                # timestamp
            -1,                                # solution_available
            -1                                 # video_link
        ]
        
        rows.append(",".join(map(str, row)))
    
    return rows

def save_final_format(user_map, data_rows, output_filename):
    """Save data in the final format: user_map;row1;row2;..."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
        # Convert user map to string format
        user_map_str = ",".join([f'{user}:{user_id}' for user, user_id in user_map.items()])
        
        # Combine all parts
        final_content = user_map_str + ";" + ";".join(data_rows) + ";"
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(final_content)
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def get_output_folder(input_filename):
    """Generate output folder name based on input filename"""
    base_name = os.path.basename(input_filename)
    return f"{base_name}_output"

def get_output_filename(output_folder, display_type, control_type, pb_type):
    """Generate output filename in the format: {display_type}_{control_type}_{pb_type}"""
    # Convert display type name to number
    display_type_map = {
        "Adjacent sum": 1, "Adjacent tiles": 2, "Chess": 3, "Fading tiles": 4,
        "Fringe minimal": 5, "Incremental vectors": 6, "Inverse permutation": 7,
        "Inverse vectors": 8, "Last move": 9, "Manhattan": 10, "Maximal unsolved": 11,
        "Minesweeper": 12, "Minimal": 13, "Minimal unsolved": 14, "RGB": 15,
        "Row minimal": 16, "Rows and columns": 17, "Standard": 18, 
        "Vanish on solved": 19, "Vectors": 20, "Cyclic": 21, "Divisible": 22,
        "Vertical multi-tile": 23, "Rows": 24, "Square fringe": 25, 
        "Split square fringe": 26, "Checkerboard": 27
    }
    
    # Convert control type name to number
    control_type_map = {
        "keyboard": 0, "mouse": 1, "both": 2, "unique": 3, "click": 4, "touch": 5
    }
    
    # Convert pb type name to number
    pb_type_map = {
        "time": 1, 
        "move": 2, 
        "tps": 3,
        "FMC": 4,
        "FMC MTM": 5
    }
    
    display_num = display_type_map.get(display_type, 0)
    control_num = control_type_map.get(control_type, 0)
    pb_num = pb_type_map.get(pb_type, 0)
    
    filename = f"{display_num}_{control_num}_{pb_num}"
    return os.path.join(output_folder, filename)

def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    print(f"Loading file: {input_file}")
    
    # Step 1: Load and decompress the file
    raw_data = load_zlib_file(input_file)
    if raw_data is None:
        sys.exit(1)
    
    print(f"Loaded {len(raw_data)} raw entries")
    
    # Step 2: Generate user map
    user_map = generate_user_map(raw_data)
    print(f"Generated user map with {len(user_map)} unique users")
    
    # Step 3: Convert to list of dictionaries with user IDs
    all_data = convert_to_dicts(raw_data, user_map)
    
    print(f"Converted {len(all_data)} entries to dictionary format")
    
    # Step 4: Create output folder
    output_folder = get_output_folder(input_file)
    os.makedirs(output_folder, exist_ok=True)
    print(f"Created output folder: {output_folder}")
    
    # Step 5: Define all possible combinations
    display_types = [
        "Adjacent sum", "Adjacent tiles", "Chess", "Fading tiles", "Fringe minimal",
        "Incremental vectors", "Inverse permutation", "Inverse vectors", "Last move",
        "Manhattan", "Maximal unsolved", "Minesweeper", "Minimal", "Minimal unsolved",
        "RGB", "Row minimal", "Rows and columns", "Standard", "Vanish on solved", "Vectors", "Cyclic", "Divisible",
        "Vertical multi-tile", "Rows", "Square fringe", "Split square fringe", "Checkerboard"
    ]
    
    control_types = ["mouse", "keyboard", "both", "unique", "click", "touch"]
    pb_types = ["time", "move", "tps", "FMC", "FMC MTM"]
    
    total_combinations = len(display_types) * len(control_types) * len(pb_types)
    print(f"\nGenerating {total_combinations} files...")
    
    # Step 6: Generate all 240 combinations
    files_created = 0
    
    for display_type in display_types:
        # First filter by display type
        display_filtered = filter_by_display_type(all_data, display_type)
        
        for pb_type in pb_types:
            # Then filter by pb type
            pb_filtered = filter_by_pb_type(display_filtered, pb_type)
            
            for control_type in control_types:
                # Get control type number for final format
                control_type_map_num = {"keyboard": 0, "mouse": 1, "both": 2, "unique": 3, "click": 4, "touch": 5}[control_type]
                
                if control_type == "unique":
                    # For unique, first get both controls, then apply unique PB logic
                    both_data = filter_by_controls(pb_filtered, "both")
                    filtered_data = get_unique_pbs(both_data)
                else:
                    # For mouse, keyboard, both - just filter by controls
                    filtered_data = filter_by_controls(pb_filtered, control_type)
                
                # Convert to final format
                data_rows = convert_to_final_format(filtered_data, user_map, control_type_map_num)
                
                # Generate output filename
                output_file = get_output_filename(output_folder, display_type, control_type, pb_type)
                
                # Save the filtered data in final format
                if save_final_format(user_map, data_rows, output_file):
                    files_created += 1
    
    # Display final summary
    print(f"\nFinal Summary:")
    print(f"  Input file: {input_file}")
    print(f"  Output folder: {output_folder}")
    print(f"  Total original entries: {len(all_data)}")
    print(f"  Unique users: {len(user_map)}")

    # Create combiner and process
    combiner = LeaderboardCombiner(output_folder)
    success = combiner.combine_and_compress()
    
    if success:
        print(f"\nCombined archive created successfully!")
        shutil.rmtree(output_folder)
        copy_and_rename_lzma(combiner, input_file)
        shutil.rmtree("combined_archives")
    else:
        print("\nFailed to create combined archive")
        sys.exit(1)

def copy_and_rename_lzma(combiner, new_name):
    source_folder = f"combined_archives/{combiner.base_name}"
    source_file = None
    
    # Find the .lzma file in the source folder
    for file in os.listdir(source_folder):
        if file.endswith('.lzma'):
            source_file = os.path.join(source_folder, file)
            break
    
    if source_file is None:
        print(f"No .lzma file found in {source_folder}")
        return False
    
    # Create new filename
    new_filename = f"leaderboard_{new_name}.lzma"
    
    # Copy and rename the file
    shutil.copy2(source_file, new_filename)
    print(f"Copied {source_file} to {new_filename}")
    return True

if __name__ == "__main__":
    main()