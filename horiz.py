import skrf as rf
import numpy as np


def print_smatrix_at_freq(file_path, freq_hz=16e9):
    ntwk = rf.Network(file_path)

    # Find closest frequency index
    idx = np.argmin(np.abs(ntwk.f - freq_hz))
    actual_freq = ntwk.f[idx]

    s = ntwk.s[idx]
    n = ntwk.nports

    COL_WIDTH = 22  # wide enough for complex values

    def fmt_val(val):
        if val == 0:
            return "0"
        if abs(val) < 1e-2 or abs(val) >= 1e3:
            return f"{val:.2E}".replace("E+0", "E").replace("E+", "E")
        return f"{val:.2f}"

    def fmt_cplx(x):
        re, im = x.real, x.imag
        sign = "+" if im >= 0 else "-"
        return f"{fmt_val(re)} {sign} j{fmt_val(abs(im))}"

    def hline():
        return "+" + "-" * 6 + "+" + "+".join(["-" * COL_WIDTH for _ in range(n)]) + "+"

    print(f"\nS-parameters at {actual_freq/1e9:.3f} GHz (closest match)\n")

    # Header
    print(hline())
    header = "| Sij  |"
    for j in range(n):
        header += f" S{j+1}".ljust(COL_WIDTH) + "|"
    print(header)
    print(hline())

    # Rows
    for i in range(n):
        row = f"| S{i+1}   |"
        for j in range(n):
            row += f" {fmt_cplx(s[i, j])}".ljust(COL_WIDTH) + "|"
        print(row)
        print(hline())

def print_smatrix_at_freq_colored(file_path, freq_hz=16e9):
    ntwk = rf.Network(file_path)

    # Find closest frequency index
    idx = np.argmin(np.abs(ntwk.f - freq_hz))
    actual_freq = ntwk.f[idx]

    s = ntwk.s[idx]
    n = ntwk.nports
    num_traces = n // 2 # Assumes 2 ports per trace

    # ANSI Colors
    COLORS = {
        'A': '\033[94m', # Blue (Top-Left Corner)
        'E': '\033[92m', # Green (Main Diagonal Middle)
        'G': '\033[96m', # Cyan (Bottom-Right Corner)
        'B': '\033[93m', # Yellow (Upper 1st Neighbor)
        'D': '\033[93m', # Yellow (Lower 1st Neighbor)
        'C': '\033[95m', # Magenta (Upper 2nd Neighbor)
        'F': '\033[95m', # Magenta (Lower 2nd Neighbor)
        '0': '\033[90m', # Grey (Zero/Other)
        'RESET': '\033[0m'
    }

    COL_WIDTH = 22  # wide enough for complex values

    def fmt_val(val):
        if val == 0:
            return "0"
        if abs(val) < 1e-2 or abs(val) >= 1e3:
            return f"{val:.2E}".replace("E+0", "E").replace("E+", "E")
        return f"{val:.2f}"

    def fmt_cplx(x):
        re, im = x.real, x.imag
        sign = "+" if im >= 0 else "-"
        return f"{fmt_val(re)} {sign} j{fmt_val(abs(im))}"

    def hline():
        return "+" + "-" * 6 + "+" + "+".join(["-" * COL_WIDTH for _ in range(n)]) + "+"

    def get_color_code(r, c):
        """Determines the color based on the 2x2 block identity"""
        block_row = r // 2
        block_col = c // 2
        
        # Identity Logic (Matches your A-G matrices)
        if block_row == block_col:
            if block_row == 0: return COLORS['A']
            elif block_row == num_traces - 1: return COLORS['G']
            else: return COLORS['E']
        elif block_col == block_row + 1: return COLORS['B']
        elif block_row == block_col + 1: return COLORS['D']
        elif block_col == block_row + 2: return COLORS['C']
        elif block_row == block_col + 2: return COLORS['F']
        
        return COLORS['0']

    print(f"\nS-parameters at {actual_freq/1e9:.3f} GHz (closest match)\n")
    print(f"Legend: {COLORS['A']}Block A (Start){COLORS['RESET']} | {COLORS['E']}Block E (Mid){COLORS['RESET']} | {COLORS['G']}Block G (End){COLORS['RESET']} | "
          f"{COLORS['B']}Block B/D (1st Neigh){COLORS['RESET']} | {COLORS['C']}Block C/F (2nd Neigh){COLORS['RESET']}")

    # Header
    print(hline())
    header = "| Sij  |"
    for j in range(n):
        header += f" S{j+1}".ljust(COL_WIDTH) + "|"
    print(header)
    print(hline())

    # Rows
    for i in range(n):
        row_str = f"| S{i+1:<4}|"
        for j in range(n):
            # 1. Format the raw text value
            val_text = f" {fmt_cplx(s[i, j])}"
            
            # 2. Pad it to the correct width FIRST
            # We subtract 1 to account for the leading space added above
            padded_text = val_text.ljust(COL_WIDTH)
            
            # 3. Wrap in color code
            # Note: The color code must NOT be inside the ljust, 
            # otherwise Python counts the invisible color characters as length
            color = get_color_code(i, j)
            row_str += f"{color}{padded_text}{COLORS['RESET']}|"
            
        print(row_str)
        print(hline())


