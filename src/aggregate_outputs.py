"""
Collect outputs from individual simulations into .npy arrays
"""

import os
import sys
import importlib
import argparse

issm_dir = os.getenv('ISSM_DIR')
print(issm_dir)
sys.path.append(issm_dir + '/bin')
sys.path.append(issm_dir + '/lib')
from issmversion import issmversion
sys.path.append(issm_dir + '/src/m/dev')
import devpath
from read_netCDF import read_netCDF

import numpy as np
import netCDF4 as nc

from . import definitions

def collect_issm_results(njobs, exp, mesh='../data/mesh/mesh_04.nc'):

    # Definitions for special quantities of interest
    fluxgate_positions = np.arange(5e3, 35e3, 5e3)
    R_thresholds = np.array([0.5, 1.])
    S_thresholds = 0.5*np.pi*R_thresholds**2

    md = read_netCDF('data/geom/IS_bamg.nc')
    nodes = np.array([md.mesh.x, md.mesh.y]).T
    connect = md.mesh.elements.astype(int)-1

#    with nc.Dataset(mesh, 'r') as dmesh:
#        nodes = dmesh['tri/nodes'][:].data.T
#        edges = dmesh['tri/edge_midpoints'][:].data.T
#        connect = dmesh['tri/connect'][:].data.T.astype(int) - 1
#        connect_edge = dmesh['tri/connect_edge'][:].data.T.astype(int) - 1
#        edge_length = dmesh['tri/edge_length'][:].data.T

    # Construct file patterns
    jobids = np.arange(1, njobs+1)

    resdir = 'RUN/output_{:03d}/'
    respattern = os.path.join(resdir, '{}.npy')
    aggpattern = '{exp}_{}.npy'.format('{}', exp=exp)

    all_ff = np.zeros((len(nodes)*365, njobs))
    all_channel_frac = np.zeros((len(fluxgate_positions), njobs))
    all_channel_length = np.zeros((len(R_thresholds), njobs))
    all_transit_time = np.zeros((len(fluxgate_positions), njobs))
    for i,jobid in enumerate(jobids):
        print('Job %d' % jobid)
        ff = np.load(respattern.format(jobid, 'ff'))
        all_ff[:, i] = ff.flatten()

        Q = np.load(respattern.format((jobid), 'Q'))
        S = np.load(respattern.format((jobid), 'S'))
        vx = np.load(respattern.format((jobid), 'vx'))/365/86400
        hs = np.load(respattern.format((jobid), 'h_s'))
        q = np.abs(vx*hs)
        
        """
        # Fraction of channelized discharge
        channel_discharge_timeseries = definitions.channel_discharge(nodes, connect_edge, 
            np.abs(Q), fluxgate_positions)
        sheet_discharge_timeseries = definitions.sheet_discharge(nodes,
            q, fluxgate_positions)

        channel_discharge = np.sum(channel_discharge_timeseries, axis=1)
        sheet_discharge = np.sum(sheet_discharge_timeseries, axis=1)
        channel_frac = channel_discharge/(channel_discharge + sheet_discharge)
        # channel_frac = channel_discharge
        all_channel_frac[:, i] = channel_frac

        # Channel network length
        channel_length_ts = definitions.channel_network_length(edge_length,
            S, S_thresholds)
        channel_length = np.max(channel_length_ts, axis=1)/1e3
        all_channel_length[:, i] = channel_length

        # Sheet transit time
        melt_start = 154
        melt_end   = 266

        T = definitions.sheet_transit_time(nodes, np.abs(vx), 
            fluxgate_positions)
        T_meltseason = np.mean(T[:, melt_start:melt_end], axis=1)/365/86400
        T_winter = np.mean(T[:, melt_start-30:melt_start-15], axis=1)/365/86400
        T_mean = np.mean(T, axis=1)/365/86400
        all_transit_time[:, i] = T_mean
    """
    np.save(aggpattern.format('ff'), all_ff)
    #np.save(aggpattern.format('channel_frac'), all_channel_frac)
    #np.save(aggpattern.format('channel_length'), all_channel_length)
    #np.save(aggpattern.format('transit_time'), all_transit_time)


def main():
    """
    Command-line interface to collect simulation outputs
    """
    desc = 'Collect simulation outputs'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('version', help='"matlab" or "issm" GlaDS')
    parser.add_argument('conf_file', help='Path to experiment config file')
    parser.add_argument('njobs', help='Number of jobs', type=int)
    args = parser.parse_args()

    if args.version not in ['matlab', 'issm']:
        raise ValueError('version must be one of "matlab" or "issm"')
    elif args.version=='matlab':
        raise NotImplementedError('"matlab" version is not implemented')

    if not os.path.exists(args.conf_file):
        raise OSError('Configuration file "{}" does not exist'.format(args.conf_file))
    
    path, name = os.path.split(args.conf_file)
    if path:
        abspath = os.path.abspath(path)
        sys.path.append(abspath)
    module, ext = os.path.splitext(name)
    config = importlib.import_module(module)
    if args.version=='issm':
        collect_issm_results(args.njobs, config.exp, mesh=config.mesh)
    return

if __name__=='__main__':
    main()
