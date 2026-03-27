import requests
import pandas as pd
from datetime import datetime

url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
print("Downloading Scrip Master...")
req = requests.get(url)
data = req.json()

df = pd.DataFrame(data)
nfo = df[(df['exch_seg'] == 'NFO') & (df['name'] == 'NIFTY') & (df['instrumenttype'] == 'OPTIDX')]

# Drop rows with empty expiry
nfo = nfo[nfo['expiry'] != ""]

# Convert expiry to datetime for sorting to find nearest expiry
nfo['expiry_dt'] = pd.to_datetime(nfo['expiry'], format="%d%b%Y", errors='coerce')
nfo = nfo.dropna(subset=['expiry_dt'])
nearest_expiry = nfo['expiry_dt'].min()

print(f"Nearest Expiry: {nearest_expiry}")

# Get all CE options for nearest expiry
nfo_nearest = nfo[nfo['expiry_dt'] == nearest_expiry]
ce_ops = nfo_nearest[nfo_nearest['symbol'].str.endswith('CE')]

print("Sample CE options for nearest expiry:")
print(ce_ops[['symbol', 'token', 'strike', 'expiry']].head())
