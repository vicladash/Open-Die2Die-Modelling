import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import skrf as rf
import os
from main_modified import simulate


base_dir = os.path.dirname(__file__)

def cancel():
    global create
    global state
    create.destroy()
    create = None
    btn_packages.clear()
    btn_advancedmaps.clear()
    btn_standardmaps.clear()
    ent_layouts.clear()
    ent_setups.clear()
    btn_controls.clear()
    state = 'package'

    start.deiconify()

def previous():
    global state
    if state == 'map':
        if var_package.get() == 1:
            frm_advancedmap.place_forget()
        elif var_package.get() == 0:
            frm_standardmap.place_forget()
        frm_package.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        btn_controls[1].config(state='disabled')
        workaround = tk.Frame(master=frm_package)
        workaround.grid(row=2, column=0)
        btn_packages[0].select()
        start.update()
        update()
        state = 'package'
    elif state == 'layout':
        center_window(create, 1050, 800)
        frm_control.place(relx=0.5, rely=0.95, anchor=tk.CENTER)
        frm_layout.place_forget()
        if var_package.get() == 1:
            frm_advancedmap.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        elif var_package.get() == 0:
            frm_standardmap.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        if var_package.get() == 1:
            workaround = tk.Frame(master=frm_advancedmap)
            workaround.grid(row=2, column=0)
            btn_advancedmaps[0].select()
        elif var_package.get() == 0:
            workaround = tk.Frame(master=frm_standardmap)
            workaround.grid(row=2, column=0)
            btn_standardmaps[0].select()
        start.update()
        update()
        state = 'map'
    elif state == 'setup':
        frm_setup.place_forget()
        frm_layout.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
        btn_controls[2].config(state='normal')
        btn_controls[3].config(text='Finish')
        workaround = tk.Frame(master=frm_layout)
        workaround.grid(row=2, column=0)
        ent_layouts[0].focus()
        start.update()
        state = 'layout'

def exit():
    start.destroy()

def open_s():
    filepath = filedialog.askopenfilename(title='Open File', initialdir=os.path.expanduser('~/Documents'))
    reveal(filepath)

def replot():
    ax.set_ylabel(['Magnitude (dB)', 'Angle (\u00B0)', 'Real', 'Imaginary', r'Reciprocity Error, $\| S - S^T \|_F$',
                   r'Passivity Metric, $\max ( \sqrt{S^H \cdot S} )$', 'Impulse Response, |h(t)|'][var_plot.get()])
    ax.set_xlabel(['Frequency (Hz)', 'Frequency (Hz)', 'Frequency (Hz)', 'Frequency (Hz)', 'Frequency (Hz)', 'Frequency (Hz)',
                   'Time (s)'][var_plot.get()])
    to_plot = [-1 for i in range(num_ports**2*4+5)]
    if var_plot.get() == 6:
        to_plot[-2] = -2
        to_plot[-1] = -2
    elif var_plot.get() > 3:
        to_plot[var_plot.get() - 8] = -2
    elif var_plot.get() < 4:
        for i, var in enumerate(var_parameters):
            if var.get():
                to_plot[[1, 2, num_ports**2*2+1, num_ports**2*2+2][var_plot.get()]+2*i] = i
    for i in range(len(to_plot)):
        if to_plot[i] != -1 and lines[i] is None:
            if i == len(to_plot) - 1:
                lines[i] = ax.axvline(0, color='k', linestyle='--')
            elif i == len(to_plot) - 2:
                lines[i], = ax.plot(data[i], data[i+1], label=names_label[var_plot.get() - 4])
            elif i > len(to_plot) - 5:
                lines[i], = ax.plot(data[0], data[i], label=names_label[var_plot.get() - 4])
            elif i < len(to_plot) - 4:
                lines[i], = ax.plot(data[0], data[i], label=f'S[{to_plot[i]//num_ports+1},{to_plot[i]%num_ports+1}]')
        elif to_plot[i] == -1 and lines[i] is not None:
            lines[i].remove()
            lines[i] = None
    ax.relim()
    ax.autoscale()
    if var_plot.get() == 6:
        ax.set_xlim(data[-2][np.argmax(data[-1])]-0.2e-9, data[-2][np.argmax(data[-1])]+0.2e-9)
    ax.autoscale_view()
    global leg
    if leg is not None and all(i is None for i in lines):
        leg.remove()
    elif not all(i is None for i in lines):
        leg = ax.legend()
    canvas3.draw()

