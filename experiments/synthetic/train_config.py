import numpy as np
from scipy import stats
import os

## EXPERIMENTAL DESIGN

exp = 'synthetic'                   # Experiment name, used for paths
m = 512                             # Number of simulations

# Name the parameter
theta_names = [  
                r'$k_{\rm{s}}$',
                r'$k_{\rm{c}}$', 
                r'$h_{\rm{b}}$',
                r'$r_{\rm{b}}$',
                r'$l_{\rm{c}}$',
                r'$A$',
                r'$\omega$',
                r'$e_{\rm{v}}$',
]

# Define lower, upper bounds in log10 space
theta_bounds = np.array([
                    [-2, 0],                # Sheet conductivity
                    [np.log10(0.05), 
                        np.log10(0.5)],     # Channel conductivity
                    [np.log10(0.05), 0],    # Bed bump height
                    [1, 2],                 # Bed bump aspect ratio
                    [0, 2],                 # Channel-sheet width
                    [-24, -23],             # Rheology parameter (C&P Table 3.3 p 73)
                    [np.log10(1/500),       # Transition parameter
                        np.log10(1/5000)],
                    [np.log10(5e-5), 
                        np.log10(5e-4)],    # Englacial storage parameter
])

# How to sample parameters
#   None: Use default sampling (minimized centered discrepancy LH)
#   stats.qmc.QMCEngine
theta_sampler = stats.qmc.Sobol(len(theta_names), seed=20240318, optimization=None)

## PATHS
base = os.path.expanduser('~/SFU-code/GladsGP/experiments/synthetic')
sim_dir = os.path.join(base, 'issm/train/')
analysis_dir = os.path.join(base, 'analysis/')
exp_dir = os.path.join(base, 'expdesign/')
mesh = os.path.join('../data/geom/synthetic_mesh.pkl')

# Paths to use for parameter design
X_physical = os.path.join(exp_dir, '{exp}_train_physical.csv'.format(exp=exp))
X_log = os.path.join(exp_dir, '{exp}_train_log.csv'.format(exp=exp))
X_standard = os.path.join(exp_dir, '{exp}_train_standard.csv'.format(exp=exp))
table = 'train.dat'

## ISSM-GlaDS CONFIGURATION
#   Tell ISSM how to set hydrology parameters given the parameter file
def parser(md, jobid):
    X = np.loadtxt(X_physical, delimiter=',', skiprows=1)
    k_s,k_c,h_bed,r_bed,l_c,A,omega,e_v = X[jobid-1, :]
    vertices = np.ones((md.mesh.numberofvertices, 1))
    md.hydrology.sheet_conductivity = k_s*vertices
    md.hydrology.channel_conductivity = k_c*vertices
    md.hydrology.bump_height = h_bed*vertices
    md.hydrology.cavity_spacing = h_bed*r_bed
    md.hydrology.channel_sheet_width = l_c
    md.hydrology.rheology_B_base = A**(-1./3.)*vertices
    md.hydrology.creep_open_flag = 0
    md.hydrology.omega = omega
    md.hydrology.englacial_void_ratio = e_v
    return md
    

## GP CONFIGURATION
p = 5               # Number of PCs
data_dir = os.path.join(analysis_dir, '/data/')
figures = os.path.join(analysis_dir, 'figures/')
Y_physical = os.path.join(sim_dir, '{exp}_ff.npy'.format(exp=exp))
