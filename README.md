# Real-Space Topological Invariants Visualization Suite

An interactive, modular project for computing and visualizing the Bott index, spectral localizer, and related real-space diagnostics for topological insulators. The implementation is designed around the real-space formulations developed by Hastings and Loring, with no momentum-space or Bloch-wave machinery anywhere in the stack.

The core idea is simple: in a finite disordered lattice, topology can still be detected from how projected position operators fail to commute. Instead of looking at band structure in `k`-space, we build the Hamiltonian directly on the lattice, form the Fermi projection, compress the position operators into the occupied subspace, and extract integer-valued topological information from their almost-commuting structure. This makes the approach especially useful for disorder, open boundaries, and finite systems where translational symmetry is broken.

## Project Goals

The suite is built to demonstrate three linked facts in a concrete computational way:

1. Noncommuting projected position operators encode topology.
2. The winding of eigenvalues of `W = U V U^dagger V^dagger` produces an integer Bott index.
3. The spectral localizer gap closes near topological phase transitions.

Every computational module must stay in real space, use `numpy.complex128` for matrix operations, log validation checks, and export data that follows the shared JSON contract.

## Project Structure

The intended layout is modular so that physics code, rendering code, and exports can evolve independently:

```text
new-project/
  README.md
  backend/
    physics/
      hamiltonian.py
      bott.py
      localizer.py
      validation.py
      cache.py
    exports/
      json_export.py
      png_export.py
  frontend/
    js/
      app.js
      state.js
      utils/
      canvas/
      three/
      math/
    styles/
      main.css
  data/
    cache/
    exports/
  logs/
    physics_checks/
    performance/
```

## Real-Space Bott Index Intuition

Consider a finite lattice Hamiltonian `H` with Fermi energy `E_F`. We diagonalize `H`, construct the Fermi projector `P` onto states below `E_F`, and then compress the position information into the occupied subspace. On a periodic geometry, the position operators are exponentiated to produce unitary-like operators associated with the two lattice directions. After projection, these operators are no longer exactly commuting. Their residual noncommutativity is the topological signal.

If the occupied space is topologically trivial, the compressed operators can be made approximately commuting in a way compatible with localized Wannier functions. In a nontrivial phase, an obstruction remains, and the Bott index captures it as an integer. This is why the Bott index is so powerful in disordered systems: it uses only the geometry of occupied states in real space.

## Physics Cheat Sheet

The formulas below are written in a PreTeXt-friendly form so they can be reused directly in the frontend math panels.

```xml
<section xml:id="physics-cheat-sheet">
  <title>Physics Cheat Sheet</title>

  <p>
    Let <m>H</m> be the finite lattice Hamiltonian and <m>E_F</m> the Fermi level.
    The occupied-state projector is
    <me>
      P = \sum_{E_n < E_F} | \psi_n \rangle \langle \psi_n |.
    </me>
  </p>

  <p>
    On a lattice of linear size <m>L</m>, define exponentiated position operators
    <me>
      X = \mathrm{diag}(x_1, x_2, \dots, x_N), \qquad
      Y = \mathrm{diag}(y_1, y_2, \dots, y_N),
    </me>
    and
    <me>
      e^{i 2\pi X / L}, \qquad e^{i 2\pi Y / L}.
    </me>
  </p>

  <p>
    Compress these into the occupied subspace:
    <me>
      U = P e^{i 2\pi X / L} P + (I - P), \qquad
      V = P e^{i 2\pi Y / L} P + (I - P).
    </me>
  </p>

  <p>
    The Bott index is computed from the almost-commutator
    <me>
      W = U V U^\ast V^\ast,
    </me>
    via
    <me>
      \mathrm{Bott}(U,V) =
      \frac{1}{2\pi} \operatorname{Im} \operatorname{Tr} \log\!\left(U V U^\ast V^\ast\right).
    </me>
  </p>

  <p>
    In numerics, one also checks approximate unitarity and approximate commutation:
    <me>
      \| U^\ast U - I \| < \varepsilon, \qquad
      \| V^\ast V - I \| < \varepsilon,
    </me>
    and
    <me>
      \| [U,V] \| = \| UV - VU \|.
    </me>
  </p>

  <p>
    A spectral localizer at spatial point <m>(x,y)</m> and energy <m>\lambda</m> is built from
    a Clifford-linear combination of the Hamiltonian and position operators. In schematic form,
    <me>
      L_{(x,y,\lambda)} =
      \kappa (X - x I) \otimes \Gamma_1 +
      \kappa (Y - y I) \otimes \Gamma_2 +
      (H - \lambda I) \otimes \Gamma_3.
    </me>
  </p>

  <p>
    The localizer gap is the smallest singular magnitude of <m>L_{(x,y,\lambda)}</m>.
    Gap closings signal transitions in topology or localization structure.
  </p>
</section>
```

