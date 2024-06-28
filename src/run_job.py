import os
import sys
import argparse

import numpy as np
import pickle

# Import ISSM paths
ISSM_DIR = os.getenv('ISSM_DIR')
sys.path.append(os.path.join(ISSM_DIR, 'bin/'))
sys.path.append(os.path.join(ISSM_DIR, 'lib/'))
from issmversion import issmversion
sys.path.append(os.path.join(ISSM_DIR, 'src/m/dev/'))
import devpath
# Import ISSM modules. These follow the pattern of
# from X import X because they are structured like a
# matlab project
from read_netCDF import read_netCDF

from model import model
from meshconvert import meshconvert
from solve import solve
from setmask import setmask
from parameterize import parameterize

import netCDF4 as nc
from src.utils import import_config

def run_job(config, jobid):
    """Execute seasonal ISSM-GlaDS simulation number 'jobid'
    
    Default ISSM parameters are set by the defaults file,
    and job-specific parameters are set by the parameterfile.

    Results are saved in directory
        RUN/output_XXX/
    The md.hydrology portion of the model class is pickled as
    md.hydrology.pkl and individual fields are saved in .npy format.
    
    Parameters
    ----------
    jobid : int
            Row number in the parameterfile. Note this ID is
            one-indexed, i.e. this should take values [1, n_jobs]
            inclusive
    defaults : str, optional
               Path to python defaults file
    meshfile : str, optional
               Path to triangular mesh file
    parameterfile : str, optional
                    Path to parameter file
    
    Returns
    -------
    md : model
         Solved model
    """

    # Initialize model, set mesh, and set default parameters
    md = model()
    
    # with nc.Dataset(meshfile, 'r') as dmesh:
    #     xy = dmesh['tri/nodes'][:].data.T
    #     elements = dmesh['tri/connect'][:].data.T.astype(int)
    # md.mesh.x = xy[:, 0]
    # md.mesh.y = xy[:, 1]
    # md.mesh.elements = elements
    # md = meshconvert(md, md.mesh.elements, md.mesh.x, md.mesh.y)

    md = read_netCDF(config.mesh)  
    md = setmask(md, '', '')
    md = parameterize(md, '../defaults.py')
    md.miscellaneous.name = 'ensemble_{:03d}'.format(jobid)


    # Overwrite hydrology defaults for given parameter vector
    md = config.parser(md, jobid)

    # Make results directory if necessary and save md.hydrology class
    resdir = 'RUN/output_%03d/' % jobid
    if not os.path.exists(resdir):
        os.makedirs(resdir)
    
    hydro = md.hydrology
    with open(os.path.join(resdir, 'md.hydrology.pkl'), 'wb') as modelinfo:
        pickle.dump(hydro, modelinfo)

    # Solve and save output fields to numpy binary files
    md = solve(md, 'Transient')
    requested_outputs = extract_requested_outputs(md)
    for field in requested_outputs.keys():
        np.save(os.path.join(resdir, '{}.npy'.format(field)), 
            requested_outputs[field])
    return md

def extract_requested_outputs(md):
    """
    Extract arrays of model output fields from ISSM outputs

    Construct a dictionary where the values are ( - , n_timesteps)
    arrays by iterating over the md.results.TransitionSolution
    struct array.

    Parameters
    ----------
    md : model
         Solved ISSM model instance
    
    Returns
    -------
    dict of model output fields
    """
    imin=-366
    imax = -1
    # imin = 0
    # imax = -1
    phi_bed = np.vstack(md.materials.rho_freshwater*md.constants.g*md.geometry.bed)
    phi = np.array([ts.HydraulicPotential[:, 0] for ts in md.results.TransientSolution[imin:imax]]).T
    N = np.array([ts.EffectivePressure[:, 0] for ts in md.results.TransientSolution[imin:imax]]).T
    pw = phi - phi_bed
    ff = pw/(N + pw)
    outputs = dict(
        phi = phi,
        N = N,
        ff = ff,
        h_s = np.array([ts.HydrologySheetThickness[:, 0] for ts in md.results.TransientSolution[imin:imax]]).T,
        S = np.array([ts.ChannelArea[:, 0] for ts in md.results.TransientSolution[imin:imax]]).T,
        Q = np.array([ts.ChannelDischarge[:, 0] for ts in md.results.TransientSolution[imin:imax]]).T,
        time = np.array([ts.time for ts in md.results.TransientSolution[imin:imax]]).T,
        vx = np.array([ts.HydrologyWaterVx[:, 0] for ts in md.results.TransientSolution[imin:imax]]).T,
        vy = np.array([ts.HydrologyWaterVy[:, 0] for ts in md.results.TransientSolution[imin:imax]]).T,
    )
    return outputs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('configuration_file')
    parser.add_argument('jobid', type=int)
    args = parser.parse_args()
    config = import_config(args.configuration_file)
    md = run_job(config, args.jobid)

if __name__=='__main__':
    main()
