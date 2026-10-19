"""
DRM Numerical Microkinetic Solver
===================================
Real steady-state solver using stiff ODE integration.

14-step mechanism, physical rate constants (Arrhenius + Hertz-Knudsen),
steady state via scipy.integrate.solve_ivp (BDF method).
"""

import numpy as np
from scipy.integrate import solve_ivp
import sys, os, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import (
    kB, ADSORPTION_ENERGIES, ELEMENTARY_STEPS,
    CATALYSTS, get_adsorption_energy,
)

kB_SI = 1.38e-23
N_sites_m2 = 1.77e19

# Global BEP scale factor — 1.0 is the baseline, can be varied for robustness
BEP_SCALE = 1.0


# ============================================================
# RATE CONSTANTS
# ============================================================

def k_arrhenius(Ea, T, nu=1e13):
    return nu * np.exp(-Ea / (kB * T))


def k_adsorption(T, P_bar, m_kg):
    P_pa = P_bar * 1e5
    flux = P_pa / np.sqrt(2 * np.pi * m_kg * kB_SI * T)
    return flux / N_sites_m2


MOLAR_MASSES = {
    "CH4_g": 16.0 * 1.66e-27,
    "CO2_g": 44.0 * 1.66e-27,
    "CO_g": 28.0 * 1.66e-27,
    "H2_g": 2.0 * 1.66e-27,
    "H2O_g": 18.0 * 1.66e-27,
}


def compute_rate_constants(T, P_dict, dE_CH4, dE_C, dE_O):
    k_fwd, k_rev = {}, {}
    nu = 1e13

    for step in ELEMENTARY_STEPS:
        name = step["name"]
        Ea_fwd = step["Ea_fwd"] if step["Ea_fwd"] is not None else 0.01

        # --- CH4 dissociative adsorption ---
        if name == "CH4_dissociative_adsorption":
            P = P_dict.get("CH4_g", 0.0)
            k_fwd[name] = 0.01 * k_adsorption(T, P, MOLAR_MASSES["CH4_g"])
            E_CH3 = get_adsorption_energy("CH3*", dE_CH4, dE_C, dE_O)
            E_H = get_adsorption_energy("H*", dE_CH4, dE_C, dE_O)
            Ea_rev = max(0.85 + E_CH3 + E_H, 0.05)
            k_rev[name] = k_arrhenius(Ea_rev, T, nu)

        # --- CO2 adsorption ---
        elif name == "CO2_adsorption":
            P = P_dict.get("CO2_g", 0.0)
            k_fwd[name] = 0.001 * k_adsorption(T, P, MOLAR_MASSES["CO2_g"])
            E_CO2 = get_adsorption_energy("CO2*", dE_CH4, dE_C, dE_O)
            Ea_rev = max(-E_CO2, 0.05)
            k_rev[name] = k_arrhenius(Ea_rev, T, nu)

        # --- CO desorption ---
        elif name == "CO_desorption":
            E_CO = get_adsorption_energy("CO*", dE_CH4, dE_C, dE_O)
            Ea_fwd_des = max(-E_CO, 0.05)
            k_fwd[name] = k_arrhenius(Ea_fwd_des, T, nu)
            P = P_dict.get("CO_g", 0.0)
            k_rev[name] = k_adsorption(T, P, MOLAR_MASSES["CO_g"])

        # --- H2 recombination/desorption ---
        elif name == "H_recombination":
            E_H = get_adsorption_energy("H*", dE_CH4, dE_C, dE_O)
            Ea_fwd_des = max(-2 * E_H, 0.05)
            k_fwd[name] = k_arrhenius(Ea_fwd_des, T, nu)
            P = P_dict.get("H2_g", 0.0)
            k_rev[name] = k_adsorption(T, P, MOLAR_MASSES["H2_g"])

        # --- H2O desorption ---
        elif name == "H2O_desorption":
            E_H2O = get_adsorption_energy("H2O*", dE_CH4, dE_C, dE_O)
            Ea_fwd_des = max(-E_H2O, 0.05)
            k_fwd[name] = k_arrhenius(Ea_fwd_des, T, nu)
            P = P_dict.get("H2O_g", 0.0)
            k_rev[name] = k_adsorption(T, P, MOLAR_MASSES["H2O_g"])

        # --- Surface reactions ---
        else:
            # BEP scaling of carbon-forming dehydrogenation barriers
            BEP_CARBON = {
                "CH3_dehydrogenation": 0.55 * BEP_SCALE,
                "CH2_dehydrogenation": 0.35 * BEP_SCALE,
                "CH_dehydrogenation":  0.60 * BEP_SCALE,
            }
            if name in BEP_CARBON:
                Ea_fwd_effective = Ea_fwd + BEP_CARBON[name] * dE_C
            else:
                Ea_fwd_effective = Ea_fwd

            k_fwd[name] = k_arrhenius(Ea_fwd_effective, T, nu)

            # Reverse barrier from thermodynamics
            dE = 0.0
            for sp, st in step["products"].items():
                if sp.endswith("_g") or sp == "*":
                    continue
                dE += st * get_adsorption_energy(sp, dE_CH4, dE_C, dE_O)
            for sp, st in step["reactants"].items():
                if sp.endswith("_g") or sp == "*":
                    continue
                dE -= st * get_adsorption_energy(sp, dE_CH4, dE_C, dE_O)

            Ea_rev = max(Ea_fwd_effective + dE, 0.05)
            k_rev[name] = k_arrhenius(Ea_rev, T, nu)

    return k_fwd, k_rev


