import horiz
import vert
import numpy as np
import os
import em_solver_1t
import em_solver_2t
import em_solver_3t
import shutil

# =============================================================================
# 1. ROUTING SPECIFICATIONS DICTIONARY
# It maps Package -> Layer -> Trace Groups
# =============================================================================
ROUTING_SPECS = {
    "x16_Standard": {
        2: [5, 5],
        4: [1, 1, 1, 1, 1, 1],
        6: [1, 1, 1, 1],
        8: [5, 5],
        10: [1, 1, 1, 1, 1, 1],
        12: [1, 1, 1, 1]
    },
    "x8_Standard": {
        2: [3, 3],
        4: [1, 1],
        6: [1, 1, 1, 1],
        8: [3, 3],
        10: [1, 1],
        12: [1, 1, 1, 1]
    },
    "x32_Advanced_16Col": {
        2: [16],
        4: [3, 2, 3, 3],
        6: [2, 7, 4],
        8: [2, 1, 7, 2],
        10: [7, 2, 3],
        12: [2, 13],
        14: [1]
    },
    "x32_Advanced_8Col": {
        2: [2, 1, 3], 
        4: [2, 1, 2], 
        6: [1, 5], 
        8: [4, 3], 
        10: [2, 1, 2], 
        12: [7], 
        14: [1, 1, 1, 1], 
        16: [2, 2, 1], 
        18: [7], 
        20: [2, 1, 3], 
        22: [2, 1, 2], 
        24: [7], 
        26: [2, 1, 3], 
        28: [1, 1, 1, 1]
    },
    "x32_Advanced_10Col": {
        2: [5, 4], 
        4: [6, 1], 
        6: [2, 1, 1, 3], 
        8: [10], 
        10: [1, 1, 1], 
        12: [1, 3, 4], 
        14: [4, 3, 1], 
        16: [6, 1], 
        18: [2, 6], 
        20: [4, 3], 
        22: [5, 1]
    },
    "x64_Advanced_8Col": {
        2: [8], 
        4: [3, 3], 
        6: [4, 2], 
        8: [8], 
        10: [1, 1, 1], 
        12: [4, 1, 1], 
        14: [8], 
        16: [1, 1, 3], 
        18: [4, 3], 
        20: [5, 1], 
        22: [2, 2, 2], 
        24: [1, 1, 3], 
        # 26: [], # No routing Signals
        28: [3, 1, 1], 
        30: [2, 2, 2], 
        32: [1, 5], 
        34: [3, 4], 
        36: [3, 1, 1], 
        38: [8], 
        40: [1, 1, 4], 
        42: [1, 1, 1], 
        44: [8], 
        46: [2, 4], 
        48: [3, 3], 
        50: [8]
    },
    "x64_Advanced_10Col": {
        2: [10], 
        4: [2, 3, 2], 
        6: [2, 3, 2], 
        8: [10], 
        10: [1, 1, 1, 1], 
        12: [4, 4], 
        14: [3, 6], 
        16: [5, 3], 
        18: [5, 3], 
        20: [1, 1, 1], 
        22: [3, 4], 
        24: [9], 
        26: [3, 2, 3],
        28: [9], 
        30: [4, 3], 
        32: [10], 
        34: [2, 3, 2], 
        36: [2, 3, 3], 
        38: [10]
    },
    "x64_Advanced_16Col": {
        2: [8, 6], 
        4: [6, 8], 
        6: [2, 5, 3, 3], 
        8: [3, 5, 4], 
        10: [6, 9], 
        12: [1, 1, 1, 1, 1, 1], 
        14: [1, 1, 1, 1, 1, 1], 
        16: [9, 6], 
        18: [4, 5, 3], 
        20: [3, 3, 5, 2], 
        22: [8, 6], 
        24: [6, 8]
    }
}

# =============================================================================
# 2. HELPER: PORT REORDERING
# =============================================================================

def reorder_trace_to_cascade(ntwk):
    """
    Converts port ordering from [In1, Out1, In2, Out2...] 
    to [In1, In2... Out1, Out2...] so skrf's ** operator works correctly.
    """
    n_ports = ntwk.number_of_ports
    num_traces = n_ports // 2
    
    current_ports = list(range(n_ports))
    new_ports = []
    
    for i in range(num_traces):
        # Even ports (0, 2, 4...) are inputs, they map to the first half (0, 1, 2...)
        new_ports.append(i)
        # Odd ports (1, 3, 5...) are outputs, they map to the second half (N, N+1, N+2...)
        new_ports.append(num_traces + i)
        
    ntwk_reordered = ntwk.copy()
    ntwk_reordered.renumber(current_ports, new_ports)
    return ntwk_reordered

