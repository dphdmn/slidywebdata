import os
import subprocess
import shutil
from datetime import datetime
import time
import sys

class Logger:
    def __init__(self, log_dir="logs"):
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"run_{timestamp}.log")
        
        # Open log file
        self.file = open(self.log_file, 'w', encoding='utf-8')
        
        # Write header
        self.log("=" * 60)
        self.log("🚀 SCRIPT STARTED")
        self.log(f"📅 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"📝 Log file: {self.log_file}")
        self.log("=" * 60)
    
    def log(self, message):
        """Write message to log file and print to console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        print(formatted_message)
        self.file.write(formatted_message + '\n')
        self.file.flush()  # Ensure message is written immediately
    
    def close(self):
        """Close the log file"""
        self.file.close()

def run_command(command, description, start_time=None, logger=None):
    """Run a command and show real-time output with timing"""
    logger.log(f"\n{description}...")
    logger.log("-" * 40)
    step_start = time.time()
    
    try:
        # Run with output capturing to log file
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Capture and log output in real-time
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.log(f"  {line}")
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
        
        step_elapsed = time.time() - step_start
        
        logger.log("-" * 40)
        logger.log(f"✓ {description} completed successfully")
        logger.log(f"  ⏱️  Time taken: {step_elapsed:.2f} seconds")
        
        if start_time is not None:
            total_elapsed = time.time() - start_time
            logger.log(f"  📊 Total so far: {total_elapsed:.2f} seconds")
        
        return True
    except subprocess.CalledProcessError as e:
        step_elapsed = time.time() - step_start
        logger.log("-" * 40)
        logger.log(f"✗ Error running {description}")
        logger.log(f"  Error code: {e.returncode}")
        logger.log(f"  ⏱️  Failed after: {step_elapsed:.2f} seconds")
        return False

def main():
    # Create logger with timestamp
    logger = Logger()
    
    # Start total timer
    total_start_time = time.time()
    
    # Get current date in YYYYMMDD format
    date_stamp = datetime.now().strftime("%Y%m%d")
    logger.log(f"\n📆 Date stamp: {date_stamp}")
    
    # Step 1: Run grabdata.py
    if not run_command("python grabdata.py", "Running grabdata.py", total_start_time, logger):
        logger.log("\n❌ Script failed at Step 1: grabdata.py")
        logger.close()
        return 1
    
    # Step 2: Run dumbifyweb.py
    if not run_command("python dumbifyweb.py", "Running dumbifyweb.py", total_start_time, logger):
        logger.log("\n❌ Script failed at Step 2: dumbifyweb.py")
        logger.close()
        return 1
    
    # Step 3: Run decomp.py with dumbified.txt
    if not run_command("python decomp.py dumbified.txt", "Running decomp.py on dumbified.txt", total_start_time, logger):
        logger.log("\n❌ Script failed at Step 3: decomp.py")
        logger.close()
        return 1
    
    # Step 4: Rename leaderboard_dumbified.txt.lzma to web_YYYYMMDD.lzma
    logger.log(f"\n📝 Renaming file...")
    logger.log("-" * 40)
    rename_start = time.time()
    
    old_filename = "leaderboard_dumbified.txt.lzma"
    new_filename = f"web_{date_stamp}.lzma"

    try:
        if os.path.exists(old_filename):
            # Remove old file with same name if it exists (to avoid errors)
            if os.path.exists(new_filename):
                os.remove(new_filename)
                logger.log(f"✓ Removed existing file: {new_filename}")
            os.rename(old_filename, new_filename)
            rename_elapsed = time.time() - rename_start
            logger.log(f"✓ Renamed successfully")
            logger.log(f"  ⏱️  Time taken: {rename_elapsed:.2f} seconds")
            
            total_elapsed = time.time() - total_start_time
            logger.log(f"  📊 Total so far: {total_elapsed:.2f} seconds")
        else:
            logger.log(f"✗ Error: {old_filename} not found")
            logger.log("\n❌ Script failed at Step 4: File rename")
            logger.close()
            return 1
    except Exception as e:
        logger.log(f"✗ Error renaming file: {e}")
        logger.log("\n❌ Script failed at Step 4: File rename")
        logger.close()
        return 1

    # Step 5: Copy file to archives directory
    logger.log(f"\n📋 Copying file...")
    logger.log("-" * 40)
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
                logger.log(f"✓ Removed existing archive file: {destination_path}")
            shutil.copy2(new_filename, destination_path)
            copy_elapsed = time.time() - copy_start
            logger.log(f"✓ Copied successfully to {destination_path}")
            logger.log(f"  ⏱️  Time taken: {copy_elapsed:.2f} seconds")
            
            total_elapsed = time.time() - total_start_time
            logger.log(f"  📊 Total so far: {total_elapsed:.2f} seconds")
        else:
            logger.log(f"✗ Error: {new_filename} not found")
            logger.log("\n❌ Script failed at Step 5: File copy")
            logger.close()
            return 1
    except Exception as e:
        logger.log(f"✗ Error copying file: {e}")
        logger.log("\n❌ Script failed at Step 5: File copy")
        logger.close()
        return 1
    
    # Step 6: Run update.bat
    update_bat = r"C:\coding\leaderboardArchiver\update.bat"
    if not run_command(update_bat, f"Running {update_bat}", total_start_time, logger):
        logger.log(f"\n❌ Script failed at Step 6: {update_bat}")
        logger.close()
        return 1
    
    # Final summary
    total_elapsed = time.time() - total_start_time
    logger.log("\n" + "=" * 60)
    logger.log("✅ ALL OPERATIONS COMPLETED SUCCESSFULLY!")
    logger.log("=" * 60)
    logger.log(f"📊 FINAL TIMING SUMMARY:")
    logger.log(f"   Total time: {total_elapsed:.2f} seconds")
    logger.log(f"   Total time: {total_elapsed/60:.2f} minutes")
    logger.log(f"   Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log(f"   Log saved to: {logger.log_file}")
    logger.log("=" * 60)
    
    # Close logger
    logger.close()
    return 0

if __name__ == "__main__":
    exit(main())