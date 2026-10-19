import numpy as np
from ase.build import fcc111, add_adsorbate
from ase.constraints import FixAtoms
from ase import Atoms
from gpaw import GPAW, PW

print("==================================================")
print(" STARTING DFT CALCULATION: Carbon on Pt(111)")
print("==================================================")

# 1. Build the Pt(111) slab
print("Building Pt(111) slab...")
slab = fcc111('Pt', size=(2, 2, 3), vacuum=10.0)
# Fix the bottom two layers to simulate a bulk surface
constraint = FixAtoms(mask=[atom.tag > 1 for atom in slab])
slab.set_constraint(constraint)

# 2. Set up the DFT Calculator
# We use a 300 eV plane-wave cutoff to ensure it runs quickly on a laptop
calc = GPAW(mode=PW(300),       
            kpts=(2, 2, 1),     
            xc='PBE',           
            txt='dft_clean_slab.txt') 
slab.calc = calc

# 3. Calculate Energy of the Clean Slab
print("Calculating energy of the CLEAN Pt slab (this may take 1-2 minutes)...")
E_slab = slab.get_potential_energy()
print(f"Clean Slab Energy: {E_slab:.4f} eV")

# 4. Add the Carbon Atom
print("Adding Carbon atom to the surface...")
add_adsorbate(slab, 'C', height=1.5, position='fcc')

# We need a new calculator for the new system
calc_new = GPAW(mode=PW(300), kpts=(2, 2, 1), xc='PBE', txt='dft_C_Pt.txt')
slab.calc = calc_new

# 5. Calculate Energy of the Slab + Carbon
print("Calculating energy of C on Pt(111) (this may take 2-3 minutes)...")
E_slab_C = slab.get_potential_energy()
print(f"Slab + Carbon Energy: {E_slab_C:.4f} eV")

# 6. Calculate the Binding Energy
print("Calculating energy of isolated Carbon atom...")
c_atom = Atoms('C', positions=[(5.0, 5.0, 5.0)], cell=(10, 10, 10))
c_atom.calc = GPAW(mode=PW(300), xc='PBE', txt=None)
E_C = c_atom.get_potential_energy()

# Binding Energy = E(slab+C) - E(slab) - E(C)
E_bind = E_slab_C - E_slab - E_C

print("\n==================================================")
print(f" DFT CALCULATION COMPLETE!")
print(f" Carbon Binding Energy on Pt(111) = {E_bind:.3f} eV")
print("==================================================")
