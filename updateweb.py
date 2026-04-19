import os
import subprocess
import shutil
from datetime import datetime
import time

def run_command(command, description, start_time=None):
    """Run a command and show real-time output with timing"""
    print(f"\n{description}...")
    print("-" * 40)
    step_start = time.time()
    
    try:
        # Run without capturing output - it will stream to console
        result = subprocess.run(command, shell=True, check=True)
        step_elapsed = time.time() - step_start
        
        print("-" * 40)
        print(f"✓ {description} completed successfully")
        print(f"  ⏱️  Time taken: {step_elapsed:.2f} seconds")
        
        if start_time is not None:
            total_elapsed = time.time() - start_time
            print(f"  📊 Total so far: {total_elapsed:.2f} seconds")
        
        return True
    except subprocess.CalledProcessError as e:
        step_elapsed = time.time() - step_start
        print("-" * 40)
        print(f"✗ Error running {description}")
        print(f"  Error code: {e.returncode}")
        print(f"  ⏱️  Failed after: {step_elapsed:.2f} seconds")
        return False

def main():
    # Start total timer
    total_start_time = time.time()
    print("=" * 60)
    print("🚀 SCRIPT STARTED")
    print(f"📅 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Get current date in YYYYMMDD format
    date_stamp = datetime.now().strftime("%Y%m%d")
    print(f"\n📆 Date stamp: {date_stamp}")
    
    # Step 1: Run grabdata.py
    if not run_command("python grabdata.py", "Running grabdata.py", total_start_time):
        return 1
    
    # Step 2: Run dumbifyweb.py
    if not run_command("python dumbifyweb.py", "Running dumbifyweb.py", total_start_time):
        return 1
    
    # Step 3: Run decomp.py with dumbified.txt
    if not run_command("python decomp.py dumbified.txt", "Running decomp.py on dumbified.txt", total_start_time):
        return 1
    
    # Step 4: Rename leaderboard_dumbified.txt.lzma to web_YYYYMMDD.lzma
    print(f"\n📝 Renaming file...")
    print("-" * 40)
    rename_start = time.time()
    
    old_filename = "leaderboard_dumbified.txt.lzma"
    new_filename = f"web_{date_stamp}.lzma"

    try:
        if os.path.exists(old_filename):
            # Remove old file with same name if it exists (to avoid errors)
            if os.path.exists(new_filename):
                os.remove(new_filename)
                print(f"✓ Removed existing file: {new_filename}")
            os.rename(old_filename, new_filename)
            rename_elapsed = time.time() - rename_start
            print(f"✓ Renamed successfully")
            print(f"  ⏱️  Time taken: {rename_elapsed:.2f} seconds")
            
            total_elapsed = time.time() - total_start_time
            print(f"  📊 Total so far: {total_elapsed:.2f} seconds")
        else:
            print(f"✗ Error: {old_filename} not found")
            return 1
    except Exception as e:
        print(f"✗ Error renaming file: {e}")
        return 1

    # Step 5: Copy file to archives directory
    print(f"\n📋 Copying file...")
    print("-" * 40)
    copy_start = time.time()
    
    destination_dir = r"C:\coding\leaderboardArchiver\archives"
    destination_path = os.path.join(destination_dir, new_filename)

    try:
        if os.path.exists(new_filename):
            # Create directory if it doesn't exist
            os.makedirs(destination_dir, exist_ok=True)
            # Remove old file in archives directory if it exists (replace)
            if os.path.exists(destination_path):
                os.remove(destination_path)
                print(f"✓ Removed existing archive file: {destination_path}")
            shutil.copy2(new_filename, destination_path)
            copy_elapsed = time.time() - copy_start
            print(f"✓ Copied successfully to {destination_path}")
            print(f"  ⏱️  Time taken: {copy_elapsed:.2f} seconds")
            
            total_elapsed = time.time() - total_start_time
            print(f"  📊 Total so far: {total_elapsed:.2f} seconds")
        else:
            print(f"✗ Error: {new_filename} not found")
            return 1
    except Exception as e:
        print(f"✗ Error copying file: {e}")
        return 1
    
    # Step 6: Run update.bat
    update_bat = r"C:\coding\leaderboardArchiver\update.bat"
    if not run_command(update_bat, f"Running {update_bat}", total_start_time):
        return 1
    
    # Final summary
    total_elapsed = time.time() - total_start_time
    print("\n" + "=" * 60)
    print("✅ ALL OPERATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"📊 FINAL TIMING SUMMARY:")
    print(f"   Total time: {total_elapsed:.2f} seconds")
    print(f"   Total time: {total_elapsed/60:.2f} minutes")
    print(f"   Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Pause at the end if running from double-click
    input("\nPress Enter to exit...")
    return 0

if __name__ == "__main__":
    exit(main())