import pandas as pd
import numpy as np

class GridEconomics:
    def __init__(self):
        self.df = None

    def load_data(self, filepath):
        try:
            # Load the CSV
            self.df = pd.read_csv(filepath)
            
            # Check for expected minimal columns required for economics
            expected_cols = ['SettlementDate', 'SettlementPeriod', 'SystemSellPrice', 'TotalBOALFVolume']
            missing_cols = [col for col in expected_cols if col not in self.df.columns]
            if missing_cols:
                raise KeyError(f"Missing expected columns in CSV: {missing_cols}")
            
            # Clean the data by dropping empty essential rows and filling numeric gaps with 0
            self.df = self.df.dropna(subset=['SettlementDate', 'SettlementPeriod'])
            
            numeric_cols = ['SystemSellPrice', 'SystemBuyPrice', 'TotalBOALFVolume']
            existing_numeric_cols = [c for c in numeric_cols if c in self.df.columns]
            self.df[existing_numeric_cols] = self.df[existing_numeric_cols].fillna(0)

            # Ensure the timestamp column is converted to a proper Pandas datetime object
            # Using SettlementDate as the primary timestamp indicator available
            if 'SettlementDate' in self.df.columns:
                self.df['SettlementDate'] = pd.to_datetime(self.df['SettlementDate'], errors='coerce')

        except KeyError as e:
            print(f"KeyError: {e}")
            if self.df is not None:
                print(f"Actual CSV columns available: {list(self.df.columns)}")
            raise
        except FileNotFoundError:
            print(f"Error: Could not find the file at {filepath}")
            raise
        except Exception as e:
            print(f"Error loading data: {e}")
            raise

    def calculate_wasted_value(self):
        if self.df is None or self.df.empty:
            raise ValueError("Data not loaded. Call load_data() first.")
            
        # Isolate negative BOALF volumes (wind farms / generators paid to turn down)
        # We clip the upper bound to 0 to easily zero out all positive volumes
        curtailed_volume = self.df['TotalBOALFVolume'].clip(upper=0)
        
        # Financial cost of the grid constraint = abs(Curtailed Volume in MWh) * System Price
        # (Assuming SystemSellPrice acts as the primary System Price metric)
        self.df['Constraint_Cost_GBP'] = curtailed_volume.abs() * self.df['SystemSellPrice']

    def get_summary_stats(self):
        if self.df is None or 'Constraint_Cost_GBP' not in self.df.columns:
            raise ValueError("Economics not calculated. Call calculate_wasted_value() first.")
            
        total_cost = self.df['Constraint_Cost_GBP'].sum()
        avg_price = self.df['SystemSellPrice'].mean()
        
        return {
            'Total_Constraint_Cost_GBP': total_cost,
            'Average_System_Price_GBP_MWh': avg_price
        }

    def simulate_battery(self, mw_capacity, mwh_duration, charge_threshold, discharge_threshold):
        if self.df is None or self.df.empty:
            raise ValueError("Data not loaded. Call load_data() first.")

        # Initialize State
        max_capacity_mwh = mw_capacity * mwh_duration
        soc_mwh = 0.0
        total_profit_gbp = 0.0
        rte = 0.85
        
        # Max flow rate for a 30-min period (MWh)
        max_flow_per_period = mw_capacity / 2.0

        # Iteration Logic (CRITICAL)
        # Using a loop to iterate through the DataFrame chronologically due to SOC dependency
        self.df = self.df.sort_values(by=['SettlementDate', 'SettlementPeriod'])
        
        soc_history = []
        profit_history = []
        
        for row in self.df.itertuples():
            system_price = row.SystemSellPrice
            period_profit = 0.0
            
            # Charge Rule
            if system_price <= charge_threshold and soc_mwh < max_capacity_mwh:
                # Max amount we can pull from the grid this period
                charge_space = max_capacity_mwh - soc_mwh
                charge_amount_mwh = min(max_flow_per_period, (charge_space / rte))
                
                # Actual energy added to battery after efficiency loss
                soc_mwh += charge_amount_mwh * rte
                
                # Cost to charge (negative price = we get paid = profit goes up)
                period_profit -= charge_amount_mwh * system_price
                
            # Discharge Rule
            elif system_price >= discharge_threshold and soc_mwh > 0:
                # Max amount we can push to the grid this period
                discharge_amount_mwh = min(max_flow_per_period, soc_mwh)
                
                soc_mwh -= discharge_amount_mwh
                
                # Revenue from dispatching
                period_profit += discharge_amount_mwh * system_price
                
            total_profit_gbp += period_profit
            soc_history.append(soc_mwh)
            profit_history.append(total_profit_gbp)
            
        self.df['Battery_SOC_MWh'] = soc_history
        self.df['Cumulative_Profit_GBP'] = profit_history
        
        return total_profit_gbp

if __name__ == "__main__":
    filepath = 'raw_grid_data.csv'
    engine = GridEconomics()
    
    try:
        print("Loading raw grid data...")
        engine.load_data(filepath)
        
        print("Calculating constraint economics...")
        engine.calculate_wasted_value()
        
        stats = engine.get_summary_stats()
        
        print("\n" + "="*45)
        print("        GRID ECONOMICS SUMMARY")
        print("="*45)
        print(f"Total B6 Constraint Cost Wasted: £{stats['Total_Constraint_Cost_GBP']:,.2f}")
        print(f"Average System Price:            £{stats['Average_System_Price_GBP_MWh']:,.2f} / MWh")
        print("="*45 + "\n")
        
        print("Simulating 500MW / 1000MWh battery arbitrage...")
        simulated_profit = engine.simulate_battery(
            mw_capacity=500,
            mwh_duration=2,
            charge_threshold=0,
            discharge_threshold=150
        )
        
        print("="*45)
        print("        BATTERY ARBITRAGE SUMMARY")
        print("="*45)
        print(f"Simulated Battery Gross Margin:  £{simulated_profit:,.2f}")
        print("="*45 + "\n")
        
    except Exception as e:
        print(f"\nExecution failed: {e}")
