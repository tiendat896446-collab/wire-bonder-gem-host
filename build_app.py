import os
import sys
import subprocess

def run_build():
    """
    Build script to compile the complete Wire Bonder application using PyInstaller.
    Compiles 'main.py' (launcher) which manages both the background FastAPI uvicorn server
    and the foreground CustomTkinter desktop UI.
    """
    print("==================================================")
    print("       WIRE BONDER DESKTOP APP BUILDER")
    print("==================================================")

    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[Error] PyInstaller package not found! Please run: pip install pyinstaller")
        sys.exit(1)

    # 2. Setup build options
    # --onefile packages everything into a single executable.
    # --collect-all customtkinter ensures all customtkinter resources, images, and themes are bundled.
    # --collect-all uvicorn ensures uvicorn server dependencies are fully packaged.
    # --collect-all fastapi ensures fastapi dependencies are included.

    cmd = [
        "pyinstaller",
        "--clean",
        "--name=WireBonderControlSuite",
        "--onefile",
        "--collect-all=customtkinter",
        "--collect-all=uvicorn",
        "--collect-all=fastapi",
        "--collect-all=websockets",
        "--collect-all=sqlalchemy",
        "--collect-all=backend",
        "main.py"
    ]

    print(f"Executing command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print("\n==================================================")
            print(" [SUCCESS] App packaged successfully!")
            print(" Executable can be found in the './dist/' folder.")
            print("==================================================")
    except subprocess.CalledProcessError as e:
        print(f"\n[Error] PyInstaller packaging failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
