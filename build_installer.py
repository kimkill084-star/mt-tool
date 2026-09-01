import PyInstaller.__main__
import os
import sys

def build_installer():
    main_exe = os.path.join('dist', 'mt-tool.exe')
    updater_exe = os.path.join('dist', 'updater.exe')
    
    if not os.path.exists(main_exe) or not os.path.exists(updater_exe):
        print("Error: Main executables not found in dist/ directory.")
        sys.exit(1)
        
    print("Building GUI Installer (Setup Wizard)...")
    
    # Path separator for add-data is ';' on Windows
    add_data_main = f"{main_exe};."
    add_data_updater = f"{updater_exe};."
    
    PyInstaller.__main__.run([
        'installer.py',
        '--noconsole',
        '--onefile',
        '--name', 'Setup_mt-tool',
        '--icon', 'app_icon.ico',
        '--add-data', 'app_icon.ico;.',
        '--add-data', add_data_main,
        '--add-data', add_data_updater,
    ])
    
    print("Installer Build complete. Look for Setup_MultiToolApp.exe in the 'dist' folder.")

if __name__ == "__main__":
    build_installer()
