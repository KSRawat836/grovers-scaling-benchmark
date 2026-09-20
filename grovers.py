from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer, AerSimulator
from qiskit.visualization import plot_histogram
import numpy as np
import matplotlib.pyplot as plt
import time
import os

os.makedirs("graphs", exist_ok=True)

bonks = 8192


# Circuit building blocks

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


def grover_circuit(password, measure=True):
    """Builds the full Grover's circuit: superposition + optimal oracle/diffuser iterations."""
    n = len(password)
    qc = QuantumCircuit(n, n) if measure else QuantumCircuit(n)

    initialize_superposition(qc, n)

    iterations = int(np.floor((np.pi / 4) * np.sqrt(2 ** n)))
    for _ in range(iterations):
        grover_oracle(qc, password)
        grover_diffuser(qc, n)

    if measure:
        qc.measure(range(n), range(n))
    return qc, iterations


def run_grover(password):
    """Builds, runs and visualizes a single Grover's search for `password` on the qasm simulator."""
    qc, iterations = grover_circuit(password)
    backend = Aer.get_backend("qasm_simulator")

    compiled = transpile(qc, backend)
    result = backend.run(compiled, shots=bonks).result()
    counts = result.get_counts()

    print(f"\nGrover iterations used: {iterations}")
    print("\nMeasurement Results:")
    print(counts)
    print(f"Expected (reversed): {password[::-1]}")

    fig = qc.draw(output='mpl', scale=1 / 4)
    fig.set_size_inches(50, 30)
    plt.show()

    plot_histogram(counts)
    plt.show()



# OUTPUT 1: probability amplification across multiple shot
# counts, all overlaid on a single graph


def probability_amplification_multi_shots(password, shots_list, runs=3, backend_name="qasm_simulator"):
    """Plots success probability vs iteration count, overlaid across different shot counts, to find the optimal iteration/shot tradeoff."""
    n = len(password)
    backend = Aer.get_backend(backend_name)

    iters = int(np.floor((np.pi / 4) * np.sqrt(2 ** n)))
    iterations_range = range(1, max(iters, 2))

    plt.figure(figsize=(9, 6))

    for shots in shots_list:
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

        optimal_iter = list(iterations_range)[int(np.argmax(probs))]
        optimal_prob = max(probs)
        print(f"[shots={shots}] optimal iterations: {optimal_iter} (P={optimal_prob:.3f})")

        plt.plot(list(iterations_range), probs, marker='o', label=f"shots={shots}")

    plt.xlabel("Grover Iterations")
    plt.ylabel("Probability of Correct Password")
    plt.title(f"Probability Amplification vs Shot Count (password={password})")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig("graphs/probability_amplification_multi_shots.png", dpi=150)
    plt.show()



# OUTPUT 2: benchmark all Aer simulator methods

def benchmark_simulators(password, shots=8192):
    """Runs the same Grover's circuit across all AerSimulator methods and compares execution time/success."""
    n = len(password)
    qc, iterations = grover_circuit(password, measure=True)

    # AerSimulator supports multiple internal "methods" (statevector,
    # density_matrix, matrix_product_state, extended_stabilizer, unitary,
    # superop, automatic). Not all methods support every circuit (e.g.
    # unitary/superop can't handle measurement instructions), so failures
    # are caught and reported rather than crashing the whole benchmark.
    methods = [
            "automatic",
            "statevector",
            "density_matrix",
    ]

    results = []

    for method in methods:
        try:
            backend = AerSimulator(method=method)
            compiled = transpile(qc, backend)

            start = time.perf_counter()
            job = backend.run(compiled, shots=shots)
            res = job.result()
            elapsed = time.perf_counter() - start

            success = res.success
            counts = res.get_counts() if success else {}
            top_state = max(counts, key=counts.get) if counts else None

            results.append({
                "method": method,
                "time_s": elapsed,
                "success": success,
                "top_state": top_state,
                "error": None,
            })
        except Exception as e:
            results.append({
                "method": method,
                "time_s": None,
                "success": False,
                "top_state": None,
                "error": str(e).splitlines()[0][:80],
            })

    # ---- print table ----
    print(f"\nBenchmark: {n}-qubit Grover circuit ({iterations} iterations), shots={shots}\n")
    print(f"{'Method':<22}{'Time (s)':<12}{'Success':<10}{'Top State':<12}Notes")
    print("-" * 80)
    for r in results:
        time_str = f"{r['time_s']:.4f}" if r['time_s'] is not None else "N/A"
        note = r["error"] if r["error"] else ""
        print(f"{r['method']:<22}{time_str:<12}{str(r['success']):<10}{str(r['top_state']):<12}{note}")

    # ---- plot bar chart of successful runs ----
    successful = [r for r in results if r["success"] and r["time_s"] is not None]
    if successful:
        plt.figure(figsize=(8, 5))
        plt.bar([r["method"] for r in successful], [r["time_s"] for r in successful])
        plt.ylabel("Execution Time (s)")
        plt.xlabel("Aer Simulator Method")
        plt.title(f"Aer Simulator Benchmark ({n}-qubit Grover, shots={shots})")
        plt.xticks(rotation=30, ha="right")
        plt.grid(axis="y")
        plt.tight_layout()
        plt.savefig("graphs/simulator_benchmark.png", dpi=150)
        plt.show()

    return results


