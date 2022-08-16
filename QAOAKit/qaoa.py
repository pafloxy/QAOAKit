# QAOA circuits

from lib2to3.pgen2.token import OP
from turtle import penup
import networkx as nx
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, Aer, execute
from qiskit.compiler import transpile
from qiskit.quantum_info import Operator, Pauli, PauliList
import numpy as np
from itertools import count as itcount
import math
from typing import Union, Optional


def misra_gries_edge_coloring(G):
    nx.set_edge_attributes(G, values=None, name="misra_gries_color")
    uncolored_edges = list(G.edges())
    while uncolored_edges:
        u, v = uncolored_edges[0]
        F = [v] # F is the maximal fan of u
        for n in G.neighbors(u):
            if (n!=v and
                G[n][u]["misra_gries_color"] != None and
                G[n][u]["misra_gries_color"] not in
                [G[F[-1]][i]["misra_gries_color"] for i in G.neighbors(F[-1])]):
                F.append(n)
        c = next((x) for x in itcount() # c is free on u
            if (x) not in set([G[u][i]["misra_gries_color"] for i in G.neighbors(u)]))
        d = next((x) for x in itcount() # d is free on F[k]
            if (x) not in set([G[F[-1]][i]["misra_gries_color"] for i in G.neighbors(F[-1])]))
        n = u # current node for the path construction
        color = d # current color
        visited_edges = [] # mark visited edges to stop double flipping
        while True: # invert cd path
            edge_found = 0
            for i, j in G.edges(n):
                if (G[i][j] not in visited_edges and 
                    G[i][j]["misra_gries_color"] == color):
                    if color == c:
                        G[i][j]["misra_gries_color"]=d
                        color = d
                    elif color == d:
                        G[i][j]["misra_gries_color"]=c
                        color = c
                    n = j
                    visited_edges.append(G[i][j])
                    edge_found = 1
                    break
            if edge_found == 0:
                break
        for i in range(len(F)): # find w satisfying w in F, [F[1]..w] a fan, d free on w
            w = F[i]
            if d not in set([G[w][j]["misra_gries_color"] for j in G.neighbors(w)]):
                Fw = F[0:i+1]
                for j in range(len(F)-1): #rotate the fan Fw
                    G[F[j]][u]["misra_gries_color"] = G[F[j+1]][u]["misra_gries_color"]
                G[F[-1]][u]["misra_gries_color"] = d
                break # break after the first w is found and the fan is rotated
        uncolored_edges.pop(0) # remove the colored edge
    return G


def append_zz_term(qc, q1, q2, gamma):
    qc.cx(q1, q2)
    qc.rz(2 * gamma, q2)
    qc.cx(q1, q2)


def append_x_term(qc, q1, beta):
    qc.h(q1)
    qc.rz(2 * beta, q1)
    qc.h(q1)


def append_zzzz_term(qc, q1, q2, q3, q4, angle):
    qc.cx(q1,q2)
    qc.cx(q2,q3)
    qc.cx(q3,q4)
    qc.rz(2 * angle, q4)
    qc.cx(q3,q4)
    qc.cx(q2,q3)
    qc.cx(q1,q2)


def append_4_qubit_pauli_rotation_term(qc, q1, q2, q3, q4, beta, pauli="zzzz"):
    print("inside-> append_4_qubit_pauli")
    allowed_symbols = set("xyz")
    if set(pauli).issubset(allowed_symbols) and len(pauli) == 4:
        if pauli[0] == "x":
            qc.h(q1)
        elif pauli[0] == "y":
            qc.rx(-np.pi*.5,q1)
        if pauli[1] == "x":
            qc.h(q2)
        elif pauli[1] == "y":
            qc.rx(-np.pi*.5,q2)
        if pauli[2] == "x":
            qc.h(q3)
        elif pauli[2] == "y":
            qc.rx(-np.pi*.5,q3)
        if pauli[3] == "x":
            qc.h(q4)
        elif pauli[3] == "y":
            qc.rx(-np.pi*.5,q4)
        append_zzzz_term(qc, q1, q2, q3, q4, beta)
        if pauli[0] == "x":
            qc.h(q1)
        elif pauli[0] == "y":
            qc.rx(-np.pi*.5,q1)
        if pauli[1] == "x":
            qc.h(q2)
        elif pauli[1] == "y":
            qc.rx(-np.pi*.5,q2)
        if pauli[2] == "x":
            qc.h(q3)
        elif pauli[2] == "y":
            qc.rx(-np.pi*.5,q3)
        if pauli[3] == "x":
            qc.h(q4)
        elif pauli[3] == "y":
            qc.rx(-np.pi*.5,q4)
    else:
        raise ValueError("Not a valid Pauli gate or wrong locality")


