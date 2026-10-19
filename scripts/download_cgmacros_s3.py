import os
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path

def download_cgmacros():
    bucket_name = 'physionet-open'
    prefix = 'cgmacros/1.0.0/'
    
    project_root = Path(__file__).resolve().parent.parent
    cgmacros_dir = project_root / 'data' / 'raw' / 'cgmacros'
    cgmacros_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize anonymous s3 client
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    
    # List objects
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    
    if 'Contents' not in response:
        print("No files found in bucket.")
        return
        
    # We only want specific files
    target_files = [
        'CGMacros_dateshifted365.zip',
        'DataDictionary.pdf',
        'DataDictionary_Bio.csv',
        'DataDictionary_CGMacros-00X.csv',
        'SHA256SUMS.txt',
        'LICENSE.txt',
        'README.txt'
    ]
    
    for obj in response['Contents']:
        key = obj['Key']
        filename = key.split('/')[-1]
        
        if filename in target_files:
            download_path = cgmacros_dir / filename
            print(f"Downloading {filename} ({obj['Size'] / (1024*1024):.2f} MB)...")
            s3.download_file(bucket_name, key, str(download_path))
            print(f"Finished downloading {filename}")
            
if __name__ == '__main__':
    download_cgmacros()