def finish():
    simulation_inputs = [['2', '1', '4', '5', '3', '6', '7', '8'][var_package.get()*(var_advancedmap.get()+2)+
                                                                  (1-var_package.get())*var_standardmap.get()]]
    simulation_inputs.extend([ent.get() for ent in ent_layouts])
    simulation_inputs.extend([ent.get() if isinstance(ent, tk.Entry) else var_setup.get() for ent in ent_setups])
    simulate(simulation_inputs)
    reveal(os.path.join(simulation_inputs[21], f'model.s{simulation_inputs[22]}p'))

def reveal(path):
    global create
    global opened
    global state
    if start.winfo_viewable():
        start.withdraw()
    elif create is not None:
        create.destroy()
        create = None
        btn_packages.clear()
        btn_advancedmaps.clear()
        btn_standardmaps.clear()
        ent_layouts.clear()
        ent_setups.clear()
        btn_controls.clear()
        state = 'package'
    elif opened is not None:
        opened.destroy()
        opened = None
        var_parameters.clear()
        data.clear()
        lines.clear()
        names_label.pop()
        
    opened = tk.Toplevel(start)
    opened.title(f'Opened Channel: {path}')
    center_window(opened, opened.winfo_screenwidth()-300, opened.winfo_screenheight()-150)
    opened.resizable(width=False, height=False)

    frm_out = tk.Frame(master=opened)
    frm_out.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    frm_top = tk.Frame(master=frm_out)
    frm_top.grid(row=0, column=0)
    for i, (btn, command) in enumerate([('New', new), ('Open', open_s), ('Help', empty), ('About', empty), ('Exit', exit)]):
        if btn == 'Help' or btn == 'About':
            tk.Button(master=frm_top, text=btn, command=command, state='disabled', width=10, height=2).grid(row=0, column=i, padx=10, pady=10)
        else:
            tk.Button(master=frm_top, text=btn, command=command, width=10, height=2).grid(row=0, column=i, padx=10, pady=10)
    frm_mid = tk.Frame(master=frm_out)
    frm_mid.grid(row=1, column=0)
    frm_midins = []
    for i, lbl in enumerate(['Summary', 'Port Names', 'Plot', 'Selected Parameters']):
        frm_midins.append(tk.Frame(master=frm_mid))
        frm_midins[-1].grid(row=0, column=i)
        tk.Label(master=frm_midins[-1], text=lbl).grid(row=0, column=0, padx=10, pady=10)
        frm_midins.append(tk.Frame(master=frm_midins[-1], padx=10, pady=10, highlightthickness=2, highlightbackground='DimGray', bg='#282828'))
        frm_midins[-1].grid(row=1, column=0, padx=10, pady=10)
    for i, lbl in enumerate(['File Name', 'Frequency Range', 'Freqeuncy Points', 'Reference Impedance']):
        tk.Label(master=frm_midins[1], text=f'{lbl}:', bg='#282828').grid(row=i, column=0, sticky='w')
    global num_ports
    num_ports = int(path.split('.')[-1][1:-1])
    tk.Label(master=frm_midins[1], text=os.path.basename(path), bg='#282828').grid(row=0, column=1, sticky='w')
    data.extend([[]for i in range(num_ports**2*2+1)])
    with open(path, mode='r', encoding='utf-8') as file:
        chunk = []
        for line in file:
            if line[0] == '!':
                continue
            if line[0] == '#':
                x_axis = line.split()[1]
                y_axis = line.split()[3]
                ref_imp = line.split()[5]
                continue
            chunk += line.split()
            if len(chunk) == num_ports**2*2+1:
                for i, j in enumerate(chunk):
                    data[i].append(float(j))
                chunk = []
    tk.Label(master=frm_midins[1], text=f'{data[0][0]:.3e} to {data[0][-1]:.3e} {x_axis}', bg='#282828').grid(row=1, column=1, sticky='w')
    tk.Label(master=frm_midins[1], text=f'{len(data[0])} points', bg='#282828').grid(row=2, column=1, sticky='w')
    tk.Label(master=frm_midins[1], text=f'{ref_imp} \u03A9', bg='#282828').grid(row=3, column=1, sticky='w')
    canvas = tk.Canvas(master=frm_midins[3], highlightthickness=0, width=230, height=150, bg='#282828')
    scrollbar = ttk.Scrollbar(master=frm_midins[3], orient='vertical', command=canvas.yview)
    scrollable_frame = tk.Frame(master=canvas, bg='#282828')
    scrollable_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
    canvas.config(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0)
    scrollbar.grid(row=0, column=1, sticky='ns')
    ent_ports = []
    for i in range(num_ports):
        tk.Label(master=scrollable_frame, text=f'{i}:', bg='#282828').grid(row=i, column=0, sticky='w')
        ent_ports.append(tk.Entry(scrollable_frame, highlightbackground='#282828'))
        ent_ports[-1].grid(row=i, column=1)
        ent_ports[-1].insert(0, f'P{i}')
    for i, btn in enumerate(['Magnitude', 'Angle', 'Real', 'Imaginary', 'Reciprocity', 'Passivity', 'Causality']):
        tk.Radiobutton(master=frm_midins[5], text=btn, variable=var_plot, value=i, command=replot, bg='#282828').grid(row=i, column=0,
                                                                                                                        sticky='w')
    canvas2 = tk.Canvas(master=frm_midins[7], highlightthickness=0, width=300, height=200, bg='#282828')
    scrollbary = ttk.Scrollbar(master=frm_midins[7], orient='vertical', command=canvas2.yview)
    scrollbarx = ttk.Scrollbar(master=frm_midins[7], orient='horizontal', command=canvas2.xview)
    scrollable_frame2 = tk.Frame(master=canvas2, bg='#282828')
    scrollable_frame2.bind('<Configure>', lambda e: canvas2.configure(scrollregion=canvas2.bbox('all')))
    canvas2.create_window((0, 0), window=scrollable_frame2, anchor='nw')
    canvas2.config(yscrollcommand=scrollbary.set)
    canvas2.config(xscrollcommand=scrollbarx.set)
    canvas2.grid(row=0, column=0)
    scrollbary.grid(row=0, column=1, sticky='ns')
    scrollbarx.grid(row=1, column=0, sticky='ew')
    for i in range(num_ports):
        for j in range(num_ports):
            var_parameters.append(tk.BooleanVar(value=False))
            tk.Checkbutton(master=scrollable_frame2, text=f'S[{i+1},{j+1}]', variable=var_parameters[-1], command=replot, indicatoron=0,
                           selectcolor='CornflowerBlue', bg='#282828').grid(row=i, column=j, sticky='ew')
    frm_bot = tk.Frame(master=frm_out, padx=10, pady=10)
    frm_bot.grid(row=2, column=0)
    fig = Figure(figsize=(10, 4), dpi=100)
    global ax
    ax = fig.add_subplot(111)
    ax.set_ylim(-240000, 0)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Magnitude (dB)')
    ax.grid(True)
    fig.tight_layout()
    global canvas3
    canvas3 = FigureCanvasTkAgg(fig, master=frm_bot)
    canvas3.draw()
    toolbar = NavigationToolbar2Tk(canvas3, frm_bot)
    toolbar.update()
    canvas3.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    more_data = []
    if y_axis == 'RI':
        for i in range(1, len(data), 2):
            ma = np.array(data[i]) + np.array(data[i+1]) * 1j
            more_data.append(20.0 * np.log10(np.maximum(np.abs(ma), 1e-12)))
            more_data.append(np.angle(ma, deg=True))
        data[1:1] = more_data
    elif y_axis == 'MA':
        for i in range(1, len(data), 2):
            ri = np.array(data[i]) * np.exp(1j * np.deg2rad(np.array(data[i+1])))
            more_data.append(ri.real)
            more_data.append(ri.imag)
        data.extend(more_data)
    ntwk = rf.Network(path)
    data.append(np.linalg.norm(rf.network.reciprocity(ntwk.s), axis=(1, 2)))
    data.append(np.max(rf.network.passivity(ntwk.s), axis=(1, 2)).real)
    f = ntwk.frequency.f
    df = f[1] - f[0]
    n_dc = int(f[0] / df)
    f_dc = np.linspace(0, f[0] - df, n_dc)
    f_new = np.concatenate([f_dc, f])
    S_dc = np.repeat(ntwk.s[0:1, :, :], n_dc, axis=0)
    S_new = np.concatenate([S_dc, ntwk.s], axis=0)
    freq_new = rf.Frequency.from_f(f_new, unit='hz')
    ntwk_dc = rf.Network(frequency=freq_new, s=S_new, z0=ntwk.z0[0])
    num_ports = ntwk_dc.nports
    worst_ratio = -np.inf
    worst_channel = None
    worst_t = None
    worst_h = None
    for i in range(num_ports):
        for j in range(num_ports):
            sij_data = ntwk_dc.s[:, i, j].reshape(-1, 1, 1)
            ntwk_sij = rf.Network(frequency=ntwk_dc.frequency, s=sij_data, z0=ntwk_dc.z0[:, i])
            t, h = ntwk_sij.impulse_response(window='hann', pad=4096, squeeze=True)
            neg_max = np.max(np.abs(h[t < 0]))
            pos_max = np.max(np.abs(h[t >= 0]))
            ratio = neg_max / max(pos_max, 1e-12)
            if ratio > worst_ratio:
                worst_ratio = ratio
                worst_channel = (i+1, j+1)
                worst_t = t
                worst_h = h
    data.append(worst_t)
    data.append(np.abs(worst_h))
    names_label.append(f'S[{worst_channel[0]},{worst_channel[1]}]')
    lines.extend([None for i in range(num_ports**2*4+5)])

