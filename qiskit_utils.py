# -*- coding: utf-8 -*-
"""
Created on Mon May  2 15:53:33 2022

@author:  GUy
"""
from typing import Union
from dataclasses import dataclass

import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Kraus, SuperOp
from qiskit.providers.aer import AerSimulator
from qiskit.tools.visualization import plot_histogram, plot_state_city
import qiskit.quantum_info as qi

# Import from Qiskit Aer noise module
from qiskit.providers.aer.noise import NoiseModel
from qiskit.providers.aer.noise import QuantumError, ReadoutError
from qiskit.providers.aer.noise import pauli_error
from qiskit.providers.aer.noise import depolarizing_error
from qiskit.providers.aer.noise import thermal_relaxation_error
import itertools as it


@dataclass
class Noise:
    T1: Union[float, list]
    T2: Union[float, list]

    def __init__(self, T1, T2, n_qubits = 1):
        if not isinstance(T1, list):
            T1 = (T1 * np.ones(n_qubits)).tolist()
        if not isinstance(T2, list):
            T2 = (T2 * np.ones(n_qubits)).tolist()

        for i in range(len(T1)):
            if T2[i] > 2 * T1[i]:
                T2[i] = 2 * T1[i]

        self.T1 = T1
        self.T2 = T2



def get_thermal_error_object(T1s, T2s, time_u1=0, time_u2=50, time_u3=100, time_cx=300, time_reset=1000,
                             time_measure=1000):
    # written by Guy, 2022_02_05
    # constructs a qiskit noise model object for thermal noise
    n_qubits = np.size(T1s)
    # QuantumError objects
    errors_reset = [thermal_relaxation_error(t1, t2, time_reset)
                    for t1, t2 in zip(T1s, T2s)]
    errors_measure = [thermal_relaxation_error(t1, t2, time_measure)
                      for t1, t2 in zip(T1s, T2s)]
    errors_u1 = [thermal_relaxation_error(t1, t2, time_u1)
                 for t1, t2 in zip(T1s, T2s)]
    errors_u2 = [thermal_relaxation_error(t1, t2, time_u2)
                 for t1, t2 in zip(T1s, T2s)]
    errors_u3 = [thermal_relaxation_error(t1, t2, time_u3)
                 for t1, t2 in zip(T1s, T2s)]
    errors_cx = [[thermal_relaxation_error(t1a, t2a, time_cx).expand(
        thermal_relaxation_error(t1b, t2b, time_cx))
        for t1a, t2a in zip(T1s, T2s)]
        for t1b, t2b in zip(T1s, T2s)]

    # Add errors to noise model
    noise_thermal = NoiseModel()
    for j in range(n_qubits):
        noise_thermal.add_quantum_error(errors_reset[j], "reset", [j])
        noise_thermal.add_quantum_error(errors_measure[j], "measure", [j])
        noise_thermal.add_quantum_error(errors_u1[j], "u1", [j])
        noise_thermal.add_quantum_error(errors_u2[j], "u2", [j])
        noise_thermal.add_quantum_error(errors_u3[j], "u3", [j])
        for k in range(n_qubits):
            noise_thermal.add_quantum_error(errors_cx[j][k], "cx", [j, k])

    return (noise_thermal)


def get_instruction_duration(gates, n_qubits, locality, duration, units='s'):
    # constructs a list (lst) of tuples in the format that Qiskit transpile function
    # wants:  [(instruction_name, qubits, duration, unit), …].
    # see https://qiskit.org/documentation/stubs/qiskit.compiler.transpile.html under "instruction_durations".
    #
    # args:
    # gates :  a set list of gates (strings) e.g. ['u1', 'u2', 'u3', 'cx']
    # n_qubits: an integer
    # locality: a list of integers of the same length as gates, storinmg the locality of each gate. the locality of a single qubit gate is 1 and the locality of a two-qubit gate is 2. for a gate with locality 2 the function will create a tuple for each possible combination of two qubits. (so doing only nearest neighbours etc. is not supported yet)
    # duration: a list, duration for each gate.

    qubits = range(n_qubits)
    lst = []
    for i, gate in enumerate(gates):
        qubit_combinations = list(it.permutations(qubits, locality[i]))
        for combination in qubit_combinations:
            tup = (gate, combination, duration[i], units)
            lst.append(tup)
    return (lst)


