from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
import numpy as np
import matplotlib.pyplot as plt
import os

os.makedirs("graphs", exist_ok=True)


def initialize_superposition(qc, n):
    for i in range(n):
        qc.h(i)


def grover_oracle(qc, password):
    """Phase-flips the state matching `password` using a multi-controlled Z (via H-MCX-H sandwich)."""
    n = len(password)
    for i, bit in enumerate(password):
        if bit == '0':
            qc.x(i)

    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)

    for i, bit in enumerate(password):
        if bit == '0':
            qc.x(i)


def grover_diffuser(qc, n):
    """Amplitude amplification: inverts amplitudes about their mean, boosting the marked state's probability."""
    qc.h(range(n))
    qc.x(range(n))

    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)

    qc.x(range(n))
    qc.h(range(n))


def sin_squared_validation(password, shots_list, max_iterations=25, runs=3, backend_name="qasm_simulator"):
    """
    Overshoots well past the optimal iteration count to reveal Grover's
    theoretical sin^2 probability curve, including the over-rotation
    drop-off past the peak. Uses one subplot per shot count so curves
    don't overlap, with the theoretical curve overlaid on each.
    """
    n = len(password)
    backend = Aer.get_backend(backend_name)
    iterations_range = range(1, max_iterations + 1)

    # theoretical curve (same for all subplots)
    theta = np.arcsin(1 / np.sqrt(2 ** n))
    theory_x = np.linspace(1, max_iterations, 200)
    theory_y = np.sin((2 * theory_x + 1) * theta) ** 2

    n_shots = len(shots_list)
    cols = 2
    rows = int(np.ceil(n_shots / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows), sharex=True, sharey=True)
    axes = np.array(axes).flatten()

    for idx, shots in enumerate(shots_list):
        probs = []
        for i in iterations_range:
            qc = QuantumCircuit(n)
            initialize_superposition(qc, n)

            for _ in range(i):
                grover_oracle(qc, password)
                grover_diffuser(qc, n)

            qc.measure_all()
            compiled = transpile(qc, backend, optimization_level=1)

            prob = 0
            for _ in range(runs):
                counts = backend.run(compiled, shots=shots).result().get_counts()
                prob += counts.get(password[::-1], 0) / shots
            prob /= runs
            probs.append(prob)

        ax = axes[idx]
        ax.plot(list(iterations_range), probs, marker='o', color='tab:blue', label="simulated")
        ax.plot(theory_x, theory_y, 'k--', linewidth=1.5, label="theoretical sin²")
        ax.set_title(f"shots={shots}")
        ax.grid()
        ax.legend(fontsize=8)

    # hide any unused subplot slots
    for j in range(n_shots, len(axes)):
        axes[j].axis('off')

    fig.supxlabel("Grover Iterations")
    fig.supylabel("Probability of Correct Password")
    fig.suptitle(f"Sin² Curve Validation — Overshoot Past Optimal (password={password})")
    plt.tight_layout()
    plt.savefig("graphs/sin_squared_validation.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    PASSWORD = "0001010101"  
    shots_list = [256,2048, 8192,16384]

    sin_squared_validation(PASSWORD, shots_list, max_iterations=70)