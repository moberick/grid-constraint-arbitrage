import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_historical_grid_data(days_back: int = 7) -> pd.DataFrame:
    """
    Fetch System Prices (DISEBSP) and Bid-Offer Acceptances (BOALF) 
    from Elexon Insights API for the requested time window.
    
    Args:
        days_back: Number of historical days to fetch (default: 7)
        
    Returns:
        pd.DataFrame: Merged data aligned to half-hourly settlement periods.
    """
    end_date_obj = datetime.now()
    start_date_obj = end_date_obj - timedelta(days=days_back)
    
    start_date = start_date_obj.strftime('%Y-%m-%d')
    end_date = end_date_obj.strftime('%Y-%m-%d')
    
    print(f"Fetching grid data from {start_date} to {end_date}...")

    # Generate list of dates to iterate for System Prices and BOALF (day by day pagination is safer)
    date_list = [start_date_obj + timedelta(days=x) for x in range(days_back + 1)]
    
    # 1. Fetch System Prices
    print("Fetching System Prices (DISEBSP)...")
    ssp_records = []
    
    for dt in date_list:
        date_str = dt.strftime('%Y-%m-%d')
        url = f"https://data.elexon.co.uk/bmrs/api/v1/balancing/settlement/system-prices/{date_str}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json().get('data', [])
                for row in data:
                    ssp_records.append({
                        'SettlementDate': row.get('settlementDate'),
                        'SettlementPeriod': row.get('settlementPeriod'),
                        'SystemSellPrice': row.get('systemSellPrice'),
                        'SystemBuyPrice': row.get('systemBuyPrice')
                    })
            else:
                print(f"Failed to fetch System Prices for {date_str} (Status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching System Prices for {date_str}: {e}")
            
    ssp_df = pd.DataFrame(ssp_records)
    if not ssp_df.empty:
        ssp_df['SettlementDate'] = pd.to_datetime(ssp_df['SettlementDate'], format='%Y-%m-%d', errors='coerce')
        ssp_df['SettlementPeriod'] = pd.to_numeric(ssp_df['SettlementPeriod'], errors='coerce')
        ssp_df['SystemSellPrice'] = pd.to_numeric(ssp_df['SystemSellPrice'], errors='coerce')
        ssp_df['SystemBuyPrice'] = pd.to_numeric(ssp_df['SystemBuyPrice'], errors='coerce')
        ssp_df = ssp_df.dropna(subset=['SettlementDate', 'SettlementPeriod'])

    # 2. Fetch Bid-Offer Acceptances (BOALF)
    print("Fetching Bid-Offer Acceptances (BOALF)...")
    boalf_records = []
    
    for dt in date_list:
        date_str = dt.strftime('%Y-%m-%d')
        url = f"https://data.elexon.co.uk/bmrs/api/v1/datasets/BOALF?from={date_str}T00:00:00Z&to={date_str}T23:59:59Z"
        try:
            headers = {'Accept': 'application/json'}
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code == 200:
                data = response.json().get('data', [])
                for row in data:
                    level_from = row.get('levelFrom', 0)
                    level_to = row.get('levelTo', 0)
                    # Use average of levelFrom and levelTo for volume
                    volume = (level_from + level_to) / 2.0
                    
                    boalf_records.append({
                        'SettlementDate': row.get('settlementDate'),
                        'SettlementPeriod': row.get('settlementPeriodFrom'),
                        'BMUnitID': row.get('bmUnit'),
                        'AcceptanceVolume': volume
                    })
            elif response.status_code == 404:
                pass
            else:
                print(f"Failed to fetch BOALF for {date_str} (Status: {response.status_code}) - {response.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching BOALF for {date_str}: {e}")
            
    boalf_df = pd.DataFrame(boalf_records)
    if not boalf_df.empty:
        boalf_df['SettlementDate'] = pd.to_datetime(boalf_df['SettlementDate'], format='%Y-%m-%d', errors='coerce')
        boalf_df['SettlementPeriod'] = pd.to_numeric(boalf_df['SettlementPeriod'], errors='coerce')
        boalf_df['AcceptanceVolume'] = pd.to_numeric(boalf_df['AcceptanceVolume'], errors='coerce')
        boalf_df = boalf_df.dropna(subset=['SettlementDate', 'SettlementPeriod'])
        
        # Aggregate total BOALF volume per settlement period
        boalf_df = boalf_df.groupby(['SettlementDate', 'SettlementPeriod'], as_index=False)['AcceptanceVolume'].sum()
        boalf_df = boalf_df.rename(columns={'AcceptanceVolume': 'TotalBOALFVolume'})

    # 3. Merge Datasets
    print("Merging datasets...")
    if ssp_df.empty and boalf_df.empty:
        print("Warning: Both datasets are empty.")
        return pd.DataFrame()
    elif ssp_df.empty:
        return boalf_df
    elif boalf_df.empty:
        return ssp_df
        
    merged_df = pd.merge(ssp_df, boalf_df, on=['SettlementDate', 'SettlementPeriod'], how='outer')
    
    # Sort and clean
    merged_df = merged_df.sort_values(by=['SettlementDate', 'SettlementPeriod']).reset_index(drop=True)
    return merged_df

if __name__ == "__main__":
    print("Starting data fetch for the last 7 days...")
    
    df = fetch_historical_grid_data(days_back=7)
    
    if not df.empty:
        output_file = "raw_grid_data.csv"
        df.to_csv(output_file, index=False)
        print(f"Successfully saved grid data to {output_file}")
        print(df.head())
    else:
        print("Failed to fetch data or data is empty.")
