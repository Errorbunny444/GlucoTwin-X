import urllib.request
import zipfile
import sys
from pathlib import Path

def download_file(url, dest_path):
    print(f"Downloading {url} to {dest_path}")
    urllib.request.urlretrieve(url, dest_path)
    print("Download complete.")

def extract_zip(zip_path, extract_dir):
    print(f"Extracting {zip_path} to {extract_dir}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print("Extraction complete.")

if __name__ == "__main__":
    synthea_url = "https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip"
    cgmacros_url = "https://physionet.org/files/cgmacros/1.0.0/CGMacros_dateshifted365.zip"

    project_root = Path(__file__).resolve().parent.parent
    synthea_dir = project_root / "data" / "raw" / "synthea"
    cgmacros_dir = project_root / "data" / "raw" / "cgmacros"

    synthea_zip = synthea_dir / "synthea_sample.zip"
    cgmacros_zip = cgmacros_dir / "cgmacros.zip"

    try:
        download_file(synthea_url, synthea_zip)
        extract_zip(synthea_zip, synthea_dir)
    except Exception as e:
        print(f"Error processing Synthea: {e}")

    try:
        download_file(cgmacros_url, cgmacros_zip)
        extract_zip(cgmacros_zip, cgmacros_dir)
    except Exception as e:
        print(f"Error processing CGMacros: {e}")