def benchmark_scaling(passwords_by_n, methods, shots=8192):
    """Sweeps Grover's circuit across increasing qubit counts, timing each simulator method to reveal scaling behavior."""
    results = []
 
    for password in passwords_by_n:
        n = len(password)
        qc, iterations = grover_circuit(password, measure=True)
 
        for method in methods:
            try:
                backend = AerSimulator(method=method)
                compiled = transpile(qc, backend)
 
                start = time.perf_counter()
                job = backend.run(compiled, shots=shots)
                res = job.result()
                elapsed = time.perf_counter() - start
 
                success = res.success
                results.append({
                    "n": n,
                    "method": method,
                    "time_s": elapsed,
                    "success": success,
                    "error": None,
                })
            except Exception as e:
                results.append({
                    "n": n,
                    "method": method,
                    "time_s": None,
                    "success": False,
                    "error": str(e).splitlines()[0][:80],
                })
 
    # ---- print table ----
    print(f"\nScaling Benchmark (shots={shots})\n")
    print(f"{'n':<5}{'Method':<20}{'Time (s)':<12}{'Success':<10}Notes")
    print("-" * 80)
    for r in results:
        time_str = f"{r['time_s']:.4f}" if r['time_s'] is not None else "N/A"
        note = r["error"] if r["error"] else ""
        print(f"{r['n']:<5}{r['method']:<20}{time_str:<12}{str(r['success']):<10}{note}")
 
    # ---- plot: time vs n, one line per method ----
    plt.figure(figsize=(9, 6))
    for method in methods:
        xs = [r["n"] for r in results if r["method"] == method and r["success"]]
        ys = [r["time_s"] for r in results if r["method"] == method and r["success"]]
        if xs:
            plt.plot(xs, ys, marker='o', label=method)
 
    plt.xlabel("Number of Qubits (n)")
    plt.ylabel("Execution Time (s)")
    plt.title(f"Simulator Scaling: Time vs Qubit Count (shots={shots})")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig("graphs/scaling_benchmark.png", dpi=150)
    plt.show()
 
    return results


# main

if __name__ == "__main__":
    PASSWORD = "0001"  # 4-15 bits

    print("Target password:", PASSWORD)
    run_grover(PASSWORD)


    # Output 1: benchmark all Aer simulator methods
    benchmark_simulators(PASSWORD, shots=8192)

    #Output 2: benchmark simulator's breaking point
    passwords_by_n = [
        # "0010",                          # n=4
        # "000010",                        # n=6
        # "00000010",                      # n=8
        # "1100111001",                    # n=10
        # "001011101010",                  # n=12
        # "11000010001111",                # n=14
        # "0110100001110100",              # n=16
        # "011100101110100111",            # n=18
        # "10010000010111100110",          # n=20
        # "1101010010010011001100",        # n=22
        # "000100010110011111000010",      # n=24
    ]
    methods = [
            "automatic",
            "statevector",
            # "density_matrix",  """ Add density matrix only for smaller n values, for larger n values the time complexity sky rockets """
    ]
    benchmark_scaling(passwords_by_n,methods,shots=8192)