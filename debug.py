import os
import boto3

# 1. Where does Python think your home directory is?
home_dir = os.path.expanduser("~")
print(f"Python sees your home directory as: {home_dir}")

# 2. Let's look at the exact path Boto3 uses
creds_path = os.path.join(home_dir, ".aws", "credentials")
print(f"Looking for credentials at: {creds_path}")
print(f"Does this file exist? {os.path.exists(creds_path)}")

# 3. If it exists, let's read the first few characters to check the format
if os.path.exists(creds_path):
    print("\n--- Reading file contents ---")
    with open(creds_path, 'r', encoding='utf-8-sig') as f: # utf-8-sig handles weird Windows encodings
        lines = f.readlines()
        for line in lines:
            # We will mask the actual secret key for safety
            if "aws_secret_access_key" in line:
                print("aws_secret_access_key = [HIDDEN FOR SECURITY]")
            else:
                print(line.strip())
    print("-----------------------------\n")

# 4. Let's ask Boto3 directly if it can find credentials
try:
    session = boto3.Session()
    creds = session.get_credentials()
    if creds:
        print("✅ Boto3 successfully found credentials!")
    else:
        print("❌ Boto3 could NOT find credentials.")
except Exception as e:
    print(f"Error: {e}")