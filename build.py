import PyInstaller.__main__
import os

def build():
    print("Building Main Application...")
    PyInstaller.__main__.run([
        'main.py',
        '--noconsole',
        '--onefile',
        '--name', 'mt-tool',
        '--icon', 'app_icon.ico',
        '--add-data', 'app_icon.ico;.',
        '--collect-data', 'onnxruntime',
        '--collect-binaries', 'onnxruntime',
        '--collect-data', 'rembg',
        '--collect-binaries', 'rembg',
    ])
    
    print("Build complete! Output: dist/mt-tool.exe")

if __name__ == "__main__":
    build()