# ============================================================
# SPECIES
# ============================================================
SURFACE_SPECIES = ["*", "CH4*", "CH3*", "CH2*", "CH*", "C*",
                    "CO2*", "O*", "CO*", "H*", "OH*", "H2O*"]
SP = {s: i for i, s in enumerate(SURFACE_SPECIES)}
N = len(SURFACE_SPECIES)


# ============================================================
# ODE RHS
# ============================================================

def rhs(t, theta, k_fwd, k_rev):
    theta_full = np.zeros(N)
    theta_full[1:] = np.clip(theta, 0.0, 1.0)
    occupied = np.sum(theta_full[1:])
    if occupied > 1.0:
        return -100.0 * theta / max(np.sum(np.abs(theta)), 1e-10)
    theta_full[0] = max(1.0 - occupied, 0.0)

    dtheta = np.zeros(N)
    for step in ELEMENTARY_STEPS:
        name = step["name"]
        Qf, Qr = 1.0, 1.0
        for sp, st in step["reactants"].items():
            if sp.endswith("_g"):
                continue
            Qf *= max(theta_full[SP[sp]], 1e-30) ** st
        for sp, st in step["products"].items():
            if sp.endswith("_g"):
                continue
            Qr *= max(theta_full[SP[sp]], 1e-30) ** st
        r = k_fwd[name] * Qf - k_rev[name] * Qr
        for sp, st in step["reactants"].items():
            if sp.endswith("_g"):
                continue
            dtheta[SP[sp]] -= st * r
        for sp, st in step["products"].items():
            if sp.endswith("_g"):
                continue
            dtheta[SP[sp]] += st * r

    return dtheta[1:]


# ============================================================
# SOLVE
# ============================================================

