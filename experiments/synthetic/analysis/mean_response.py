
import argparse

import os
import sys

import numpy as np
import matplotlib
matplotlib.rc('font', size=8)
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import cmocean
from scipy import stats

from sepia.SepiaModel import SepiaModel
from sepia.SepiaData import SepiaData
from sepia.SepiaPredict import SepiaEmulatorPrediction

from src import utils
# import src
import src.model


def init_model(t_std, y_sim, exp_name, data_dir='data/'):
    """
    Initialize SepiaData and SepiaModel instances for scalar variable

    Parameters
    ----------
    t_std : (n simulations,)
            Standardized simulation design matrix
    
    exp_name : str
               Name for simulation, used to generate file paths
    
    Returns:
    --------
    SepiaData, SepiaModel
    """
    data = SepiaData(t_sim=t_std, y_sim=y_sim)
    data.transform_xt()
    data.standardize_y()
    model = SepiaModel(data)
    return data, model

def compute_mean_response_profiles(config):
    # Load data and initialize model

    scalar_defs = ['channel_frac', 'log_transit_time', 'channel_length']
    thresholds = [ np.array([5, 10, 15, 20, 25, 30, -1]),
                    np.array([5, 10, 15, 20, 25, 30, -1]),
                    np.array([0.5, 1.])
    ]
    labels = ['{:.0f} km', '{:.0f} km', '{:.1f} m']
    xlabels = [ 'Fluxgate position (km)',
                'Fluxgate position (km)',
                'Channel radius (m)',
    ]
    ylabels = ['Channel fraction', 'log Transit time (a)', 'Channel length (km)']
    ylims = [[0, 1], [-1.5, 0.25], [0, 1500]]

    t_std = np.loadtxt(config.X_standard, delimiter=',', skiprows=1,
        comments=None)
    t_names = np.loadtxt(config.X_physical, delimiter=',', max_rows=1,
        dtype=str, comments=None)
    t_names= [tn.strip('#') for tn in t_names]
    t_phys = np.loadtxt(config.X_physical, delimiter=',', skiprows=1)
    t_log = np.loadtxt(config.X_log, delimiter=',', skiprows=1)
    t_std = t_std[:config.m, :]
    t_phys = t_phys[:config.m, :]

    # Prediction points
    ntarget = 11
    nintegrate = 20
    n_dim = t_std.shape[1]
    sampler = stats.qmc.LatinHypercube(n_dim-1, 
        optimization='random-cd', scramble=False, seed=20240418)
    Xintegrate = sampler.random(n=nintegrate)
    Xpred = np.zeros((ntarget*nintegrate, n_dim))
    Xpred[:, 1:] = np.tile(Xintegrate, (ntarget, 1))
    xtarget = np.linspace(0, 1, ntarget)
    Xpred[:, 0]  = np.kron(xtarget, np.ones(nintegrate))

    for k in range(len(scalar_defs)):
        print(scalar_defs[k])
        data_dir = os.path.join('data/scalars')
        n_defs = len(thresholds[k])
        Y_integrated_mean = np.zeros((n_defs, n_dim, ntarget))
        for j in range(len(thresholds[k])):
            print('Threshold {}/{}'.format(j+1, n_defs))

            Y_fname = os.path.join(config.sim_dir, 
                '{exp}_{qoi}.npy'.format(exp=config.exp, qoi=scalar_defs[k]))
            y_sim = np.load(Y_fname).T[:config.m]

            # Arbitrarily take one of the fluxgate positions
            y_sim = (np.vstack(y_sim[:, j]))

            data,model = init_model(t_std, y_sim, config.exp, data_dir='data/')
            model_file = os.path.join(data_dir, 
                '{exp}_{qoi}_n{m}_t{threshold}'.format( exp=config.exp,
                    qoi=scalar_defs[k], m=config.m, threshold=j))
            model.restore_model_info(model_file)
            samples = model.get_samples(nburn=256, numsamples=16)


            for d_index in range(n_dim):
                dnums = np.arange(n_dim)
                dnums = dnums + d_index
                dnums = np.mod(dnums, n_dim)
                # dnums = np.mod(dnums-d_index, n_dim)
                xpred = np.zeros(Xpred.shape, dtype=np.float32)
                xpred[:, d_index] = Xpred[:, 0]
                xpred[:, dnums[1:]] = Xpred[:, 1:]

                GPpred = SepiaEmulatorPrediction(model=model, t_pred=xpred, samples=samples)
                GPpred.w = GPpred.w.astype(np.float32)
                Ypred = GPpred.get_y()
                Ymean = np.mean(Ypred, axis=0).flatten()

                Yint = np.zeros(xtarget.shape)
                for i in range(ntarget):
                    start = i*nintegrate
                    end = (i+1)*nintegrate
                    Yint[i] = np.mean(Ymean[start:end])
                
                # Y_integrated_mean = np.zeros((n_defs, n_dim, ntarget))
                Y_integrated_mean[j, d_index, :] = Yint
        data_dir = 'data/scalars'
        data_file = os.path.join('data/scalars/{}_{}_n{}_mean_response.npy'.format(
            config.exp, scalar_defs[k], config.m)
        )
        np.save(data_file, Y_integrated_mean)

    return