def thermal_noise_transpile(circuit, T1s, T2s,
                            basis_gates=['u1', 'u2', 'u3', 'cz', 'save_density_matrix'],
                            basis_gate_times=np.array([0, 25, 50, 26, 0]) * 1e-9,
                            basis_gates_locality=[1, 1, 1, 2, 'all'],
                            time_step=1e-9,
                            initial_layout=None):
    # returns a transpiled circuit with basis gates basis_gates, adn thermal noise (implemented with qiskit RelaxationNoisePass)
    # args:
    # circuit: # a circuit
    # T1s: a list of T1 times for each qubit
    # T2s - similar for T2
    # basis_gates :  a set list of gates (strings)
    # basis_gates_times : duration for eahc gate
    # basis_gates_locality:  a list of integers of the same length as gates, storinmg the locality of each gate. the locality of a single qubit gate is 1 and the locality of a two-qubit gate is 2. for a gate with locality 2 the function will create a noise model for each possible combination of two qubits. (so doing only nearest neighbours etc. is not supported yet)

    from qiskit.providers.aer.noise import RelaxationNoisePass

    for i, loca in enumerate(basis_gates_locality):
        if loca == 'all':
            basis_gates_locality[i] = circuit.num_qubits

    instruction_durations = get_instruction_duration(basis_gates, circuit.num_qubits, basis_gates_locality,
                                                     basis_gate_times)
    delay_pass = RelaxationNoisePass(T1s, T2s, dt=time_step)

    trans_circ = transpile(circuit, basis_gates=basis_gates,
                           scheduling_method='asap',
                           instruction_durations=instruction_durations,
                           initial_layout=initial_layout)
    return (delay_pass(trans_circ))


def get_transpiled(circ, backend, noise=None, basis_gates=['u1', 'u2', 'u3', 'cx', 'save_density_matrix'],
                   basis_gate_times=np.array([0, 50, 100, 300, 0]) * 1e-9,
                   basis_gates_locality=[1, 1, 1, 2, 'all'],
                   time_step=1e-10,
                   initial_layout=None):
    # take care of single cicuitt case
    if not type(circ) == list:
        circ = [circ]

    trans_circ = []
    if noise:
        for j in range(len(circ)):
            N = circ[j].num_qubits

            trans_circ.append(thermal_noise_transpile(circ[j].copy(), noise.T1, noise.T2, basis_gates=basis_gates,
                                                      basis_gate_times=basis_gate_times,
                                                      basis_gates_locality=basis_gates_locality,
                                                      time_step=time_step,
                                                      initial_layout=initial_layout))
    else:
        for j in range(len(circ)):
            trans_circ = transpile(circ[j].copy(), backend,initial_layout=initial_layout, scheduling_method='asap')

    if len(trans_circ) == 1:
        return trans_circ[0]
    else:
        return trans_circ


from qiskit.ignis.mitigation.measurement import complete_meas_cal, CompleteMeasFitter
import pickle


def run_calib(backend, n_qubits, shots=20000, initial_layout=None):
    meas_calib_circs, state_labels = complete_meas_cal(qr=qiskit.QuantumRegister(n_qubits))
    transpiled_meas_calib = qiskit.transpile(meas_calib_circs, backend,initial_layout=initial_layout)
    print(f"sending measurement calibration job for {n_qubits} qubits with {shots} shots")
    job = backend.run(transpiled_meas_calib, shots=shots)
    return job, state_labels


def get_calib_meas_fitter(calib_job, state_labels):
    cal_results = calib_job.result()
    print("got calibration results.")
    meas_fitter = CompleteMeasFitter(cal_results, state_labels)
    with open(f'G:\My Drive\guy PHD folder\Z2_LGT_simulation\qiskit_calib_data\calib_{calib_job.backend().name()}',
              'wb') as file:
        pickle.dump(meas_fitter, file)
    return meas_fitter

def max_qubit_number(circs:list):
    qubit_numbers = []
    for circ in circs:
        qubit_numbers.append(circ.num_qubits)
    return max(qubit_numbers)