def solve_drm(catalyst_name="Ni(111)", T=900.0, P_total=1.0,
              y_CH4=0.45, y_CO2=0.45, verbose=True):
    cat = CATALYSTS[catalyst_name]
    dE_CH4, dE_C, dE_O = cat["dE_CH4"], cat["dE_C"], cat["dE_O"]

    P_dict = {
        "CH4_g": P_total * y_CH4,
        "CO2_g": P_total * y_CO2,
        "CO_g": 0.0,
        "H2_g": 0.0,
        "H2O_g": 0.0,
    }

    k_fwd, k_rev = compute_rate_constants(T, P_dict, dE_CH4, dE_C, dE_O)

    theta0 = np.ones(N - 1) * 1e-6
    sol = solve_ivp(
        rhs, t_span=(0, 1e6), y0=theta0,
        args=(k_fwd, k_rev),
        method="BDF", rtol=1e-6, atol=1e-10,
        max_step=1e5,
    )

    theta_final = np.clip(sol.y[:, -1], 0.0, 1.0)
    occupied = np.sum(theta_final)
    if occupied > 1.0:
        theta_final = theta_final / occupied * 0.99
    theta = np.zeros(N)
    theta[1:] = theta_final
    theta[0] = max(1.0 - np.sum(theta_final), 0.0)
    theta_dict = {sp: theta[i] for sp, i in SP.items()}

    rates = {}
    for step in ELEMENTARY_STEPS:
        name = step["name"]
        Qf, Qr = 1.0, 1.0
        for sp, st in step["reactants"].items():
            if sp.endswith("_g"):
                continue
            Qf *= max(theta[SP[sp]], 1e-30) ** st
        for sp, st in step["products"].items():
            if sp.endswith("_g"):
                continue
            Qr *= max(theta[SP[sp]], 1e-30) ** st
        rates[name] = k_fwd[name] * Qf - k_rev[name] * Qr

    tof_ch4 = rates["CH4_dissociative_adsorption"]
    tof_co = rates["CO_desorption"]
    tof_h2 = rates["H_recombination"] / 2.0

    if verbose:
        print(f"\n{'='*70}")
        print(f"Catalyst: {catalyst_name}    T = {T} K    P = {P_total} bar")
        print(f"{'='*70}")
        print(f"\nCoverages (sum = {sum(theta):.4f}):")
        for sp in SURFACE_SPECIES:
            if theta[SP[sp]] > 1e-15 or sp == "*":
                print(f"  {sp:<8} : {theta[SP[sp]]:.4e}")
        print(f"\nTurnover frequencies (s^-1):")
        print(f"  TOF_CH4 = {tof_ch4:+.4e}")
        print(f"  TOF_CO  = {tof_co:+.4e}")
        print(f"  TOF_H2  = {tof_h2:+.4e}")
        print(f"\nCarbon analysis:")
        print(f"  θ_C  = {theta[SP['C*']]:.4e}")
        print(f"  θ_CH = {theta[SP['CH*']]:.4e}")
        print(f"  θ_O  = {theta[SP['O*']]:.4e}")

    return {
        "catalyst": catalyst_name,
        "theta": theta_dict,
        "TOF_CH4": tof_ch4,
        "TOF_CO": tof_co,
        "TOF_H2": tof_h2,
        "theta_C": theta[SP['C*']],
        "theta_O": theta[SP['O*']],
        "theta_CH": theta[SP['CH*']],
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DRM NUMERICAL MICROKINETIC SOLVER")
    print("=" * 70)
    print(f"\nBEP_SCALE = {BEP_SCALE}")

    print("\n[Base case] Ni(111) at 900 K, 1 bar")
    result_ni = solve_drm("Ni(111)")

    print(f"\n{'='*70}")
    print("CATALYST COMPARISON AT T = 900 K, P = 1 bar")
    print(f"{'='*70}\n")
    print(f"{'Catalyst':<12}{'TOF_CH4':>14}{'θ_C':>12}{'θ_O':>12}{'θ_CH':>12}")
    print("-" * 62)

    results = {}
    for name in CATALYSTS:
        r = solve_drm(name, verbose=False)
        results[name] = r
        print(f"{name:<12}{r['TOF_CH4']:>14.3e}{r['theta_C']:>12.3e}"
              f"{r['theta_O']:>12.3e}{r['theta_CH']:>12.3e}")

    print(f"\n{'='*70}")
    print("CARBON RESISTANCE RANKING (based on θ_C and θ_CH)")
    print(f"{'='*70}\n")

    ranked = sorted(results.items(),
                    key=lambda x: x[1]['theta_C'] + x[1]['theta_CH'])
    for i, (name, r) in enumerate(ranked, 1):
        total_c = r['theta_C'] + r['theta_CH']
        bar = "█" * int(max(0, 1 - min(total_c * 5, 1)) * 30)
        print(f"  {i}. {name:<12} total C = {total_c:.3e}  {bar}")

    print(f"\n{'='*70}")
    print("OK Solver completed.")