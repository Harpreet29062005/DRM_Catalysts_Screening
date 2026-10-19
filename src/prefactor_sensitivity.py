"""
Pre-exponential Factor Sensitivity Analysis (Corrected)
========================================================
Uses step-specific literature prefactors as the baseline instead of a
global 1e13 s^-1. Then perturbs each prefactor by a random factor drawn
log-uniformly from [0.1x, 10x] to test ranking robustness.
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
import sys, os, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microkinetics as mk
from mechanism import CATALYSTS, ELEMENTARY_STEPS


N_SAMPLES = 20
LOG_RANGE = (-1.0, 1.0)   # +/- one order of magnitude around the literature value


# Literature-derived pre-exponential factors (s^-1) for DRM elementary steps.
# Sources:
#   - Blaylock et al. 2009 (Ni(111) DFT-derived prefactors)
#   - Jones et al. 2009 (Pt, Ru)
#   - Wang et al. 2009 (Rh)
LITERATURE_PREFACTORS = {
    "CH4_dissociative_adsorption": 1.0e12,
    "CH3_dehydrogenation":         1.0e13,
    "CH2_dehydrogenation":         1.0e13,
    "CH_dehydrogenation":          1.0e13,
    "CO2_adsorption":              1.0e12,   # (value used only if step exists)
    "CO2_dissociation":            1.0e12,
    "C_oxidation_by_O":            1.0e13,
    "Boudouard_reaction":          1.0e12,
    "CO_desorption":               1.0e13,
    "H_recombination":             1.0e13,
    "OH_formation":                1.0e13,
    "H2O_formation":               1.0e13,
    "H2O_desorption":              1.0e13,
    "CH_oxidation":                1.0e13,
}


def solve_with_prefactors(catalyst_name, prefactors, T=900.0, P_total=1.0):
    """Solve DRM steady state with custom prefactors per step."""
    cat = CATALYSTS[catalyst_name]
    dE_CH4, dE_C, dE_O = cat["dE_CH4"], cat["dE_C"], cat["dE_O"]

    P_dict = {
        "CH4_g": P_total * 0.45, "CO2_g": P_total * 0.45,
        "CO_g": 0.0, "H2_g": 0.0, "H2O_g": 0.0,
    }

    k_fwd_base, k_rev_base = mk.compute_rate_constants(
        T, P_dict, dE_CH4, dE_C, dE_O
    )

    # Apply custom prefactor ratio
    nu_default = 1e13
    k_fwd, k_rev = {}, {}
    for step in ELEMENTARY_STEPS:
        name = step["name"]
        ratio = prefactors.get(name, nu_default) / nu_default
        k_fwd[name] = k_fwd_base[name] * ratio
        k_rev[name] = k_rev_base[name] * ratio

    # Solve
    theta0 = np.ones(mk.N - 1) * 1e-6
    sol = solve_ivp(mk.rhs, t_span=(0, 1e6), y0=theta0,
                    args=(k_fwd, k_rev), method="BDF",
                    rtol=1e-6, atol=1e-10, max_step=1e5)

    theta_final = np.clip(sol.y[:, -1], 0.0, 1.0)
    occ = np.sum(theta_final)
    if occ > 1.0:
        theta_final = theta_final / occ * 0.99
    theta = np.zeros(mk.N)
    theta[1:] = theta_final
    theta[0] = max(1.0 - np.sum(theta_final), 0.0)

    theta_C = theta[mk.SP["C*"]]
    theta_CH = theta[mk.SP["CH*"]]
    return theta_C + theta_CH


def main():
    print("=" * 70)
    print("PRE-EXPONENTIAL FACTOR SENSITIVITY (Literature-Based)")
    print("=" * 70)
    print()
    print(f"Method: {N_SAMPLES} random prefactor sets per catalyst,")
    print("        each perturbed by a random factor drawn log-uniformly")
    print("        from 0.1x to 10x the literature value.")
    print()

    rng = np.random.default_rng(42)
    catalysts = list(CATALYSTS.keys())
    results = {cat: [] for cat in catalysts}

    for cat in catalysts:
        print(f"Running {cat}...")
        for _ in range(N_SAMPLES):
            prefactors = {}
            for step in ELEMENTARY_STEPS:
                name = step["name"]
                base = LITERATURE_PREFACTORS.get(name, 1e13)
                prefactors[name] = base * (10 ** rng.uniform(*LOG_RANGE))
            try:
                carbon = solve_with_prefactors(cat, prefactors)
                if np.isfinite(carbon):
                    results[cat].append(carbon)
            except Exception:
                continue

    print()
    print("=" * 70)
    print("CARBON COVERAGE ACROSS PREFACTOR REALIZATIONS")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'Mean':>12}{'Std':>12}{'Min':>12}{'Max':>12}")
    print("-" * 60)
    for cat in catalysts:
        arr = np.array(results[cat])
        if len(arr) == 0:
            print(f"{cat:<12}{'N/A':>12}")
            continue
        print(f"{cat:<12}{arr.mean():>12.3e}{arr.std():>12.3e}"
              f"{arr.min():>12.3e}{arr.max():>12.3e}")

    # Ranking stability
    print()
    print("=" * 70)
    print("RANKING STABILITY CHECK")
    print("=" * 70)
    print()
    reference_order = ["Ir(111)", "Pt(111)", "Rh(111)", "Ru(0001)",
                       "Co(0001)", "Ni(111)"]
    print("Reference ranking (literature prefactors): "
          "Ir > Pt > Rh > Ru > Co > Ni")
    print()

    n_samples_valid = min(len(results[c]) for c in catalysts)
    stable_count = 0
    for i in range(n_samples_valid):
        sample_vals = {c: results[c][i] for c in catalysts}
        ranked = sorted(sample_vals.items(), key=lambda x: x[1])
        ranked_names = [r[0] for r in ranked]
        if ranked_names == reference_order:
            stable_count += 1

    print(f"Reference ranking preserved in "
          f"{stable_count} / {n_samples_valid} prefactor realizations")
    if n_samples_valid > 0:
        print(f"  ({100*stable_count/n_samples_valid:.0f}% success rate)")

    # Figure
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [CATALYSTS[c]["color"] for c in catalysts]
    data = [results[c] for c in catalysts if len(results[c]) > 0]
    names = [c for c in catalysts if len(results[c]) > 0]

    if data:
        bp = ax.boxplot(data, tick_labels=names, patch_artist=True, showfliers=True)
        for patch, color in zip(bp["boxes"], colors[:len(names)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax.set_ylabel("Total carbon coverage (θ_C + θ_CH)", fontsize=12)
    ax.set_title(f"Carbon Coverage Distribution across {N_SAMPLES} "
                 f"Perturbed Prefactor Sets\n(±1 order of magnitude around "
                 f"literature values)",
                 fontsize=12, fontweight="bold")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, which="both")
    plt.setp(ax.get_xticklabels(), rotation=20)

    plt.tight_layout()
    os.makedirs("results/figures", exist_ok=True)
    plt.savefig("results/figures/prefactor_sensitivity.png",
                dpi=200, bbox_inches="tight")
    plt.close()
    print(f"\nOK Saved: results/figures/prefactor_sensitivity.png")


if __name__ == "__main__":
    main()