# --- Example Usage ---
# Assuming 'base_network' is your 6-port .s6p file from the field solver
# expanded_network = extrapolate_network(base_network, target_num_traces=8)
# expanded_network.write_touchstone('ucie_8_lane_model.s16p')
def extrapolate_network(original_ntwk, target_num_traces):
    """
    Extrapolates a 3-trace (6-port) scikit-rf Network into an N-trace (2*N-port) Network
    using a block-Toeplitz expansion pattern.
    
    Parameters
    ----------
    original_ntwk : skrf.Network
        The input network. MUST be 6-port (representing 3 coupled traces).
        Ports must be ordered by trace (e.g., Trace1_In, Trace1_Out, Trace2_In...).
    target_num_traces : int
        The number of traces you want in the final network.
        The resulting network will have 2 * target_num_traces ports.
        
    Returns
    -------
    new_ntwk : skrf.Network
        The expanded network.
    """
    
    # 1. Validation
    if original_ntwk.number_of_ports != 6:
        raise ValueError("Input network must have exactly 6 ports (3 traces).")
    
    if target_num_traces < 3:
        raise ValueError("Target number of traces must be >= 3.")

    # 2. Extract the 2x2 Building Blocks from the S-matrix
    # The S-matrix shape is (n_freqs, 6, 6). 
    # We slice it into 2x2 blocks relative to the 3x3 trace grid.
    s = original_ntwk.s
    
    # Row 0 blocks
    A = s[:, 0:2, 0:2] # Top-left corner
    B = s[:, 0:2, 2:4] # 1st Upper off-diag
    C = s[:, 0:2, 4:6] # 2nd Upper off-diag
    
    # Row 1 blocks (The repeating "Middle" behavior)
    D = s[:, 2:4, 0:2] # 1st Lower off-diag
    E = s[:, 2:4, 2:4] # The repeating Main Diagonal block
    # Note: We assume B at [0,1] is the same coupling as at [1,2], etc.
    
    # Row 2 blocks
    F = s[:, 4:6, 0:2] # 2nd Lower off-diag
    G = s[:, 4:6, 4:6] # Bottom-right corner
    
    # 3. Initialize the new giant S-matrix
    n_freqs = len(original_ntwk.frequency)
    n_ports_new = 2 * target_num_traces
    new_s = np.zeros((n_freqs, n_ports_new, n_ports_new), dtype=complex)
    
    # 4. Fill the new matrix using the "Sliding Window" logic
    # We iterate through the block grid (row_idx, col_idx) where each index represents a trace.
    for row in range(target_num_traces):
        for col in range(target_num_traces):
            
            # Calculate the pixel indices for this 2x2 block in the giant matrix
            r_start, r_end = row * 2, (row + 1) * 2
            c_start, c_end = col * 2, (col + 1) * 2
            
            # --- Logic for placing blocks ---
            
            # Case 1: Main Diagonal (The trace itself)
            if row == col:
                if row == 0:
                    new_s[:, r_start:r_end, c_start:c_end] = A
                elif row == target_num_traces - 1:
                    new_s[:, r_start:r_end, c_start:c_end] = G
                else:
                    new_s[:, r_start:r_end, c_start:c_end] = E
            
            # Case 2: 1st Upper Diagonal (Neighbor to the right)
            elif col == row + 1:
                new_s[:, r_start:r_end, c_start:c_end] = B
                
            # Case 3: 2nd Upper Diagonal (Next-nearest neighbor right)
            elif col == row + 2:
                new_s[:, r_start:r_end, c_start:c_end] = C
                
            # Case 4: 1st Lower Diagonal (Neighbor to the left)
            elif row == col + 1:
                new_s[:, r_start:r_end, c_start:c_end] = D
                
            # Case 5: 2nd Lower Diagonal (Next-nearest neighbor left)
            elif row == col + 2:
                new_s[:, r_start:r_end, c_start:c_end] = F
            
            # All other blocks remain 0 (as initialized)

    # 5. Create the new Network object
    new_ntwk = rf.Network()
    new_ntwk.frequency = original_ntwk.frequency
    new_ntwk.s = new_s
    new_ntwk.z0 = original_ntwk.z0[0,0] # Assuming uniform system Z0
    new_ntwk.name = f"{original_ntwk.name}_extrapolated_{target_num_traces}traces"
    
    return new_ntwk