# =============================================================================
# 3. MAIN EXECUTION FLOW
# =============================================================================
def simulate(simulate_inputs):
    print("=== UCIe S-Parameter Simulation Tool ===\n")

    # --- Step A: User Selection ---
    packages = list(ROUTING_SPECS.keys())
    print("Available Packages:")
    for i, pkg in enumerate(packages):
        print(f"  {i + 1}. {pkg}")
    
    pkg_idx = int(simulate_inputs[0]) - 1
    selected_package = packages[pkg_idx]

    available_layers = list(ROUTING_SPECS[selected_package].keys())
    print(f"\nAvailable Layers for {selected_package}: {available_layers}")
    target_layer = int(simulate_inputs[20])

    if target_layer not in available_layers:
        print("Error: Invalid layer selected.")
        return

    trace_groups = ROUTING_SPECS[selected_package][target_layer]
    total_traces = sum(trace_groups)

    print(f"\n[INFO] Simulating {selected_package} - Layer {target_layer}")
    print(f"[INFO] Total Traces: {total_traces}\n")

    # --- Step B: Global Parameters & File Paths ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # CHANGED: We now define the paths for the newly generated dynamic files
    s2p_path = os.path.join(script_dir, f'base_1t_L{target_layer}.s2p')
    s4p_path = os.path.join(script_dir, f'base_2t_L{target_layer}.s4p')
    s6p_path = os.path.join(script_dir, f'base_3t_L{target_layer}.s6p')
    
    # Define frequency bounds to pass to both the EM solver and the Vertical solver
    f_min = float(simulate_inputs[17])
    f_max = float(simulate_inputs[18])
    f_points = 20
    freq_sweep = np.linspace(f_min, f_max, f_points)

    uci_geometry = {
        # --- Shared Material Properties ---
        'epsilon_r': float(simulate_inputs[13]),               
        'mu_r': float(simulate_inputs[14]),                    
        'losstan': float(simulate_inputs[15]),                
        'sigma_cu': float(simulate_inputs[16])*1e6,               

        # --- Horizontal Stripline Parameters ---
        'trace_width': float(simulate_inputs[9]),              
        'die_to_die_separation': float(simulate_inputs[10]),  
        'di_thickness': float(simulate_inputs[11]),             
        'cu_thickness': float(simulate_inputs[12]),              
        'board_bounds': 30,             

        # --- Vertical Via/Bump Parameters ---
        'pitch': float(simulate_inputs[1])*1e-6,                
        'pad_thickness':float(simulate_inputs[2])*1e-6,      #same as cu_thickness   
        'pad_radius': float(simulate_inputs[3])*1e-6,          
        'antipad_radius': float(simulate_inputs[4])*1e-6,     
        'bump_height': float(simulate_inputs[5])*1e-6,          
        'bump_radius': float(simulate_inputs[6])*1e-6,         
        'via_height': float(simulate_inputs[7])*1e-6,        #same as di_thickness         
        'via_radius': float(simulate_inputs[8])*1e-6,          

        # --- System Parameters ---
        'Z0': float(simulate_inputs[19])                        
    }

    # --- Step C: Run EM Field Solvers ---
    # NEW: We generate the golden base files dynamically based on the layer requested
    print("\n--- Generating Golden EM Base Files ---")
    em_solver_1t.generate_1trace_s2p(s2p_path, f_min, f_max, f_points, target_layer, **uci_geometry)
    em_solver_2t.generate_2trace_s4p(s4p_path, f_min, f_max, f_points, target_layer, **uci_geometry)
    em_solver_3t.generate_3trace_s6p(s6p_path, f_min, f_max, f_points, target_layer, **uci_geometry)

    # --- Step D: Generate Raw Networks ---
    print("\n--- Assembling Full Layer Matrices ---")
    print("Generating Horizontal Matrix from EM data...")
    horiz_ntwk = horiz.assemble_layer_network(trace_groups, s2p_path, s4p_path, s6p_path)
    
    freq_sweep = horiz_ntwk.f

    print("Generating Vertical Via Matrix mathematically...")
    vert_ntwk = vert.assemble_layer_network(total_traces, freq_sweep, target_layer, **uci_geometry)

    # --- Step E: Format and Cascade ---
    print("\n--- Cascading Full Channel ---")
    print("Reordering ports and multiplying [Vert] x [Horiz] x [Vert_Flipped]...")
    
    # 1. Reorder both networks for cascading
    horiz_ready = reorder_trace_to_cascade(horiz_ntwk)
    vert_ready = reorder_trace_to_cascade(vert_ntwk)
    
    # 2. Define the Tx side (Die to Package) and Rx side (Package to Die)
    vert_tx = vert_ready
    vert_rx = vert_ready.flipped() # Flips ports to mirror the via transition
    
    # 3. Perform the Matrix Cascade
    full_channel = vert_tx ** horiz_ready ** vert_rx
    full_channel.name = f"Full_Channel_{selected_package}_L{target_layer}"

    # --- Step F: Export ---
    filename = f"{full_channel.name}_{total_traces}traces.s{total_traces*2}p"
    full_channel.write_touchstone(filename)
    
    print(f"\n[SUCCESS] Exported {total_traces*2}-port channel to: {filename}")

    shutil.copy(filename, os.path.join(simulate_inputs[21], f'model.s{total_traces*2}p'))
    simulate_inputs.append(total_traces*2)


if __name__ == "__main__":
    simulate()

    
    # 5. Checks
    #check_causal(S_total)
    #check_passive(S_total)
    
    # 6. Plot example
    #plot_sparam(S_total, "S23")
