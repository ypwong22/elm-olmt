"""
Populate the obs and obs_err of each site. Do multi-site optimization
  using the first site as the leading site.

Based on MCMC.py
"""
import numpy as np
from scipy.stats import norm
import model_surrogate as models
import os, math, random
import matplotlib
matplotlib.use('Agg')
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from optparse import OptionParser
import multiprocessing
import emcee
import time
import corner
import netCDF4 as nc
import shutil
import pickle

import model_ELM # auto-updated get_flux_obs
from model_ELM.MCMC import sample_from_prior, log_posterior, estimate_burnin

pft = 7
if pft == 2:
  site_list = ['CA-Qfo', 'CH-Dav', 'FI-Hyy', 'RU-Fyo', 'US-NR1']
  prefix_list = ['20260812','20260812','20260812','20260812','20260812']
  base_case = '20260812_CA-Qfo_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC
elif pft == 1:
  site_list = ['DE-Tha', 'IT-Lav', 'NL-Loo']
  prefix_list = ['20260806', '20260806', '20260806']
  base_case = '20260806_DE-Tha_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC
elif pft == 5:
  site_list = ['FR-Pue']
  prefix_list = ['20260809']
  base_case = '20260809_FR-Pue_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC
elif pft == 7:
  site_list = ['DE-Hai', 'DK-Sor', 'US-MMS', 'US-SRM']
  prefix_list = ['20260809','20260809','20260809','20260809']
  base_case = '20260809_DE-Hai_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC
elif pft == 9:
  site_list = ['IT-Noe']
  prefix_list = ['20260811']
  base_case = '20260811_IT-Noe_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC
elif pft == 14:
  site_list = ['US-SRG', 'US-Wkg']
  prefix_list = ['20260811','20260811']
  base_case = '20260811_US-SRG_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC
elif pft == 10: 
  site_list = ['US-Whs']
  prefix_list = ['20260812']
  base_case = '20260812_US-Whs_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC
elif pft == 13: 
  site_list = ['US-Var','DE-Gri','IT-MBo','US-Ton']
  prefix_list = ['20260812','20260812','20260812','20260812']
  base_case = '20260812_US-Var_ICB20TRCNPRDCTCBC_Prior' # use the first case to drive the MCMC


# debug case
#site_list = ['US-MMS']
#prefix_list = ['20260809']
#base_case = '20260809_US-MMS_ICB20TRCNPRDCTCBC_Prior'
#site_list = ['US-Var']
#prefix_list = ['20260812']
#base_case = '20260812_US-Var_ICB20TRCNPRDCTCBC_Prior'

output_years = range(1994, 2018)
fluxnet_vars = ['NEE','EFLX_LH_TOT','FSH']

#----------------------------------------------------------------------
# Populate the obs and obs_err
#----------------------------------------------------------------------
myobsdir = os.path.join(os.environ['SHARDIR'], 'CalLMIP', 'data', 'Phase1', 'Data', 'Phase1b')
for site, prefix in zip(site_list, prefix_list):
    myfile=open('pklfiles/'+prefix+'_'+site+'_ICB20TRCNPRDCTCBC_Prior.pkl','rb')
    mycase=pickle.load(myfile)

    for vv in fluxnet_vars:
      file_ystart, file_yend = mycase.get_fluxnet_obs(site, tstep='daily',
        myobsdir=myobsdir, time_average=10, fluxnet_var=vv)

    mycase.create_pkl(outdir=mycase.OLMTdir+'/pklfiles/')


#run MCMC
myfile=open('pklfiles/'+base_case+'.pkl','rb')
mycase=pickle.load(myfile)
mycase.all_sites = site_list

obs_mcmc = fluxnet_vars
mycase.nobs_vars = len(obs_mcmc)
nwalkers = max(24, (mycase.nparms_ensemble+mycase.nobs_vars)*2) # increasing the walkers do not matter

print(f"Running multisite MCMC for {len(mycase.all_sites)} sites: {mycase.all_sites}")
mycase.MCMC(obs_mcmc, nwalkers=nwalkers, nsteps=10000, multisite=True, multiprefix=prefix_list)

#Save postprocessed output
mycase.create_pkl(outdir=mycase.OLMTdir+'/pklfiles/')