# --- Example Usage ---
# layer_net = assemble_layer_network(
#     trace_groups=[3, 5, 1], 
#     s2p_path='trace_1.s2p',
#     s4p_path='trace_2.s4p',
#     s6p_path='trace_3.s6p'
# )
# layer_net.write_touchstone('layer_1_complete.sNp')
def assemble_layer_network(trace_groups, s2p_path, s4p_path, s6p_path):
    """
    Constructs a full-layer S-parameter network by assembling isolated trace groups
    into a block-diagonal matrix.
    
    Parameters
    ----------
    trace_groups : list of int
        A list defining the number of traces in each isolated group.
        Example: [3, 5, 1] means:
        - Group 1: 3 traces (uses s6p directly)
        - Group 2: 5 traces (extrapolated from s6p)
        - Group 3: 1 trace (uses s2p)
        
    s2p_path : str
        Path to the 1-trace Touchstone file (.s2p).
    s4p_path : str
        Path to the 2-trace Touchstone file (.s4p).
    s6p_path : str
        Path to the 3-trace Touchstone file (.s6p).
        
    Returns
    -------
    full_layer_ntwk : skrf.Network
        The composite network representing the entire layer.
    """
    
    # 1. Load Base Networks
    # We load these once to avoid repeated I/O
    net_1t = rf.Network(s2p_path)
    net_2t = rf.Network(s4p_path)
    net_3t = rf.Network(s6p_path)
    
    # Validation: Ensure all files have the same frequency points
    if not (np.array_equal(net_1t.f, net_2t.f) and np.array_equal(net_2t.f, net_3t.f)):
        raise ValueError("All input Touchstone files must have identical frequency points.")

    sub_networks = []

    # 2. Generate the Sub-Network for each group
    print(f"Assembling Layer with groups: {trace_groups}")
    
    for i, n_traces in enumerate(trace_groups):
        if n_traces == 1:
            print(f"  - Group {i+1}: 1 trace (Using s2p)")
            sub_networks.append(net_1t)
            
        elif n_traces == 2:
            print(f"  - Group {i+1}: 2 traces (Using s4p)")
            sub_networks.append(net_2t)
            
        elif n_traces == 3:
            print(f"  - Group {i+1}: 3 traces (Using s6p)")
            sub_networks.append(net_3t)
            
        elif n_traces > 3:
            print(f"  - Group {i+1}: {n_traces} traces (Extrapolating s6p)")
            # Using the function we created previously
            extrapolated = extrapolate_network(net_3t, target_num_traces=n_traces)
            sub_networks.append(extrapolated)
            
        else:
            raise ValueError(f"Invalid trace count: {n_traces}. Must be > 0.")

    # 3. Create the Block Diagonal Matrix
    # scikit-rf has a specific function for this: ntwk.create_connected_network is complex,
    # but strictly electrically isolated networks can be merged using a block-diag approach.
    # However, skrf doesn't have a simple 'block_diag' for Networks, so we do it manually via numpy.
    
    freqs = net_1t.frequency
    total_ports = sum(ntwk.number_of_ports for ntwk in sub_networks)
    n_freqs = len(freqs)
    
    # Initialize giant zero matrix: (Freqs, Total_Ports, Total_Ports)
    big_s = np.zeros((n_freqs, total_ports, total_ports), dtype=complex)
    
    current_idx = 0
    
    for sub_net in sub_networks:
        n_sub = sub_net.number_of_ports
        
        # Insert the sub-matrix block along the diagonal
        # This keeps them electrically isolated (zeros everywhere else)
        big_s[:, current_idx : current_idx + n_sub, current_idx : current_idx + n_sub] = sub_net.s
        
        current_idx += n_sub

    # 4. Final Packaging
    full_layer_ntwk = rf.Network()
    full_layer_ntwk.frequency = freqs
    full_layer_ntwk.s = big_s
    full_layer_ntwk.z0 = net_1t.z0[0,0] # Assume uniform Z0 across all
    full_layer_ntwk.name = f"Full_Layer_Assembly_{trace_groups}"
    
    return full_layer_ntwk


#ntwk_layer_2 =  assemble_layer_network([5,5], "one_trace_sara.s2p", "two_trace_sara.s4p", "three_trace_sara.s6p")
#ntwk_layer_2.write_touchstone("ntwk_layer_2")
#print_smatrix_at_freq_colored("ntwk_layer_2.s20p")





#-------------------------------------------------------------------------------------------------------------
#Testing extrapolate Network Function
#-------------------------------------------------------------------------------------------------------------
#ntwk6 = rf.Network("three_trace_sara.s6p")
#print_smatrix_at_freq_colored("three_trace_sara.s6p")
#print_smatrix_at_freq("three_trace_sara.s6p")

#ntwk_test = extrapolate_network(ntwk6, 8)
#ntwk_test.write_touchstone("test_trace_model")
#print_smatrix_at_freq_colored("test_trace_model.s16p")
#print_smatrix_at_freq("test_trace_model.s16p")