def append_n_qubit_z_term(qc, ql, angle):
    for i in range(len(ql)-1):
        qc.cx(ql[i],ql[i+1])
    qc.rz(2 * angle, ql[-1])
    for i in range(len(ql)-1):
        qc.cx(ql[len(ql)-2+i],ql[len(ql)-1+i])


def append_n_qubit_pauli_rotation_term(qc, ql, beta, pauli):
    allowed_symbols = set("xyz")
    if set(pauli).issubset(allowed_symbols) and len(pauli) == len(ql):
        for i in range(len(ql)-1):
            if pauli[0] == "x":
                qc.h(ql[i])
            elif pauli[0] == "y":
                qc.rx(-np.pi*.5, ql[i])
        qc.rz(2 * beta, ql[-1])
        for i in range(len(ql)-1):
            if pauli[0] == "x":
                qc.h(ql[i])
            elif pauli[0] == "y":
                qc.rx(-np.pi*.5, ql[i])
    else:
        raise ValueError("Not a valid Pauli gate or wrong locality")


def get_mixer_operator_circuit(G, beta):
    N = G.number_of_nodes()
    qc = QuantumCircuit(N)
    for n in G.nodes():
        append_x_term(qc, n, beta)
    return qc


def get_maxcut_cost_operator_circuit(G, gamma):
    N = G.number_of_nodes()
    qc = QuantumCircuit(N)
    for i, j in G.edges():
        if nx.is_weighted(G):
            append_zz_term(qc, i, j, gamma * G[i][j]["weight"])
        else:
            append_zz_term(qc, i, j, gamma)
    return qc


def get_tsp_cost_operator_circuit(G, gamma, pen=0, encoding="onehot"):
    """
    Generates a circuit for the TSP phase unitary with optional penalty.

    Parameters
    ----------
    G : networkx.Graph
        Graph to solve TSP on
    gamma :
        QAOA parameter gamma
    pen :
        Penalty for edges with no roads
    encoding : string, default "onehot"
        Type of encoding for the city ordering

    Returns
    -------
    qc : qiskit.QuantumCircuit
        Quantum circuit implementing the TSP phase unitary
    
    """
    
    print("inside-> tsp_cost_operator_circuit") ##checkflag
    if encoding == "onehot":
        N = G.number_of_nodes()
        if not nx.is_weighted(G):
            raise ValueError("Provided graph is not weighted")
        qc = QuantumCircuit(N**2)
        for n in range(N): # cycle over all cities in the input ordering
            for u in range(N):
                for v in range(N): #road from city v to city u

                    q1 = (n*N + u) % (N**2)
                    q2 = ((n+1)*N + v) % (N**2)
                    if G.has_edge(u, v):
                        append_zz_term(qc, q1, q2, gamma * G[u][v]["weight"])

                    q1 = (n*N + u - 1) % (N**2)
                    q2 = ((n+1)*N + v - 1) % (N**2)
                    if G.has_edge(u, v):                                               ## modified the phase hamiltonian @pafloxy
                        # append_zz_term(qc, q1, q2, gamma * G[u][v]["weight"]) 
                        qc.cp( gamma * G[u][v]["weight"], q1, q2)

                    else:
                        # append_zz_term(qc, q1, q2, gamma * pen)
                        qc.cp( gamma * pen, q1, q2)
                        pass
        return qc



def is_valid_path( path:str, graph: Optional[Union[nx.Graph, None]]= None)-> bool:
    
    ## check if the path is valid wrt. to feasibility ~
    n = int(np.sqrt(len(path)))
    if path.count('1') != int(np.sqrt(len(path)) ): return False
    rep_matrix= np.zeros((n,n), dtype= int)
    for index, val in enumerate(path) :
        if val== '1':
            u = index % n
            i = math.floor(index/n)
            rep_matrix[ i, u] = 1
    for index in n :
        if np.count_nonzero(rep_matrix[index] ) <= 1 : return False
    
    ## check if path is valid wrt. to graph ~
    if isinstance(graph, nx.Graph):
        for i in range(n) :
            city_i = np.where( rep_matrix[i%n] == 1)[0]
            city_j = np.where( rep_matrix[(i+1)%n] == 1)[0]
            if (city_i, city_j) not in graph.edges: return False

    return True