def browse():
    filepath = filedialog.askdirectory(title='Browse Directories', initialdir=os.path.expanduser('~/Documents'))
    if not filepath:
        return
    ent_setups[-1].delete(0, tk.END)
    ent_setups[-1].insert(0, filepath)

def next():
    global state
    if state == 'package':
        frm_package.place_forget()
        if var_package.get() == 1:
            frm_advancedmap.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        elif var_package.get() == 0:
            frm_standardmap.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        btn_controls[1].config(state='normal')
        if var_package.get() == 1:
            workaround = tk.Frame(master=frm_advancedmap)
            workaround.grid(row=2, column=0)
            btn_advancedmaps[0].select()
        elif var_package.get() == 0:
            workaround = tk.Frame(master=frm_standardmap)
            workaround.grid(row=2, column=0)
            btn_standardmaps[0].select()
        start.update()
        update()
        state = 'map'
    elif state == 'map':
        center_window(create, 950, 450)
        frm_control.place(relx=0.5, rely=0.9, anchor=tk.CENTER)
        if var_package.get() == 1:
            frm_advancedmap.place_forget()
        elif var_package.get() == 0:
            frm_standardmap.place_forget()
        frm_layout.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
        workaround = tk.Frame(master=frm_layout)
        workaround.grid(row=2, column=0)
        ent_layouts[0].focus()
        start.update()
        state = 'layout'
    elif state == 'layout':
        frm_layout.place_forget()
        frm_setup.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
        btn_controls[2].config(state='disabled')
        btn_controls[3].config(text='Simulate')
        workaround = tk.Frame(master=frm_setup)
        workaround.grid(row=4, column=0)
        ent_setups[0].focus()
        start.update()
        state = 'setup'

