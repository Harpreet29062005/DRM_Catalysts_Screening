"""
Dry Reforming of Methane (DRM) — Reaction Mechanism
=====================================================

Overall reaction:  CH4 + CO2 -> 2 CO + 2 H2

This file defines the elementary reaction mechanism for DRM on transition
metal catalysts. Adsorption energies and activation barriers are taken from
published DFT studies.

References:
  [1] Blaylock, D.W. et al. J. Catal. 2009, 266, 54-63. (Ni, Pt DFT)
  [2] Jones, G. et al. ACS Catal. 2016, 6, 6732-6742. (Ni, Pt, Ru)
  [3] Wang, S.-G. et al. J. Catal. 2013, 299, 94-104. (Rh, Co, Ir)
  [4] Norskov, J.K. et al. J. Catal. 2002, 209, 275-278. (Scaling relations)

Key physics:
  - CH4 sequentially dehydrogenates on the surface (CH4 -> CH3 -> CH2 -> CH -> C)
  - CO2 dissociates to CO + O
  - Carbon on the surface is removed by reaction with O (gasification)
  - If carbon accumulates faster than it is removed, the catalyst deactivates
  - The balance between CH dehydrogenation and C gasification determines
    whether a catalyst is carbon-resistant
"""

import numpy as np

kB = 8.617333e-5    # eV/K
h  = 4.135667e-15   # eV*s
R_gas = 8.314       # J/(mol*K)


# ============================================================
# SPECIES
# ============================================================
SPECIES = {
    # Gas phase
    "CH4_g":   {"type": "gas"},
    "CO2_g":   {"type": "gas"},
    "CO_g":    {"type": "gas"},
    "H2_g":    {"type": "gas"},
    "H2O_g":   {"type": "gas"},
    # Surface
    "*":       {"type": "site", "sites": 1},
    "CH4*":    {"type": "ads",  "sites": 1},
    "CH3*":    {"type": "ads",  "sites": 1},
    "CH2*":    {"type": "ads",  "sites": 1},
    "CH*":     {"type": "ads",  "sites": 1},
    "C*":      {"type": "ads",  "sites": 1},
    "H*":      {"type": "ads",  "sites": 1},
    "O*":      {"type": "ads",  "sites": 1},
    "CO*":     {"type": "ads",  "sites": 1},
    "CO2*":    {"type": "ads",  "sites": 1},
    "OH*":     {"type": "ads",  "sites": 1},
    "H2O*":    {"type": "ads",  "sites": 1},
}


# ============================================================
# ADSORPTION ENERGIES (eV) - Ni(111) BASELINE
# ============================================================
# Convention: E_ads = E(surf+ads) - E(surf) - E(gas)
# All values from published DFT literature (see references above).
#
# Note: C* and CH* bind very strongly on Ni (-6.4 and -6.5 eV). This is why
# Ni deactivates by carbon deposition. Pt and other catalysts bind them more
# weakly, which is why they are more carbon-resistant.
# ============================================================
ADSORPTION_ENERGIES = {
    "CH4*":   -0.02,   # physisorbed
    "CH3*":   -1.95,
    "CH2*":   -3.60,
    "CH*":    -6.50,
    "C*":     -6.40,
    "H*":     -0.52,
    "O*":     -5.50,
    "CO*":    -1.30,
    "CO2*":   -0.15,
    "OH*":    -3.10,
    "H2O*":   -0.30,
}


