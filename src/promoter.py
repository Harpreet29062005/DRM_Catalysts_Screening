"""
Virtual Promoter Screening for Ni(111)
======================================
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Ensure we can import from the src folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import CATALYSTS
from microkinetics import solve_drm

def run_promoter_screening():
    promoter_shifts = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    carbon_coverages = []
    tofs = []
    
    # Save the original dE_C for Ni(111)
    original_dE_C = CATALYSTS["Ni(111)"]["dE_C"]
    
    print("\n--- STARTING VIRTUAL PROMOTER SCREENING FOR NI(111) ---")
    print("This may take a minute as it runs the stiff ODE solver 6 times...\n")

    for shift in promoter_shifts:
        # 1. Apply the promoter shift
        CATALYSTS["Ni(111)"]["dE_C"] = original_dE_C + shift
        
        # 2. Run the actual ODE solver
        result = solve_drm(catalyst_name="Ni(111)", verbose=False)
        
        # 3. Extract data
        theta_C = result["theta_C"]
        theta_CH = result["theta_CH"]
        tof = result["TOF_CH4"]
        
        total_carbon = theta_C + theta_CH
        carbon_coverages.append(total_carbon)
        tofs.append(tof)
        
        print(f"Shift: +{shift:.1f} eV | Total Carbon: {total_carbon:.4e} | TOF: {tof:.2f} s^-1")
        
    # 4. Reset Ni back to its original state
    CATALYSTS["Ni(111)"]["dE_C"] = original_dE_C

    # ==========================================
    # PLOTTING
    # ==========================================
    fig, ax1 = plt.subplots(figsize=(8, 5))

    color = 'tab:red'
    ax1.set_xlabel('Virtual Promoter Shift on Ni (dE_C shift, eV)', fontsize=12)
    ax1.set_ylabel('Total Carbon Coverage (theta_C + theta_CH)', color=color, fontsize=12)
    ax1.semilogy(promoter_shifts, carbon_coverages, 'o-', color=color, linewidth=2, markersize=8)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.axhline(y=1e-2, color='black', linestyle='--', label='Coking Threshold (1e-2 ML)')

    ax2 = ax1.twinx()  
    color = 'tab:blue'
    ax2.set_ylabel('Turnover Frequency (s^-1)', color=color, fontsize=12)
    ax2.plot(promoter_shifts, tofs, 's--', color=color, linewidth=2, markersize=8)
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('Virtual Promoter Screening for Ni(111) at 900 K', fontsize=14, fontweight='bold')
    fig.tight_layout()
    plt.grid(True, alpha=0.3, which='both')
    
    # Save the figure to the results folder
    save_path = "../results/promoter_screening.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    print(f"\nOK: Saved figure to {save_path}")
    
    plt.show()

if __name__ == "__main__":
    run_promoter_screening()