def update():
    for btn in btn_packages:
        btn.config(highlightbackground='#282828')
    btn_packages[var_package.get()].config(highlightbackground='CornflowerBlue')

    for btn in btn_advancedmaps:
        btn.config(highlightbackground='#282828')
    btn_advancedmaps[var_advancedmap.get()].config(highlightbackground='CornflowerBlue')

    for btn in btn_standardmaps:
        btn.config(highlightbackground='#282828')
    btn_standardmaps[var_standardmap.get()].config(highlightbackground='CornflowerBlue')

    ent_setups[-2]['menu'].delete(0, 'end')
    max = [12, 12, 28, 22, 14, 50, 38, 24][var_package.get()*(var_advancedmap.get()+2)+(1-var_package.get())*var_standardmap.get()]
    for option in list(range(2, max+1, 2)):
        if not (option == 26 and max == 50):
            ent_setups[-2]['menu'].add_command(label=option, command=tk._setit(var_setup, f'{option}'))
    var_setup.set('2')

def new():
    global opened
    if start.winfo_viewable():
        start.withdraw()
    elif opened is not None:
        opened.destroy()
        opened = None
        var_parameters.clear()
        data.clear()
        lines.clear()
        names_label.pop()

    global create
    create = tk.Toplevel(start)
    create.title('Create Channel')
    center_window(create, 1050, 800)
    create.resizable(width=False, height=False)

    global frm_package
    frm_package = tk.Frame(master=create)
    frm_package.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
    tk.Label(master=frm_package, text='Select package type:').grid(row=0, column=0, padx=10, pady=10)
    frm_packagein = tk.Frame(master=frm_package, padx=10, pady=10, highlightthickness=2, highlightbackground='DimGray', bg='#282828')
    frm_packagein.grid(row=1, column=0, padx=10, pady=10)
    for i, (btn, size) in enumerate([('Standard', (950, 139)), ('Advanced', (950, 182))]):
        diagram = ImageTk.PhotoImage(Image.open(os.path.join(base_dir, f'{btn}.png')).resize(size, Image.Resampling.LANCZOS))
        btn_packages.append(tk.Radiobutton(master=frm_packagein, text=f'\n{btn} Package\n', image=diagram, compound=tk.TOP, variable=var_package,
                                           value=i, command=update, indicatoron=0, fg='Black', highlightthickness=2,
                                           highlightbackground='#282828'))
        btn_packages[-1].image = diagram
        btn_packages[-1].grid(row=i+1, column=0, padx=10, pady=10)

    global frm_advancedmap
    frm_advancedmap = tk.Frame(master=create)
    tk.Label(master=frm_advancedmap, text='Select bump map:').grid(row=0, column=0, padx=10, pady=10)
    frm_advancedmapin = tk.Frame(master=frm_advancedmap, padx=10, pady=10, highlightthickness=2, highlightbackground='DimGray', bg='#282828')
    frm_advancedmapin.grid(row=1, column=0, padx=10, pady=10)
    for i, (btn, size) in enumerate([('x32c8', (240, 231)),
                                     ('x32c10', (240, 166)),
                                     ('x32c16', (240, 70)),
                                     ('x64c8', (175, 240)),
                                     ('x64c10', (239, 240)),
                                     ('x64c16', (240, 112))]):
        diagram = ImageTk.PhotoImage(Image.open(os.path.join(base_dir, f'{btn}.png')).resize(size, Image.Resampling.LANCZOS))
        btn_advancedmaps.append(tk.Radiobutton(master=frm_advancedmapin, text=f'\n{btn[4:]}-Column x{btn[1:3]}\n', image=diagram, compound=tk.TOP,
                                               variable=var_advancedmap, value=i, command=update, indicatoron=0, fg='Black', highlightthickness=2,
                                               highlightbackground='#282828'))
        btn_advancedmaps[-1].image = diagram
        btn_advancedmaps[-1].grid(row=i//3, column=i%3, padx=10, pady=10)

    global frm_standardmap
    frm_standardmap = tk.Frame(master=create)
    tk.Label(master=frm_standardmap, text='Select bump map:').grid(row=0, column=0, padx=10, pady=10)
    frm_standardmapin = tk.Frame(master=frm_standardmap, padx=10, pady=10, highlightthickness=2, highlightbackground='DimGray', bg='#282828')
    frm_standardmapin.grid(row=1, column=0, padx=10, pady=10)
    for i, (btn, size) in enumerate([('x08c8', (450, 270)), ('x16c12', (450, 166))]):
        diagram = ImageTk.PhotoImage(Image.open(os.path.join(base_dir, f'{btn}.png')).resize(size, Image.Resampling.LANCZOS))
        btn_standardmaps.append(tk.Radiobutton(master=frm_standardmapin, text=f'\n{btn[4:]}-Column x{int(btn[1:3])}\n', image=diagram,
                                               compound=tk.TOP, variable=var_standardmap, value=i, command=update, indicatoron=0, fg='Black',
                                               highlightthickness=2, highlightbackground='#282828'))
        btn_standardmaps[-1].image = diagram
        btn_standardmaps[-1].grid(row=i, column=0, padx=10, pady=10)

    global frm_layout
    frm_layout = tk.Frame(master=create)
    tk.Label(master=frm_layout, text='Enter physical dimensions and material properties:').grid(row=0, column=0, padx=10, pady=10)
    frm_layoutout = tk.Frame(master=frm_layout)
    frm_layoutout.grid(row=1, column=0)
    frm_layoutins = []
    for i, lbl in enumerate(['Vertical Via/Bump', 'Horizontal Stripline', 'Shared Material Properties']):
        frm_layoutins.append(tk.Frame(master=frm_layoutout))
        frm_layoutins[-1].grid(row=0, column=i)
        tk.Label(master=frm_layoutins[-1], text=lbl).grid(row=0, column=0, padx=10, pady=10)
        frm_layoutins.append(tk.Frame(master=frm_layoutins[-1], padx=10, pady=10, highlightthickness=2, highlightbackground='DimGray',
                                      bg='#282828'))
        frm_layoutins[-1].grid(row=1, column=0, padx=10, pady=10)
    for i, ent in enumerate([('Pitch', 100, '\u03BCm'),
                             ('Pad Thickness', 15, '\u03BCm'),
                             ('Pad Radius', 42.5, '\u03BCm'),
                             ('Antipad Radius', 63.75, '\u03BCm'),
                             ('Bump Height', 100, '\u03BCm'),
                             ('Bump Radius', 42.5, '\u03BCm'),
                             ('Via Height', 25, '\u03BCm'),
                             ('Via Radius', 25.5, '\u03BCm')]):
        tk.Label(master=frm_layoutins[1], text=f'{ent[0]}:', bg='#282828').grid(row=i, column=0, sticky='w')
        ent_layouts.append(tk.Entry(master=frm_layoutins[1], width=10, highlightbackground='#282828'))
        ent_layouts[-1].insert(0, f'{ent[1]}')
        ent_layouts[-1].grid(row=i, column=1)
        tk.Label(master=frm_layoutins[1], text=f'{ent[2]}', bg='#282828').grid(row=i, column=2)
    for i, ent in enumerate([('Trace Width', 21, '\u03BCm'),
                             ('Die-to-die Separation', 300, '\u03BCm'),
                             ('Dielectric Thickness', 25, '\u03BCm'),
                             ('Copper Thickness', 15, '\u03BCm')]):
        tk.Label(master=frm_layoutins[3], text=f'{ent[0]}:', bg='#282828').grid(row=i, column=0, sticky='w')
        ent_layouts.append(tk.Entry(master=frm_layoutins[3], width=10, highlightbackground='#282828'))
        ent_layouts[-1].insert(0, f'{ent[1]}')
        ent_layouts[-1].grid(row=i, column=1)
        tk.Label(master=frm_layoutins[3], text=f'{ent[2]}', bg='#282828').grid(row=i, column=2)
    for i, ent in enumerate([('Relative Permittivity', 3.3, ''),
                             ('Relative Permeability', 1, ''),
                             ('Loss Tangent', 0.02, ''),
                             ('Copper Conductivity', 44, 'MS/m')]):
        tk.Label(master=frm_layoutins[5], text=f'{ent[0]}:', bg='#282828').grid(row=i, column=0, sticky='w')
        ent_layouts.append(tk.Entry(master=frm_layoutins[5], width=10, highlightbackground='#282828'))
        ent_layouts[-1].insert(0, f'{ent[1]}')
        ent_layouts[-1].grid(row=i, column=1)
        tk.Label(master=frm_layoutins[5], text=f'{ent[2]}', bg='#282828').grid(row=i, column=2)

    global frm_setup
    frm_setup = tk.Frame(master=create)
    tk.Label(master=frm_setup, text='Enter simulation setup:').grid(row=0, column=0, padx=10, pady=10)
    frm_setupins = []
    for i in range(3):
        frm_setupins.append(tk.Frame(master=frm_setup, padx=10, pady=10, highlightthickness=2, highlightbackground='DimGray', bg='#282828'))
        frm_setupins[-1].grid(row=i+1, column=0, padx=10, pady=10)
    for i, ent in enumerate([('Start Frequency', '10e6', 'Hz'),
                             ('End Frequency', '50e9', 'Hz'),
                             ('Reference Impedance', 50, '\u03A9')]):
        tk.Label(master=frm_setupins[0], text=f'{ent[0]}:', bg='#282828').grid(row=i, column=0, sticky='w')
        ent_setups.append(tk.Entry(master=frm_setupins[0], highlightbackground='#282828'))
        ent_setups[-1].insert(0, f'{ent[1]}')
        ent_setups[-1].grid(row=i, column=1)
        tk.Label(master=frm_setupins[0], text=f'{ent[2]}', bg='#282828').grid(row=i, column=2)
    tk.Label(master=frm_setupins[1], text='Layer to Simulate:', bg='#282828').grid(row=0, column=0, sticky='w')
    ent_setups.append(tk.OptionMenu(master=frm_setupins[1], variable=var_setup, value='2'))
    ent_setups[-1].config(width=1, bg='#282828')
    ent_setups[-1].grid(row=0, column=1)
    tk.Label(master=frm_setupins[2], text='Save to:', bg='#282828').grid(row=0, column=0)
    ent_setups.append(tk.Entry(master=frm_setupins[2], width=70, highlightbackground='#282828'))
    ent_setups[-1].insert(0, os.path.expanduser('~/Documents'))
    ent_setups[-1].grid(row=0, column=1)
    tk.Button(master=frm_setupins[2], text='Browse', command=browse, width=10, height=2, highlightbackground='#282828').grid(row=0, column=i)

    global frm_control
    frm_control = tk.Frame(master=create)
    frm_control.place(relx=0.5, rely=0.95, anchor=tk.CENTER)
    for i, (btn, command) in enumerate([('Cancel', cancel), ('Previous', previous), ('Next', next), ('Finish', finish)]):
        btn_controls.append(tk.Button(master=frm_control, text=btn, command=command, width=10, height=2))
        btn_controls[-1].grid(row=0, column=i, padx=10, pady=10)
    btn_controls[1].config(state='disabled')

    update()

def empty():
    pass

def center_window(win, width, height):
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width//2)-(width//2)
    y = (screen_height//2)-(height//2)
    win.geometry(f'{width}x{height}+{x}+{y}')


start = tk.Tk()
start.title('Start Menu')
center_window(start, 250, 625)
start.resizable(width=False, height=False)

frm_out = tk.Frame(master=start)
frm_out.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
logo = ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'logo.png')).resize((200, 200), Image.Resampling.LANCZOS))
tk.Label(master=frm_out, image=logo).grid(row=0, column=0, padx=10, pady=10)
frm_in = tk.Frame(master=frm_out, padx=10, pady=10, highlightthickness=2, highlightbackground='DimGray', bg='#282828')
frm_in.grid(row=1, column=0, padx=10, pady=10)
for i, (btn, command) in enumerate([('New', new), ('Open', open_s), ('Help', empty), ('About', empty), ('Exit', exit)]):
    if btn == 'Help' or btn == 'About':
        tk.Button(master=frm_in, text=btn, command=command, state='disabled', width=10, height=2,
                  highlightbackground='#282828').grid(row=i, column=0, padx=10, pady=10)
    else:
        tk.Button(master=frm_in, text=btn, command=command, width=10, height=2,
                  highlightbackground='#282828').grid(row=i, column=0, padx=10, pady=10)

create = None
frm_package = None
btn_packages = []
var_package= tk.IntVar()
frm_advancedmap = None
btn_advancedmaps = []
var_advancedmap = tk.IntVar()
frm_standardmap = None
btn_standardmaps = []
var_standardmap = tk.IntVar()
frm_layout = None
ent_layouts = []
frm_setup = None
ent_setups = []
var_setup = tk.StringVar()
frm_control = None
btn_controls = []
state = 'package'
opened = None
var_plot = tk.IntVar()
var_parameters = []
data = []
lines = []
ax = None
leg = None
canvas3 = None
num_ports = None
names_label = [r'$\| S - S^T \|_F$', r'$\max ( \sqrt{S^H \cdot S} )$']

start.mainloop()
