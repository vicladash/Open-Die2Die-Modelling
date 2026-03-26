import emerge as em

def generate_1trace_s2p(filename, f_min, f_max, f_points, layer, **kwargs):
    """
    Generates a 1-trace (.s2p) Touchstone file using the EMerge solver.
    Calculates trace length dynamically based on the routing layer depth.
    """
    print(f"[EMerge] Meshing and solving 1-trace baseline: {filename}...")

    # 1. Extract physical parameters
    um = 1e-6
    di_thickness = kwargs.get('di_thickness', 25)
    cu_thickness = kwargs.get('cu_thickness', 8)
    w0 = kwargs.get('trace_width', 40)
    
    # --- Dynamic Trace Length Calculation ---
    base_separation = kwargs.get('die_to_die_separation', 3000)
    pitch_m = kwargs.get('pitch', 100e-6)
    pitch_um = pitch_m * 1e6 # Convert to microns for the solver
    
    trace_length = base_separation + ((layer - 2) * pitch_um)
    print(f"         Calculated Trace Length for Layer {layer}: {trace_length} um")

    board_bounds = kwargs.get('board_bounds', 30)
    epsilon_r = kwargs.get('epsilon_r', 3.3)
    losstan = kwargs.get('losstan', 0.01)
    sigma_cu = kwargs.get('sigma_cu', 44e6)

    board_thickness = (di_thickness * 2) + cu_thickness
    trace_bottom = - board_thickness / 2

    # 2. Materials 
    di = em.Material(er=epsilon_r, tand=losstan, opacity=0.3, color="#2C8A30")
    cu = em.Material(cond=sigma_cu, _metal=True, color="#F79424")

    # 3. 3D Model Setup
    model = em.Simulation('SingleTrace')
    pcb = em.geo.PCB(board_thickness, um, layers=3, material=di, 
                     trace_thickness=cu_thickness*um, thick_traces=True, trace_material=cu)

    # 4. Traces
    pcb.new(0, 0, w0, (1,0), trace_bottom).store('p1').straight(trace_length).store('p2')
    traces = pcb.compile_paths(merge=True)

    # 5. Board
    pcb.determine_bounds(board_bounds, board_bounds, board_bounds, board_bounds)
    diel = pcb.generate_pcb()

    # 6. Create Terminals
    lp1 = pcb.lumped_port(pcb.load('p1'))
    lp2 = pcb.lumped_port(pcb.load('p2'))

    # 7. Meshing & Solver config
    model.commit_geometry()
    model.mw.set_frequency_range(f_min, f_max, f_points)  
    model.mesher.set_boundary_size(traces, w0/2*um)
    model.generate_mesh()
    
    # 8. Attach ports and Solve
    model.mw.bc.LumpedPort(lp1, 1)
    model.mw.bc.LumpedPort(lp2, 2)
    data = model.mw.run_sweep(True, 4)  

    # 9. Post Processing and Export
    g = data.scalar.grid
    g.export_touchstone(filename, Z0ref=50, format="RI")

    return filename