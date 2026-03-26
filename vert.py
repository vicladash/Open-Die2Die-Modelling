import numpy as np
import matplotlib.pyplot as plt
import os
import skrf as rf

# -------------------------------
# Lumped Element Functions (LC)
# -------------------------------

def C_pkg1_f(epsilon, h, r, s):
    """
    Compute package capacitance C_pkg1 using:

        C = (2 * pi * epsilon * h) / ln((r + s) / r)

    Parameters
    ----------
    epsilon : float
        Absolute permittivity (F/m), i.e., epsilon_r * epsilon_0.
    h : float
        Height / separation (m).
    r : float
        Radius (m).
    s : float
        Spacing offset (m).

    Returns
    -------
    float or ndarray
        C_pkg1 in Farads. Works with scalar or array inputs.
    """
    return (2 * np.pi * epsilon * h) / np.log((r + s) / r)

def C_pkg2_f(epsilon, r, h):
    """
    Compute C_pkg2 using the formula:

        C = ((pi * epsilon * r^2) / h) *
            (1 + (2*h)/(pi*r) * (ln((pi*r)/(2*h)) + 1.7726))

    Parameters
    ----------
    epsilon : float
        Absolute permittivity (F/m).
    r : float
        Radius (m).
    h : float
        Height / separation (m).

    Returns
    -------
    float or ndarray
        C_pkg2 in Farads. Works with scalar or array inputs.
    """
    term1 = (np.pi * epsilon * r**2) / h
    term2 = 1 + (2*h) / (np.pi * r) * (np.log((np.pi * r) / (2*h)) + 1.7726)
    return term1 * term2

def C_c(epsilon, r, s, h):
    """
    Coupling capacitance C_c using:

        k = (2*r + s) / (2*r)
        C_c = (pi * epsilon * h) /
              ln( k + sqrt(k^2 - 1) )

    Parameters
    ----------
    epsilon : float
        Absolute permittivity (F/m).
    r : float
        Radius (m).
    s : float
        Spacing offset (m).
    h : float
        Height (m).

    Returns
    -------
    float or ndarray
        Coupling capacitance C_c in farads.
    """
    k = (2*r + s) / (2*r)
    return (np.pi * epsilon * h) / np.log(k + np.sqrt(k**2 - 1))

def L_m(mu, h, s):
    """
    Mutual inductance L_m using:

        L_m = (mu * h / (2*pi)) * [
                  ln( h/s + sqrt( (h/s)**2 + 1 ) )
                - sqrt( (s/h)**2 + 1 )
                + s/h
              ]

    Parameters
    ----------
    mu : float
        Absolute permeability (H/m), e.g. mu0 * mu_r.
    h : float
        Vertical separation (m).
    s : float
        Lateral spacing (m).

    Returns
    -------
    float or ndarray
        L_m in Henries.
    """
    h_over_s = h / s
    s_over_h = s / h

    term1 = np.log(h_over_s + np.sqrt(h_over_s**2 + 1.0))
    term2 = np.sqrt(s_over_h**2 + 1.0)
    term3 = s_over_h  # + s/h

    return (mu * h / (2.0 * np.pi)) * (term1 - term2 + term3)

def L_s(mu, h, r):
    """
    Self-inductance L_s using:

        L_s = (mu * h / (2*pi)) * [
                  ln( h/r + sqrt( (h/r)**2 + 1 ) )
                - sqrt( (r/h)**2 + 1 )
                + r/h
                + 1/4
              ]

    Parameters
    ----------
    mu : float
        Absolute permeability (H/m).
    h : float
        Vertical height (m).
    r : float
        Radius (m).

    Returns
    -------
    float or ndarray
        L_s in Henries.
    """
    h_over_r = h / r
    r_over_h = r / h

    term1 = np.log(h_over_r + np.sqrt(h_over_r**2 + 1.0))
    term2 = np.sqrt(r_over_h**2 + 1.0)
    term3 = r_over_h
    term4 = 0.25  # 1/4

    return (mu * h / (2.0 * np.pi)) * (term1 - term2 + term3 + term4)

# -------------------------------
# Helper ABCD functions
# -------------------------------

