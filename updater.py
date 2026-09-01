import sys
import os
import time
import zipfile
import subprocess
import shutil

def main():
    if len(sys.argv) < 4:
        print("Usage: updater.exe <app_dir> <zip_path> <executable_name>")
        sys.exit(1)

    app_dir = sys.argv[1]
    zip_path = sys.argv[2]
    executable_name = sys.argv[3]

    print(f"Waiting for main application to close...")
    time.sleep(3)  # Wait for main app to exit completely

    try:
        print(f"Extracting update from {zip_path} to {app_dir}...")
        # Extract the zip file over the existing files
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # We assume the zip contains the contents that should go directly into app_dir
            zip_ref.extractall(app_dir)
        print("Extraction successful.")
    except Exception as e:
        print(f"Error during extraction: {e}")
        # Even if extraction fails, try to restart the app
    
    # Try to clean up the zip file
    try:
        os.remove(zip_path)
    except:
        pass

    # Restart the main app
    exe_path = os.path.join(app_dir, executable_name)
    if os.path.exists(exe_path):
        print(f"Restarting application: {exe_path}")
        subprocess.Popen([exe_path])
    else:
        print(f"Error: Could not find executable {exe_path} to restart.")

if __name__ == "__main__":
    main()