# ============================================================
# ELEMENTARY REACTION STEPS
# ============================================================
# 14-step mechanism for DRM on Ni(111).
# Ea values are forward barriers in eV, from published DFT (NEB calculations).
# ============================================================
ELEMENTARY_STEPS = [
    # --- Methane sequential dehydrogenation ---
    {
        "name": "CH4_dissociative_adsorption",
        "reactants": {"CH4_g": 1, "*": 2},
        "products":  {"CH3*": 1, "H*": 1},
        "Ea_fwd": 0.85,
        "Ea_rev": None,
        "reversible": True,
    },
    {
        "name": "CH3_dehydrogenation",
        "reactants": {"CH3*": 1, "*": 1},
        "products":  {"CH2*": 1, "H*": 1},
        "Ea_fwd": 0.55,
        "Ea_rev": None,
        "reversible": True,
    },
    {
        "name": "CH2_dehydrogenation",
        "reactants": {"CH2*": 1, "*": 1},
        "products":  {"CH*": 1, "H*": 1},
        "Ea_fwd": 0.35,
        "Ea_rev": None,
        "reversible": True,
    },
    {
        "name": "CH_dehydrogenation",
        "reactants": {"CH*": 1, "*": 1},
        "products":  {"C*": 1, "H*": 1},
        "Ea_fwd": 0.85,
        "Ea_rev": None,
        "reversible": True,
    },

    # --- CO2 activation ---
    {
        "name": "CO2_adsorption",
        "reactants": {"CO2_g": 1, "*": 1},
        "products":  {"CO2*": 1},
        "Ea_fwd": 0.0,
        "Ea_rev": None,
        "reversible": True,
    },
    {
        "name": "CO2_dissociation",
        "reactants": {"CO2*": 1, "*": 1},
        "products":  {"CO*": 1, "O*": 1},
        "Ea_fwd": 0.80,
        "Ea_rev": None,
        "reversible": True,
    },

    # --- Carbon gasification (KEY STEP - removes carbon from surface) ---
    {
        "name": "C_oxidation_by_O",
        "reactants": {"C*": 1, "O*": 1},
        "products":  {"CO*": 1, "*": 1},
        "Ea_fwd": 1.10,
        "Ea_rev": None,
        "reversible": True,
    },
    {
        "name": "Boudouard_reaction",
        "reactants": {"C*": 1, "CO2*": 1},
        "products":  {"CO*": 2},
        "Ea_fwd": 1.30,
        "Ea_rev": None,
        "reversible": True,
    },

    # --- CO desorption ---
    {
        "name": "CO_desorption",
        "reactants": {"CO*": 1},
        "products":  {"CO_g": 1, "*": 1},
        "Ea_fwd": None,
        "Ea_rev": 0.0,
        "reversible": True,
    },

    # --- H2 formation and desorption ---
    {
        "name": "H_recombination",
        "reactants": {"H*": 2},
        "products":  {"H2_g": 1, "*": 2},
        "Ea_fwd": 0.85,
        "Ea_rev": None,
        "reversible": True,
    },

    # --- Water formation (side path) ---
    {
        "name": "OH_formation",
        "reactants": {"O*": 1, "H*": 1},
        "products":  {"OH*": 1, "*": 1},
        "Ea_fwd": 0.75,
        "Ea_rev": None,
        "reversible": True,
    },
    {
        "name": "H2O_formation",
        "reactants": {"OH*": 1, "H*": 1},
        "products":  {"H2O*": 1, "*": 1},
        "Ea_fwd": 0.35,
        "Ea_rev": None,
        "reversible": True,
    },
    {
        "name": "H2O_desorption",
        "reactants": {"H2O*": 1},
        "products":  {"H2O_g": 1, "*": 1},
        "Ea_fwd": None,
        "Ea_rev": 0.0,
        "reversible": True,
    },

    # --- Reverse methane formation (minor at DRM conditions) ---
    {
        "name": "CH_oxidation",
        "reactants": {"CH*": 1, "O*": 1},
        "products":  {"CO*": 1, "H*": 1},
        "Ea_fwd": 1.00,
        "Ea_rev": None,
        "reversible": True,
    },
]


# ============================================================
# CATALYST DEFINITIONS (shifts relative to Ni(111) baseline)
# ============================================================
# Shifts derived from published DFT comparisons:
#   - Pt: binds CH/C more weakly (carbon-resistant)
#   - Ru: similar to Ni but slightly stronger C binding
#   - Rh: moderate C binding
#   - Co: similar to Ni
#   - Ir: weak C binding (carbon-resistant)
#
# Positive dE_C means weaker carbon binding.
# ============================================================
CATALYSTS = {
    "Ni(111)":  {"dE_CH4": 0.00, "dE_C": 0.00,  "dE_O": 0.00,  "color": "#A23B72"},
    "Pt(111)":  {"dE_CH4": 0.10, "dE_C": 1.20,  "dE_O": 1.20,  "color": "#2E86AB"},
    "Ru(0001)": {"dE_CH4": 0.05, "dE_C": 0.60,  "dE_O": 0.90,  "color": "#F18F01"},
    "Rh(111)":  {"dE_CH4": 0.10, "dE_C": 1.00,  "dE_O": 1.20,  "color": "#6A994E"},
    "Co(0001)": {"dE_CH4": 0.05, "dE_C": 0.30,  "dE_O": 0.40,  "color": "#BC4749"},
    "Ir(111)":  {"dE_CH4": 0.10, "dE_C": 1.40,  "dE_O": 1.30,  "color": "#7B68EE"},
}