def abcd_series(Z):
    return np.array([[1, Z],
                     [0, 1]], dtype=complex)

def abcd_shunt(Y):
    return np.array([[1, 0],
                     [Y, 1]], dtype=complex)

# -------------------------------------------------
# Build ABCD for C1 – L1 – C2 – L2 – C3 ladder
# -------------------------------------------------

def network_abcd(freq, C_bump, C_via, C_pkg1, C_pkg2, L_bump, L_via, layer):
    freq = np.atleast_1d(freq)
    omega = 2 * np.pi * freq
    N = len(freq)

    ABCD = np.zeros((N, 2, 2), dtype=complex)

    # Element values
    C1 = C_bump / 2
    L1 = L_bump
    
    C2 = ((C_bump + C_via) / 2) + C_pkg1
    L2 = L_via
    
    #Repeated Section Elements
    Cn = C_via / 2
    Ln = L_via
    
    C3 = (C_via / 2) + C_pkg2
    
    # Calculate how many times to repeat the Mn1 @ Mn2 block
    # Logic: layer=2 -> 0 repeats, layer=3 -> 1 repeat, etc.
    num_repeats = max(0, layer - 2)

    for i, w in enumerate(omega):

        Y_C1 = 1j * w * C1
        Z_L1 = 1j * w * L1
        
        Y_C2 = 1j * w * C2
        Z_L2 = 1j * w * L2
        
        Y_Cn = 1j * w * Cn
        Z_Ln = 1J * w * Ln
        
        Y_C3 = 1j * w * C3

        # Create Matrices
        M1 = abcd_shunt(Y_C1)
        M2 = abcd_series(Z_L1)
        M3 = abcd_shunt(Y_C2)
        M4 = abcd_series(Z_L2)
        
        # The repeating block matrices
        Mn1= abcd_shunt(Y_Cn)
        Mn2 = abcd_series(Z_Ln)

        # The final termination matrix
        M5 = abcd_shunt(Y_C3)

        # 1. Start the cascade with the fixed initial section
        cascade = M1 @ M2 @ M3 @ M4

        # 2. Add the repeated via segments (Mn1 @ Mn2)
        # We pre-calculate the block to avoid redundant multiply in the loop
        M_repeat = Mn1 @ Mn2

        for _ in range(num_repeats):
            cascade = cascade @ M_repeat

        # 3. Add the final termination (M5)
        ABCD[i] = cascade @ M5

    return ABCD

# -------------------------------------------------
# ABCD → S conversion
# -------------------------------------------------

def abcd_to_s(ABCD, Z0=50):
    ABCD = np.asarray(ABCD)
    N = ABCD.shape[0]

    S = np.zeros((N, 2, 2), dtype=complex)
    delta = np.zeros(N, dtype=complex)

    for i in range(N):
        A = ABCD[i,0,0]
        B = ABCD[i,0,1]
        C = ABCD[i,1,0]
        D = ABCD[i,1,1]

        Δ = A + B/Z0 + C*Z0 + D
        delta[i] = Δ

        S11 = (A + B/Z0 - C*Z0 - D) / Δ
        S21 = 2 / Δ
        S12 = 2 * (A*D - B*C) / Δ
        S22 = (-A + B/Z0 - C*Z0 + D) / Δ

        S[i,0,0] = S11
        S[i,0,1] = S12
        S[i,1,0] = S21
        S[i,1,1] = S22

    return S, delta

# -------------------------------------------------
# DEBUGGING - Verification Function to View Overall Vertical Matrix
# -------------------------------------------------

