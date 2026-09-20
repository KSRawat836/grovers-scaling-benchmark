# Grover's Algorithm — Simulator Performance & Scaling Analysis

An implementation of Grover's search algorithm in Qiskit, extended with two experiments:
(1) how measurement shot count affects success probability convergence, and
(2) how different Aer simulator backends scale with qubit count.

## What this is

Standard Grover's search (oracle + diffuser, optimal iteration count via
`floor((pi/4) * sqrt(2^n))`), built to find a target n-bit password. On top
of the base algorithm, this project investigates two practical questions
that most tutorial implementations skip:

1. **How many shots are actually needed** to reliably find the correct
   answer, and how does that interact with iteration count?
2. **Which Aer simulator backend should you use**, and where does each
   one stop being practical as qubit count grows?

## Key findings

### Simulator scaling (qubit count vs. execution time)

| n  | `automatic` / `statevector` | `density_matrix` |
|----|------------------------------|-------------------|
| 4  | ~0.015s                     | ~0.015s           |
| 8  | ~0.02s                      | ~0.77s            |
| 10 | ~0.02s                      | **~126s**         |
| 14 | ~0.2s                       | not tested (too slow) |
| 16 | **~25-32s**                 | not tested         |
| 18 | **~71s**                    | not tested         |

- `statevector`/`automatic` stay near-instant up to ~14 qubits, then hit
  the expected exponential wall — visible starting at n=16 (25-32s) and
  worsening to ~71s at n=18, consistent with O(2^n) state vector scaling.
- `density_matrix` blows up far earlier and far worse: ~1000x slower than
  statevector by n=10 alone, consistent with its O(4^n) scaling (it
  tracks an n×n density matrix over a 2^n-dimensional space).
- `unitary`, `superop`, `extended_stabilizer`, and `matrix_product_state`
  either hang or fail outright on this circuit at n=4 — likely because
  the multi-controlled-X gates in the oracle/diffuser aren't Clifford
  operations and these methods aren't suited to measured circuits with
  this gate structure. Not yet root-caused in depth.

### Practical takeaway

For circuits like this (oracle-based search with multi-controlled gates),
`statevector` or `automatic` are the only Aer methods that scale
reasonably past toy sizes on consumer hardware. `density_matrix` becomes
impractical almost immediately once qubit count leaves single digits.

## How to run

```bash
uv sync
uv run python grovers.py
```

Outputs:
- Circuit diagram + measurement histogram for a single run
- `graphs/simulator_benchmark.png` — backend comparison at fixed n
- `graphs/scaling_benchmark.png` — execution time vs. qubit count

### Backend comparison (fixed n=4)

![Simulator benchmark at n=4](graphs/simulator_benchmark.png)

### Scaling: execution time vs qubit count

![Scaling benchmark](graphs/scaling_benchmark.png)

Note the flat region from n=12–14 (transpile/overhead-dominated, not real
scaling), then the sharp exponential climb from n=14 onward — this is
where 2^n statevector cost actually starts to bite.

## Known limitations / next steps

- `unitary`/`superop`/`extended_stabilizer`/`matrix_product_state` failure
  modes not yet diagnosed — worth investigating whether they work on
  unmeasured circuits (`grover_circuit(password, measure=False)`).
- Scaling data stops at n=18 (statevector) and n=10 (density_matrix) —
  extrapolation beyond that is inferred from trend, not measured.
- No noise model / real hardware run included yet (simulator-only so far).