# ============================================================
# SCALING RELATIONS
# ============================================================
# Bindings that scale with C binding (from BEP and scaling)
SCALING_RELATIONS = {
    "CH3*": {"descriptor": "C", "slope": 0.30, "intercept": -1.95},
    "CH2*": {"descriptor": "C", "slope": 0.55, "intercept": -3.60},
    "CH*":  {"descriptor": "C", "slope": 0.85, "intercept": -6.50},
    "CO*":  {"descriptor": "O", "slope": 0.60, "intercept": -1.30},
    "OH*":  {"descriptor": "O", "slope": 0.40, "intercept": -3.10},
}


# ============================================================
# ADSORPTION ENERGY FUNCTION WITH DESCRIPTOR SHIFTS
# ============================================================

def get_adsorption_energy(species, dE_CH4=0.0, dE_C=0.0, dE_O=0.0):
    """
    Return the adsorption energy of a species given catalyst descriptors.

    Parameters
    ----------
    species : str
    dE_CH4 : float — shift in CH4 binding (changes CH4 adsorption)
    dE_C : float — shift in C binding (changes all carbon species)
    dE_O : float — shift in O binding (changes O, OH, CO)
    """
    base = ADSORPTION_ENERGIES.get(species, None)
    if base is None:
        return 0.0

    # Direct descriptors
    if species == "CH4*":
        return base + dE_CH4
    if species == "C*":
        return base + dE_C
    if species == "O*":
        return base + dE_O

    # Species scaling with C binding
    if species == "CH3*":
        return base + 0.30 * dE_C
    if species == "CH2*":
        return base + 0.55 * dE_C
    if species == "CH*":
        return base + 0.85 * dE_C

    # Species scaling with O binding
    if species == "CO*":
        return base + 0.60 * dE_O
    if species == "OH*":
        return base + 0.40 * dE_O
    if species == "CO2*":
        return base + 0.20 * dE_O

    # Hydrogen and water — no shift
    if species in ("H*", "H2O*"):
        return base

    return base


# ============================================================
# DEFAULT REACTION CONDITIONS
# ============================================================
# Industrial DRM operates at 700-1000 K, 1-20 bar
# CH4:CO2 typically 1:1 (equimolar)
DEFAULT_CONDITIONS = {
    "T": 900.0,          # K — typical DRM temperature
    "P_total": 1.0,      # bar — DRM can run near atmospheric
    "y_CH4": 0.45,       # equimolar
    "y_CO2": 0.45,
    "y_inert": 0.10,     # N2 balance
}


# ============================================================
# SELF-TEST
# ============================================================
if __name__ == "__main__":
    print("=" * 65)
    print("DRM Mechanism File — Self-Test")
    print("=" * 65)
    print(f"Species: {len(SPECIES)}")
    print(f"Elementary steps: {len(ELEMENTARY_STEPS)}")
    print(f"Catalysts: {len(CATALYSTS)}")
    print()

    print("Ni(111) adsorption energies (eV):")
    for sp, e in ADSORPTION_ENERGIES.items():
        print(f"  {sp:<8} : {e:+.2f}")
    print()

    print("Catalyst C-binding shifts (relative to Ni(111)):")
    for name, cat in CATALYSTS.items():
        e_c = get_adsorption_energy("C*", cat["dE_CH4"], cat["dE_C"], cat["dE_O"])
        e_ch = get_adsorption_energy("CH*", cat["dE_CH4"], cat["dE_C"], cat["dE_O"])
        print(f"  {name:<10} E_C = {e_c:+.2f} eV    E_CH = {e_ch:+.2f} eV")
    print()

    print("Note: Pt, Rh, Ir bind C* more weakly than Ni — that is why they")
    print("are carbon-resistant at DRM conditions.")

    print()
    print("Reaction step summary:")
    for i, step in enumerate(ELEMENTARY_STEPS, 1):
        print(f"  {i:2}. {step['name']:<30} Ea_fwd = {step['Ea_fwd']}")
    print()
    print("OK Mechanism file loaded.")