def verify_vertical_matrix(ntwk, freq_hz=1e9):
    """
    Prints a highly readable sparsity map of the block-diagonal vertical matrix.
    Color-codes the 4 unique elements of the 2x2 sub-matrices to verify correct 
    placement and orientation (S11, S12, S21, S22).
    """
    # Find the closest frequency index
    idx = np.argmin(np.abs(ntwk.f - freq_hz))
    actual_freq = ntwk.f[idx]
    s = ntwk.s[idx]
    n_ports = ntwk.number_of_ports
    num_traces = n_ports // 2

    # ANSI Colors for the 4 unique sub-matrix positions
    C11 = '\033[94m'  # Blue for Top-Left (S11)
    C12 = '\033[93m'  # Yellow for Top-Right (S12)
    C21 = '\033[95m'  # Magenta for Bottom-Left (S21)
    C22 = '\033[96m'  # Cyan for Bottom-Right (S22)
    
    GREY = '\033[90m'   # Perfect zero (Isolation)
    RED = '\033[91m'    # Error (Leaky cross-talk)
    RESET = '\033[0m'

    print(f"\n=== Vertical Matrix Verification @ {actual_freq/1e9:.3f} GHz ===")
    print(f"Network: {ntwk.name} ({num_traces} Traces, {n_ports}x{n_ports} Ports)\n")

    # 1. Print the Legend
    print("Legend:")
    print(f"  {C11}11{RESET} = S11 (Port 1 In, Port 1 Out)   |  {C12}12{RESET} = S12 (Port 2 In, Port 1 Out)")
    print(f"  {C21}21{RESET} = S21 (Port 1 In, Port 2 Out)   |  {C22}22{RESET} = S22 (Port 2 In, Port 2 Out)")
    print(f"  {GREY}..{RESET} = Isolated (Zero)               |  {RED}ER{RESET} = ERROR (Non-zero in isolated zone)")
    print("-" * 70)
    
    # Column Headers
    header = "    " + "".join([f"{j:<3}" for j in range(n_ports)])
    print(header)
    print("-" * len(header))
    
    for i in range(n_ports):
        row_str = f"{i:2} |"
        for j in range(n_ports):
            val = s[i, j]
            
            # Check if we are inside a 2x2 trace block
            is_active_block = (i // 2 == j // 2)
            
            if is_active_block:
                # Find local position within the 2x2 block
                sub_i = i % 2
                sub_j = j % 2
                
                # Assign label and color based on local position
                if sub_i == 0 and sub_j == 0:
                    row_str += f"{C11}11 {RESET}"
                elif sub_i == 0 and sub_j == 1:
                    row_str += f"{C12}12 {RESET}"
                elif sub_i == 1 and sub_j == 0:
                    row_str += f"{C21}21 {RESET}"
                elif sub_i == 1 and sub_j == 1:
                    row_str += f"{C22}22 {RESET}"
            else:
                # Tolerance check for exact zeros
                if np.abs(val) > 1e-12:
                    row_str += f"{RED}ER {RESET}"
                else:
                    row_str += f"{GREY}.. {RESET}"
        print(row_str)

    # 2. Print the Exact Values for Base 2x2 Block
    print("\n--- Exact Values for Base 2x2 Block (Trace 0) ---")
    for i in range(2):
        val_str = "    "
        for j in range(2):
            v = s[i, j]
            sign = "+" if v.imag >= 0 else "-"
            # Color code the exact numbers too so they match the grid
            color = [C11, C12, C21, C22][i*2 + j]
            val_str += f"{color}{v.real: .4f} {sign} j{abs(v.imag):.4f}{RESET}      "
        print(val_str)
    print("=" * 70 + "\n")

# -------------------------------------------------
# Creating the Network for base 2x2 Matrix
# -------------------------------------------------

def generate_base_vertical_network(freq, 
                                   layer, 
                                   pitch=100e-6, 
                                   epsilon_r=3.3, 
                                   mu_r=1.0,
                                   pad_thickness=15e-6, 
                                   pad_radius=42.5e-6, 
                                   antipad_radius=63.75e-6,
                                   bump_height=100e-6, 
                                   bump_radius=42.5e-6,
                                   via_height=25e-6, 
                                   via_radius=25.5e-6,
                                   Z0=50,
                                   **kwargs):
    """
    Calculates the 2-port S-parameters for a single vertical trace transition.
    """
    # Constants
    mu_0 = (4e-7) * np.pi
    mu = mu_0 * mu_r
    epsilon_0 = 8.854e-12
    epsilon = epsilon_0 * epsilon_r

    # Package pad parasitics
    spacing_between_pad_and_antipad = antipad_radius - pad_radius
    C_pkg1 = C_pkg1_f(epsilon, pad_thickness, pad_radius, spacing_between_pad_and_antipad)
    C_pkg2 = C_pkg2_f(epsilon, pad_radius, pad_thickness)

    # Bump parasitics
    bump_spacing = pitch - 2 * bump_radius
    L_bump = L_s(mu, bump_height, bump_radius) - L_m(mu, bump_height, bump_spacing)
    C_bump = C_c(epsilon_0, bump_radius, bump_spacing, bump_height)

    # Via parasitics
    via_spacing = pitch - 2 * via_radius
    L_via = L_s(mu, via_height, via_radius) - L_m(mu, via_height, via_spacing)
    C_via = C_c(epsilon, via_radius, via_spacing, via_height)

    # Generate ABCD and convert to S-parameters
    ABCD = network_abcd(freq, C_bump, C_via, C_pkg1, C_pkg2, L_bump, L_via, layer)
    S, delta = abcd_to_s(ABCD, Z0=Z0)

    # Package into scikit-rf Network for easy downstream manipulation
    ntwk = rf.Network()
    ntwk.frequency = rf.Frequency.from_f(freq, unit='hz')
    ntwk.s = S
    ntwk.z0 = Z0
    ntwk.name = f"Vert_Layer_{layer}"

    return ntwk


# -------------------------------------------------
# Creating the Overall Network for the Vertical Layer
# -------------------------------------------------

def assemble_layer_network(num_traces, freq, layer, **kwargs):
    """
    Generates the base 2x2 vertical network and expands it into a
    2N x 2N block-diagonal network representing N isolated traces.
    
    Parameters
    ----------
    num_traces : int
        The total number of vertical traces on this layer.
    freq : ndarray
        The frequency sweep array.
    layer : int
        The target routing layer depth.
    **kwargs : dict
        The physical geometry and material properties to pass to the base generator.
        
    Returns
    -------
    full_layer_ntwk : skrf.Network
        The composite 2N-port network representing all isolated vertical transitions.
    """
    # 1. Generate the base 1-trace 2x2 network
    base_ntwk = generate_base_vertical_network(freq, layer, **kwargs)
    
    # 2. Extract base data and define new matrix dimensions
    base_s = base_ntwk.s  # Shape: (n_freqs, 2, 2)
    n_freqs = len(base_ntwk.frequency)
    n_ports_total = 2 * num_traces
    
    # 3. Initialize the block-diagonal giant matrix with zeros
    big_s = np.zeros((n_freqs, n_ports_total, n_ports_total), dtype=complex)
    
    # 4. Fill the diagonal
    # Since all vertical transitions are identical and isolated, we just copy 
    # the 2x2 base matrix down the diagonal.
    for i in range(num_traces):
        start_idx = i * 2
        end_idx = start_idx + 2
        big_s[:, start_idx:end_idx, start_idx:end_idx] = base_s
        
    # 5. Package into a new scikit-rf Network
    full_layer_ntwk = rf.Network()
    full_layer_ntwk.frequency = base_ntwk.frequency
    full_layer_ntwk.s = big_s
    full_layer_ntwk.z0 = base_ntwk.z0[0, 0] # Assume uniform Z0
    full_layer_ntwk.name = f"Full_Vertical_Layer_{layer}_{num_traces}_traces"
    
    return full_layer_ntwk


# # =============================================================================
# # QUICK TEST BLOCK FOR REPORT SCREENSHOT
# # =============================================================================
# if __name__ == "__main__":
#     import numpy as np
#     import skrf as rf

#     # 1. Setup a quick frequency sweep (1 GHz to 50 GHz)
#     test_freqs = np.linspace(1e9, 50e9, 50) 
    
#     # 2. Define how many traces you want to show in your report image
#     # 4 traces will create a nice, readable 8x8 block-diagonal matrix
#     num_traces_to_test = 4 
#     target_layer = 2 

#     print("Assembling Vertical Network...")
    
#     # 3. Call your assembly function (it will use the default kwargs you defined)
#     test_ntwk = assemble_layer_network(
#         num_traces=num_traces_to_test, 
#         freq=test_freqs, 
#         layer=target_layer
#     )

#     # 4. Trigger the colorful verification printout at exactly 1 GHz
#     verify_vertical_matrix(test_ntwk, freq_hz=1e9)

