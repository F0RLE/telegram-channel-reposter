"""
Universal Stable Diffusion WebUI Reforge Installer
Installs SD with recommended PyTorch 2.3.1+cu121 and xformers 0.0.27
"""
import subprocess
import sys
import os
from pathlib import Path

# Recommended versions (SD WebUI Reforge tested)
PYTORCH_VERSION = "2.3.1"
TORCHVISION_VERSION = "0.18.1"
TORCHAUDIO_VERSION = "2.3.1"
XFORMERS_VERSION = "0.0.27"
CUDA_VERSION = "cu121"

# Paths
APPDATA = os.environ["APPDATA"]
SD_DIR = os.path.join(APPDATA, "TelegramBotData", "data", "Engine", "stable-diffusion-webui-reforge")
VENV_DIR = os.path.join(SD_DIR, "venv")
VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
SITE_PACKAGES = os.path.join(VENV_DIR, "Lib", "site-packages")

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def run_pip(args, check=True):
    """Run pip command with the venv python"""
    cmd = [VENV_PYTHON, "-m", "pip"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=False)
    return result.returncode

def check_sd_exists():
    """Check if SD is already installed"""
    return os.path.exists(SD_DIR) and os.path.exists(os.path.join(SD_DIR, "launch.py"))

def check_venv_exists():
    """Check if venv exists"""
    return os.path.exists(VENV_PYTHON)

def install_pytorch():
    """Install PyTorch with CUDA support"""
    print_header(f"Installing PyTorch {PYTORCH_VERSION}+{CUDA_VERSION}")
    
    # Uninstall existing versions
    print("Uninstalling existing PyTorch...")
    run_pip(["uninstall", "-y", "torch", "torchvision", "torchaudio", "xformers"], check=False)
    
    # Install new versions
    print(f"\nInstalling PyTorch {PYTORCH_VERSION}...")
    returncode = run_pip([
        "install", 
        f"torch=={PYTORCH_VERSION}", 
        f"torchvision=={TORCHVISION_VERSION}", 
        f"torchaudio=={TORCHAUDIO_VERSION}", 
        "--index-url", f"https://download.pytorch.org/whl/{CUDA_VERSION}"
    ])
    
    if returncode != 0:
        print("ERROR: Failed to install PyTorch!")
        return False
    
    print("✓ PyTorch installed successfully")
    return True

def install_xformers():
    """Install xformers"""
    print_header(f"Installing xformers {XFORMERS_VERSION}")
    
    returncode = run_pip([
        "install", 
        f"xformers=={XFORMERS_VERSION}", 
        "--index-url", f"https://download.pytorch.org/whl/{CUDA_VERSION}"
    ])
    
    if returncode != 0:
        print("WARNING: Failed to install xformers from PyTorch index, trying PyPI...")
        returncode = run_pip([f"install", f"xformers=={XFORMERS_VERSION}"], check=False)
        
    if returncode == 0:
        print("✓ xformers installed successfully")
        return True
    else:
        print("WARNING: Could not install xformers, SD will work without it")
        return False

def install_joblib():
    """Install joblib (required by some SD extensions)"""
    print_header("Installing joblib")
    returncode = run_pip(["install", "joblib"])
    if returncode == 0:
        print("✓ joblib installed successfully")
    return returncode == 0

def create_sitecustomize():
    """Create sitecustomize.py to fix PYTHONPATH for extensions"""
    print_header("Creating sitecustomize.py")
    
    sitecustomize_path = os.path.join(SITE_PACKAGES, "sitecustomize.py")
    content = f'''
import sys
import os

# Add SD root to sys.path to fix 'import launch' errors in extensions
sd_dir = r"{SD_DIR}"
if sd_dir not in sys.path:
    sys.path.insert(0, sd_dir)
'''
    
    try:
        with open(sitecustomize_path, "w") as f:
            f.write(content.strip())
        print(f"✓ Created sitecustomize.py at {sitecustomize_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create sitecustomize.py: {e}")
        return False

def verify_installation():
    """Verify PyTorch and xformers installation"""
    print_header("Verifying Installation")
    
    check_script = '''
import torch
import sys

print(f"PyTorch: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA Version: {torch.version.cuda}")
    print(f"Device: {torch.cuda.get_device_name(0)}")

try:
    import xformers
    print(f"xformers: {xformers.__version__}")
except ImportError:
    print("xformers: Not installed")
'''
    
    result = subprocess.run(
        [VENV_PYTHON, "-c", check_script],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return False
    
    return "CUDA Available: True" in result.stdout

def main():
    print_header("SD WebUI Reforge - Universal Installer")
    print(f"PyTorch: {PYTORCH_VERSION}+{CUDA_VERSION}")
    print(f"xformers: {XFORMERS_VERSION}")
    print(f"Target: {SD_DIR}")
    
    # Check if SD exists
    if not check_sd_exists():
        print("\nERROR: SD WebUI Reforge not found!")
        print(f"Expected location: {SD_DIR}")
        print("Please install SD first or check the path.")
        return 1
    
    print("✓ SD WebUI Reforge found")
    
    # Check if venv exists
    if not check_venv_exists():
        print("\nERROR: Virtual environment not found!")
        print(f"Expected location: {VENV_DIR}")
        print("Please create the venv first.")
        return 1
    
    print("✓ Virtual environment found")
    
    # Install components
    success = True
    success = install_pytorch() and success
    success = install_xformers() and success
    success = install_joblib() and success
    success = create_sitecustomize() and success
    
    # Verify
    if success and verify_installation():
        print_header("✓ Installation Complete!")
        print("All components installed successfully.")
        print("\nYou can now start Stable Diffusion.")
        return 0
    else:
        print_header("⚠ Installation Completed with Warnings")
        print("Some components may not have installed correctly.")
        print("SD should still work, but with reduced functionality.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
