import matplotlib.pyplot as plt
import numpy as np
import os

# Data from your original paper (Table 3)
old_tof = [7.81, 8.51, 13.0, 9.49, 2.75, 2.14] 
# Data from your new realistic run (from the cmd screen)
new_tof = [0.647, 0.671, 0.736, 0.874, 0.819, 0.617]
catalysts = ['Ir(111)', 'Pt(111)', 'Rh(111)', 'Ru(0001)', 'Co(0001)', 'Ni(111)']

x = np.arange(len(catalysts))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
rects1 = ax.bar(x - width/2, old_tof, width, label='Ideal (Sticking = 1.0)', color='gray', edgecolor='black')
rects2 = ax.bar(x + width/2, new_tof, width, label='Realistic Sticking', color='tab:blue', edgecolor='black')

ax.set_ylabel('Turnover Frequency (s^-1)', fontsize=12)
ax.set_title('Effect of Realistic Sticking Coefficients on DRM Activity', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(catalysts, fontsize=11)
ax.legend(fontsize=11)
ax.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
save_path = "../results/sticking_comparison.png"
os.makedirs(os.path.dirname(save_path), exist_ok=True)
plt.savefig(save_path, dpi=300)
print(f"Saved figure to {save_path}")
plt.show()