## Numerical and Physics Validation Checklist

Every physics module in this project should log the following checks:

1. Unitarity:
   `||U^dagger U - I|| < epsilon` and `||V^dagger V - I|| < epsilon`
2. Commutator control:
   compare `||[U,V]||` with expected smallness in the gapped regime
3. Integer stability:
   `|bott_index - round(bott_index)| < 1e-6`
4. Gap robustness:
   the spectral gap or localizer gap should remain open under small perturbations of mass, disorder, or Fermi level

These checks are not optional. If one fails, the code should emit a clear warning and continue with graceful degradation where possible.

## Shared Data Contract

All computational modules must export JSON objects of the following exact shape:

```json
{
  "lattice_size": 0,
  "hamiltonian_shape": [0, 0],
  "eigenvalues": [],
  "U_V_matrices": {
    "U": [],
    "V": []
  },
  "localizer_gap_grid": [],
  "bott_index": 0,
  "winding_phases": [],
  "parameters": {
    "mass": 0.0,
    "disorder": 0.0,
    "fermi": 0.0
  }
}
```

Even when a field is not yet populated by a specific module, it must still be present with an explicit fallback value.

## Tech Constraints

### Backend

- Python only
- `numpy`, `scipy.sparse`, `matplotlib`
- `numpy.complex128` for every matrix calculation
- Graceful handling of eigensolver non-convergence
- Hamiltonian caching during parameter sweeps

### Frontend

- Vanilla JavaScript only
- HTML5 Canvas for 2D
- Three.js for 3D
- PreTeXt for all displayed mathematics
- Pretext.js for performance-sensitive text rendering

## Troubleshooting Numerical Issues

### Eigensolver does not converge

- Reduce lattice size first to isolate whether the issue is physical or purely numerical.
- Verify the Hamiltonian is Hermitian to machine precision before diagonalization.
- If using sparse diagonalization, make sure the requested spectral window is compatible with the chosen solver.
- Fall back to a denser but more stable routine for small systems when sparse methods stall.
- Log the parameter set that failed so the frontend can show a meaningful warning instead of silently freezing.

### Loss of integer Bott index

- Check that `U` and `V` are being built from the correct Fermi projector and exponentiated position operators.
- Confirm every intermediate matrix remains `complex128`; mixed precision can spoil the branch structure of the matrix logarithm.
- Measure `||U^dagger U - I||`, `||V^dagger V - I||`, and `||[U,V]||`; large values often indicate insufficient gap protection or a construction bug.
- Inspect whether the system is near a genuine phase transition where the invariant becomes numerically delicate.

### Matrix logarithm becomes unstable

- Examine the eigenvalues of `W = U V U^dagger V^dagger`; instability is common when they approach the branch cut near `-1`.
- Test small parameter perturbations to see whether the branch issue is isolated or physical.
- Compare the extracted winding phases against the integer Bott value to verify consistency.

### Precision loss in disordered systems

- Keep all operators in `complex128` from Hamiltonian construction through export.
- Avoid unnecessary dense conversions for large lattices.
- Cache Hamiltonians so repeated sweeps do not accumulate avoidable floating-point differences from reconstruction.
- Re-run the validation suite after any change in disorder realization, boundary condition, or projector construction.

### Spectral gap appears to vanish unexpectedly

- Distinguish a true physical gap closing from finite-size artifacts by testing nearby system sizes.
- Recompute under small perturbations of mass, disorder, and Fermi level to check persistence.
- For localizer diagnostics, verify that the chosen tuning parameter `kappa` is in a regime that resolves the gap cleanly.

## Performance and Resource Notes

- Log computation time for Bott index evaluations.
- Log memory usage when `L > 100`.
- Log frame rate in any animated frontend module.
- Every Three.js visualization must provide `cleanup()` or `dispose()` to release geometries, materials, textures, controls, and renderers.

## References Guiding the Implementation

- Hastings, M. B. and Loring, T. A. (2010). Topological insulators and `C^\ast`-algebras: Theory and numerical practice.
- Loring, T. A. and Hastings, M. B. (2011). Disordered topological insulators via `C^\ast`-algebras.
- Loring, T. A. (2019). A guide to the Bott index and spectral localizer in finite systems.

The codebase should follow these works as the primary standard for definitions, numerical checks, and interpretation.