def get_tsp_cost( path:str, graph:nx.Graph )-> float: ##pafloxy

    if is_valid_path(path, graph):
        n = int(np.sqrt(len(path)))
        rep_matrix= np.zeros((n,n), dtype= int)
        for index, val in enumerate(path) :
            if val== '1':
                u = index % n
                i = math.floor(index/n)
                rep_matrix[ i, u] = 1
       
        cost= 0
        for i in range(n) :
            city_i = np.where( rep_matrix[i%n] == 1)[0]
            city_j = np.where( rep_matrix[(i+1)%n] == 1)[0]
            cost += graph.get_edge_data(city_i, city_j)['weight']

        return cost

    else : raise ValueError("solution string is not a valid path")



def get_tsp_hamiltonian_single( cost_q1_q2, q1, q2, N): ## @pafloxy
    print("inside-> get_tsp_single, qubits:", [q1,q2]) ##checkflag

    ## define single qubit operator ~
    op = Operator( 0.5*( Pauli('Z').to_matrix() + Pauli('I').to_matrix()))

    ## initiate multi-qubit operator ~
    string = ''
    for i in range(q1): string+= 'I'
    hamil = Operator(Pauli(string).to_matrix())

    hamil = hamil.tensor(op)
    for i in range(q1+1 , q2 ) :
        hamil = hamil.tensor( Operator(Pauli('I').to_matrix()) )
    hamil = hamil.tensor(op)
    for i in range(q2+1 , N ) :
        hamil = hamil.tensor( Operator(Pauli('I').to_matrix()) )

    hamil = Operator(cost_q1_q2 * hamil)

    return hamil



def get_tsp_cost_operator_hamiltonian(G, pen=0, encoding= "onehot"):  ## @pafloxy
    """
    Generates the Hamiltonian operator encoding the TSP cost function

    Parameters
    ----------
    G : networkx.Graph
        Graph to solve TSP on
    pen :
        Penalty for edges with no roads
    encoding : string, default "onehot"
        Type of encoding for the city ordering

    Returns
    -------
    qc : qiskit.QuantumCircuit
        Quantum circuit implementing the TSP phase unitary
    """
    print("inside-> tsp_cost_operator_hamiltonian") ##checkflag
    if encoding == "onehot":
        N = G.number_of_nodes()
        num_qubits= N**2
        if not nx.is_weighted(G):
            raise ValueError("Provided graph is not weighted")
        
        ## initiate hamiltonian ~
        hamiltonian = Operator(np.zeros((2,2)))
        for q in range(num_qubits-1):
            hamiltonian = Operator(np.zeros((2,2))).tensor(hamiltonian)

        ## add weight terms to the hamiltonian
        for n in range(N): # cycle over all cities in the input ordering
            for u in range(N):
                for v in range(N): #road from city v to city u
                    
                    print('hamiltonian :', hamiltonian)

                    q1 = (n*N + u - 1) % (N**2)
                    q2 = ((n+1)*N + v - 1) % (N**2)
                    if G.has_edge(u, v):                                              
                        hamiltonian+= get_tsp_hamiltonian_single( G[u][v]["weight"], q1, q2, num_qubits )
                    elif pen!= 0:
                        hamiltonian+= get_tsp_hamiltonian_single( pen, q1, q2, num_qubits )
                        pass

        return hamiltonian

    

def get_ordering_swap_partial_mixing_circuit(G, i, j, u, v, beta, T, encoding="onehot"):
    """
    Generates an ordering swap partial mixer for the TSP mixing unitary.

    Parameters
    ----------
    G : networkx.Graph
        Graph to solve TSP on
    i, j :
        Positions in the ordering to be swapped
    u, v :
        Cities to be swapped
    beta :
        QAOA angle
    T :
        Number of Trotter steps
    encoding : string, default "onehot"
        Type of encoding for the city ordering

    Returns
    -------
    qc : qiskit.QuantumCircuit
        Quantum circuit implementing the TSP phase unitary
    """
    if encoding == "onehot":
        N = G.number_of_nodes()
        dt = beta/T
        qc = QuantumCircuit(N**2)
        qui = (N*i + u) % (N**2)
        qvj = (N*j + v) % (N**2)
        quj = (N*j + u) % (N**2)
        qvi = (N*i + v) % (N**2)
        for i in range(T):
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, 2*dt, "xxxx")
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, -2*dt, "xxyy")
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, 2*dt, "xyxy")
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, 2*dt, "xyyx")
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, 2*dt, "yxxy")
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, 2*dt, "yxyx")
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, -2*dt, "yyxx")
            append_4_qubit_pauli_rotation_term(qc, qui, qvj, quj, qvi, 2*dt, "yyyy")
        return qc


