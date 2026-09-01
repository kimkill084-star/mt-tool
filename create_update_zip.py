import os
import zipfile
import sys

def create_update_zip():
    dist_dir = 'dist'
    zip_path = os.path.join(dist_dir, 'update.zip')
    main_exe = os.path.join(dist_dir, 'mt-tool.exe')
    updater_exe = os.path.join(dist_dir, 'updater.exe')
    
    if not os.path.exists(main_exe) or not os.path.exists(updater_exe):
        print(f"Error: Could not find {main_exe} or {updater_exe}.")
        print("Please run build.py first.")
        sys.exit(1)
        
    print(f"Creating {zip_path} for GitHub release...")
    try:
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(main_exe, 'mt-tool.exe')
            zf.write(updater_exe, 'updater.exe')
        print("Done! You can now upload 'dist/update.zip' to your GitHub Release.")
    except PermissionError:
        fallback_zip = os.path.join(dist_dir, 'update_new.zip')
        print(f"Warning: update.zip is locked. Writing to {fallback_zip} instead...")
        with zipfile.ZipFile(fallback_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(main_exe, 'mt-tool.exe')
            zf.write(updater_exe, 'updater.exe')
        print(f"Done! 'dist/update.zip'이 사용 중이어서 '{fallback_zip}'으로 저장되었습니다.")

if __name__ == "__main__":
    create_update_zip()
