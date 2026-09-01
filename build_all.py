import subprocess
import sys

def run_step(cmd, desc):
    print(f"\n{'='*50}\n[STEP] {desc}\n{'='*50}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error: Step failed with code {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    run_step("python build.py", "1. Building main application (mt-tool.exe)")
    run_step("python build_installer.py", "2. Building setup wizard (Setup_mt-tool.exe)")
    print("\nAll builds completed successfully!")