def get_color_parity_ordering_swap_mixer_circuit(G, beta, T, encoding="onehot"):
    print("inside-> tsp_color_parity_mixer_circuit") ##checkflag
    if encoding == "onehot":
        N = G.number_of_nodes()
        qc = QuantumCircuit(N**2)
        G = misra_gries_edge_coloring(G)
        colors = nx.get_edge_attributes(G, "misra_gries_color")
        for c in colors.values():

            # print("implemnting-> ")
            for i in range(0,N-1,2):
                for u, v in G.edges:
                    if G[u][v]["misra_gries_color"] == c:
                        qc = qc.compose(get_ordering_swap_partial_mixing_circuit(
                            G, i, i+1, u, v, beta, T, encoding="onehot"))
                            
            for i in range(1,N-1,2):
                for u, v in G.edges:
                    if G[u][v]["misra_gries_color"] == c:
                        qc = qc.compose(get_ordering_swap_partial_mixing_circuit(
                            G, i, i+1, u, v, beta, T, encoding="onehot"))
            if N%2 == 1:
                for u, v in G.edges:
                    if G[u][v]["misra_gries_color"] == c:
                        qc = qc.compose(get_ordering_swap_partial_mixing_circuit(
                            G, N-1, 0, u, v, beta, T, encoding="onehot"))
        return qc


def get_tsp_init_circuit(G, encoding="onehot"):  ## mgiht be a bug here 
    if encoding == "onehot":
        N = G.number_of_nodes()
        qc = QuantumCircuit(N**2)
        for i in range(N):
            qc.x(i*N+i)
        return qc


def get_tsp_qaoa_circuit(
    G, beta, gamma, T=1, pen=2, transpile_to_basis=True,insert_barriers= True, save_state=True, encoding="onehot"
):
    if encoding == "onehot":
        assert len(beta) == len(gamma)
        p = len(beta)  # infering number of QAOA steps from the parameters passed
        N = G.number_of_nodes()
        qr = QuantumRegister(N**2)
        qc = QuantumCircuit(qr)
        # prepare the init state in onehot encoding
        qc = qc.compose(get_tsp_init_circuit(G, encoding="onehot"))
        # second, apply p alternating operators
        for i in range(p):
            qc = qc.compose(get_tsp_cost_operator_circuit(G, gamma[i], pen, encoding="onehot"))
            if insert_barriers: qc.barrier() 
            qc = qc.compose(get_color_parity_ordering_swap_mixer_circuit(G, beta[i], T, encoding="onehot"))
        if transpile_to_basis:
            qc = transpile(qc, optimization_level=0, basis_gates=["u1", "u2", "u3", "cx"])
        if save_state:
            qc.save_state()
        return qc


# def 


def get_maxcut_qaoa_circuit(
    G, beta, gamma, transpile_to_basis=True, save_state=True, qr=None, cr=None
):
    """
    Generates a circuit for weighted MaxCut on graph G.

    Parameters
    ----------
    G : networkx.Graph
        Graph to solve MaxCut on
    beta : list-like
        QAOA parameter beta
    gamma : list-like
        QAOA parameter gamma
    transpile_to_basis : bool, default True
        Transpile the circuit to ["u1", "u2", "u3", "cx"]
    save_state : bool, default True
        Add save state instruction to the end of the circuit
    qr : qiskit.QuantumRegister, default None
        Registers to use for the circuit.
        Useful when one has to compose circuits in a complicated way
        By default, G.number_of_nodes() registers are used
    cr : qiskit.ClassicalRegister, default None
        Classical registers, useful if measuring
        By default, no classical registers are added

    Returns
    -------
    qc : qiskit.QuantumCircuit
        Quantum circuit implementing QAOA
    """
    assert len(beta) == len(gamma)
    p = len(beta)  # infering number of QAOA steps from the parameters passed
    N = G.number_of_nodes()
    if qr is not None:
        assert isinstance(qr, QuantumRegister)
        assert qr.size >= N
    else:
        qr = QuantumRegister(N)

    if cr is not None:
        assert isinstance(cr, ClassicalRegister)
        qc = QuantumCircuit(qr, cr)
    else:
        qc = QuantumCircuit(qr)

    # first, apply a layer of Hadamards
    qc.h(range(N))
    # second, apply p alternating operators
    for i in range(p):
        qc = qc.compose(get_maxcut_cost_operator_circuit(G, gamma[i]))
        qc = qc.compose(get_mixer_operator_circuit(G, beta[i]))
    if transpile_to_basis:
        qc = transpile(qc, optimization_level=0, basis_gates=["u1", "u2", "u3", "cx"])
    if save_state:
        qc.save_state()
    return qc