def plot_mean_response_profiles(config):
    # Load data and initialize model
    scalar_defs = ['channel_frac', 'log_transit_time', 'channel_length']
    thresholds = [ np.array([5, 10, 15, 20, 25, 30, -1]),
                    np.array([5, 10, 15, 20, 25, 30, -1]),
                    np.array([0.5, 1.])
    ]
    labels = ['{:.0f} km', '{:.0f} km', '{:.1f} m']
    xlabels = [ 'Fluxgate position (km)',
                'Fluxgate position (km)',
                'Channel radius (m)',
    ]
    ylabels = [r'$f_Q$', r'$\log T_{\rm{s}}$ (a)', r'$L_{\rm{c}}$ (km)']
    ylims = [[0, 1], [-1.5, 0.25], [0, 1500]]
    xlims = [
        [0, 1],
        [0, 0.5],
        [0, 1],
        [0, 100],
        [0, 100],
        [0, 1e-23],
        [0, 2e-3],
        [0, 5.5e-4]
    ]
    xticks = [
        [0, 0.25, 0.5, 0.75, 1],
        [0, 0.125, 0.25, 0.375, 0.5],
        [0, 0.25, 0.5, 0.75, 1],
        [0, 25, 50, 75, 100],
        [0, 25, 50, 75, 100],
        [0, 2.5e-24, 5e-24, 7.5e-24, 10e-24],
        [0, 5e-4, 1e-3, 1.5e-3, 2e-3],
        [0, 1e-4, 2e-4, 3e-4, 4e-4, 5e-4]
    ]
    # print(xticks)
    multipliers = np.array([1, 1, 1, 1, 1, 1e24, 1.e4, 1.e4])
    labels = ['{:.0f} km', '{:.0f} km', '{:.1f} m']


    t_std = np.loadtxt(config.X_standard, delimiter=',', skiprows=1,
        comments=None)
    n_dim = t_std.shape[1]
    t_names = np.loadtxt(config.X_physical, delimiter=',', max_rows=1,
        dtype=str, comments=None)
    t_names= [tn.strip('#') for tn in t_names]
    t_phys = np.loadtxt(config.X_physical, delimiter=',', skiprows=1)
    t_log = np.loadtxt(config.X_log, delimiter=',', skiprows=1)
    t_std = t_std[:config.m, :]
    t_phys = t_phys[:config.m, :]

    # Prediction points
    fig_dir = os.path.join(config.figures, 'scalars')
    # fig, axs = plt.subplots(ncols=4, nrows=2, figsize=(8, 6))
    fig = plt.figure(figsize=(6, 8.5))
    gs = GridSpec(8, 3, bottom=0.125, left=0.075, right=0.97, top=0.975,
        hspace=0.75, wspace=0.25)
    axs = np.array([[fig.add_subplot(gs[i,j]) for j in range(3)] 
        for i in range(8)])
    

    for k in range(len(scalar_defs)):
    # for k in range(1):
        
        n_defs = len(thresholds[k])

        if thresholds[k][-1]==-1:
            cticks = np.zeros(len(thresholds[k]))
            cticks[:-1] = np.linspace(0.15, 0.85, len(thresholds[k])-1)
            colors = cmocean.cm.delta(cticks)
            colors[-1] = [0.4, 0.4, 0.4, 1.]
            cticks = cticks[:-1]
        else:
            cticks = np.linspace(0.15, 0.85, len(thresholds[k]))
            colors = cmocean.cm.delta(cticks)
        data_file = os.path.join('data/scalars/{}_{}_n{}_mean_response.npy'.format(
            config.exp, scalar_defs[k], config.m)
        )
        print(data_file)
        Y_integrated_mean = np.load(data_file)
        n_int = Y_integrated_mean.shape[-1]
        x_int = np.linspace(0, 1, n_int)
        print(Y_integrated_mean.shape)
        for j in range(n_dim):
            theta_bounds = config.theta_bounds
            x_int_phys = 10**(theta_bounds[j][0] + (theta_bounds[j][1] - theta_bounds[j][0])*x_int)
            ax = axs[j,k]
            for tindex in range(n_defs):
                label = labels[k].format(thresholds[k][tindex])
                if thresholds[k][tindex]==-1:
                    label = 'Mean'
                ax.plot(x_int_phys, Y_integrated_mean[tindex, j, :].T, color=colors[tindex],
                    label=label)
            ax.set_ylim(ylims[k])
            ax.grid(linestyle=':')
            ax.spines[['right', 'top']].set_visible(False)
            xlabel = t_names[j] if multipliers[j]==1 else t_names[j] + r' $\times 10^{{{:.0f}}}$'.format(np.log10(multipliers[j]))
            ax.set_xlabel(xlabel)
            ax.set_facecolor('none')
            ax.set_xlim(xlims[j])
            xticklabels = np.array(xticks[j])*multipliers[j]
            ax.set_xticks(xticks[j], xticklabels.round(decimals=2).astype(str))

    axs[-1,0].legend(bbox_to_anchor=(0, -1.1, 2.5, 0.5), loc='upper center', 
            ncols=4, frameon=False, title='Fluxgate position')

    axs[-1,2].legend(bbox_to_anchor=(0, -1.1, 1, 0.5), loc='upper center', 
            ncols=1, frameon=False, title='Channel radius')
    
    for i,ax in enumerate(axs[0]):
        ax.set_title(ylabels[i], fontsize=8)
    # for ax in axs[:-1, :].flat:
    #     ax.set_xticklabels([])
    fig.savefig(os.path.join(config.figures, 'scalar_response_profiles.png'), dpi=400)
    fig.savefig(os.path.join(config.figures, 'scalar_response_profiles.pdf'))
    return


def main():
    """
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('train_config')
    parser.add_argument('--recompute', '-r', action='store_true')
    args = parser.parse_args()
    train_config = utils.import_config(args.train_config)

    if args.recompute:
        compute_mean_response_profiles(train_config)
    
    plot_mean_response_profiles(train_config)

if __name__=='__main__':
    main()