import numpy as np
import os
import re
from netCDF4 import Dataset

def get_fluxnet_obs(self, site='US-UMB',tstep='monthly',ystart=-1,yend=9999,fluxnet_var='GPP', \
  myobsdir='', valid_months=None, time_average=1):
  
  # Ensure valid_months is a list of integers
  if valid_months is None:
      valid_months = list(range(1, 13))  # [1,2,3,4,5,6,7,8,9,10,11,12]
  # Convert and validate
  valid_months = [int(m) for m in valid_months if 1 <= int(m) <= 12]
  if not valid_months:
      raise ValueError("No valid months provided. Months must be integers between 1 and 12.")

  # Validate time_average parameter
  time_average = int(time_average)
  if time_average < 1:
      time_average = 1

  vars_elm     = ['NEE',                 'NEP',                  'FPSN',           'GPP',           'ER',              'EFLX_LH_TOT','FSH',      'TBOT',    'FSDS',      'WS',  'RAIN', 'VPD', 'SR']
  vars_fluxnet = ['NEE_CUT_REF',         'NEE_CUT_REF',          'GPP_NT_CUT_REF', 'GPP_NT_CUT_REF','RECO_NT_CUT_REF','LE_F_MDS',   'H_F_MDS',  'TA_F_MDS','SW_IN_F_MDS','WS_F','P_F', 'VPD_F_MDS', 'SR_mean']
  vars_unc     = ['NEE_CUT_REF_JOINTUNC','NEE_CUT_REF_JOINTUNC', 'GPP_NT_CUT_SE',  'GPP_NT_CUT_SE', 'RECO_NT_CUT_SE', 'LE_RANDUNC', 'H_RANDUNC','NA',      'NA',        'NA',  'NA', 'NA', 'SR_sd']
  vars_qc      = ['NEE_CUT_REF_QC',      'NEE_CUT_REF_QC', 'NEE_CUT_REF_QC', 'NEE_CUT_REF_QC','NEE_CUT_REF_QC',  'LE_F_MDS_QC', 'H_F_MDS_QC','TA_F_MDS_QC','SW_IN_F_MDS_QC','WS_F_QC','P_F_QC','VPD_F_MDS_QC','WS_F_QC']

  for v in range(0,len(vars_elm)):
      if fluxnet_var == vars_elm[v]:
          vnum = v

  ndaysm = [31,28,31,30,31,30,31,31,30,31,30,31]
  if (tstep == 'monthly'):
    nstep = 12
  elif (tstep == 'daily'):
    nstep = 365

  # ---------------- 'CalLmip' style file processing -------------------------------
  # read the FLUXNET2015 NetCDF aggregated daily file instead of CSVs.
  if 'callmip' in myobsdir.lower():
    # search possible locations for the netcdf file
    search_dirs = [myobsdir, os.path.join(myobsdir, tstep)]
    ncfile_path = None
    for d in search_dirs:
      try:
        for f in os.listdir(d):
          fname = f.lower()
          if fname.startswith(site.lower() + '_daily_aggregated_') and fname.endswith('_fluxnet2015_flux.nc'):
            ncfile_path = os.path.join(d, f)
            break
      except Exception:
        continue
      if ncfile_path is not None:
        break

    if ncfile_path is None:
      raise FileNotFoundError(f"No FLUXNET2015 netCDF file found for site {site} in {myobsdir}")

    print('Reading CalLMIP observations from: ' + ncfile_path)
    ds = Dataset(ncfile_path, 'r')

    # mapping from internal vars_elm to variables in the CALLMIP netcdf
    nc_var_map = {
      'NEE': ('NEE_daily', 'NEE_uc_daily'),
      'NEP': ('NEE_daily', 'NEE_uc_daily'),
      'EFLX_LH_TOT': ('Qle_daily', 'Qle_uc_daily'),
      'FSH': ('Qh_daily', 'Qh_uc_daily')
    }

    # ensure vnum was set above
    try:
      vnum
    except NameError:
      for v in range(0, len(vars_elm)):
        if fluxnet_var == vars_elm[v]:
          vnum = v

    varkey = vars_elm[vnum]
    if varkey in nc_var_map:
      var_name, var_err_name = nc_var_map[varkey]
      if var_name in ds.variables:
        obs_arr = np.array(ds.variables[var_name][:]).astype(float)
      else:
        obs_arr = np.full(0, -9999.0)
      if var_err_name in ds.variables:
        obs_err_arr = np.array(ds.variables[var_err_name][:]).astype(float)
      else:
        obs_err_arr = np.full(obs_arr.shape, -9999.0)
    else:
      # variable not available in netcdf mapping
      obs_arr = np.full(0, -9999.0)
      obs_err_arr = np.full(0, -9999.0)

    # replace nan with -9999 and ensure 1D array
    if obs_arr.size > 0:
      obs_arr = np.where(np.isnan(obs_arr), -9999.0, obs_arr).ravel()
      obs_err_arr = np.where(np.isnan(obs_err_arr), -9999.0, obs_err_arr).ravel()
      # Replace extremely large fill values (e.g., > 1e10) with missing flag -9999
      obs_arr[obs_arr > 1e10] = -9999.0
      if (fluxnet_var == 'NEP'):
          obs_arr[obs_arr > -9000] = obs_arr[obs_arr > -9000]*-1.0
      obs_err_arr[obs_err_arr > 1e10] = -9999.0
    else:
      obs_arr = np.array([])
      obs_err_arr = np.array([])

    # Parse years from filename (expect pattern _YYYY-YYYY_)
    basename = os.path.basename(ncfile_path)
    m = re.search(r'_(\d{4})-(\d{4})_', basename)
    if m:
      file_ystart = int(m.group(1))
      file_yend = int(m.group(2))
    else:
      # fallback: try to find any 4digit-4digit pattern
      m2 = re.search(r'(\d{4})-(\d{4})', basename)
      if m2:
        file_ystart = int(m2.group(1))
        file_yend = int(m2.group(2))
      else:
        # unknown years in filename; assume full span in array if possible
        file_ystart = None
        file_yend = None

    # If file contains year info, select arrays for requested ystart/yend
    if file_ystart is not None and file_yend is not None and obs_arr.size > 0:
      # default requested years: use file's range if caller didn't specify
      if (ystart <= 0 and yend >= 9000):
        req_ystart = file_ystart
        req_yend = file_yend
      else:
        req_ystart = max(ystart, file_ystart)
        req_yend = min(yend, file_yend)

      if req_ystart > req_yend:
        raise ValueError(f"Requested years {ystart}-{yend} are outside file range {file_ystart}-{file_yend}")

      # Build full-date index for the file (includes leap days) and select requested years
      full_start = np.datetime64(f"{file_ystart}-01-01")
      full_end = np.datetime64(f"{file_yend+1}-01-01")
      dates_full = np.arange(full_start, full_end, np.timedelta64(1, 'D'))

      sel_start = np.datetime64(f"{req_ystart}-01-01")
      sel_end = np.datetime64(f"{req_yend+1}-01-01")
      mask_years = (dates_full >= sel_start) & (dates_full < sel_end)

      obs_sel = obs_arr[mask_years]
      err_sel = obs_err_arr[mask_years]
      dates_sel = dates_full[mask_years]

      # Omit leap days (Feb 29)
      date_strs = dates_sel.astype('datetime64[D]').astype(str)
      # numpy.char.substr is not available; use Python slicing per-element
      md = np.array([s[5:10] for s in date_strs])  # 'MM-DD'
      non_leap_mask = (md != '02-29')
      obs_arr = obs_sel[non_leap_mask]
      obs_err_arr = err_sel[non_leap_mask]

      # update ystart/yend to the actual returned range for downstream logic
      ystart = req_ystart
      yend = req_yend

    ds.close()

    # assign to self and apply same post-processing as CSV branch
    self.obs[vars_elm[vnum]] = obs_arr
    self.obs_err[vars_elm[vnum]] = obs_err_arr

    if tstep == 'daily':
      # Shift obs by 1 day (Model timestamp represents previous day)
      if self.obs[vars_elm[vnum]].size > 0:
        self.obs[vars_elm[vnum]] = np.roll(self.obs[vars_elm[vnum]], 1)
        self.obs_err[vars_elm[vnum]] = np.roll(self.obs_err[vars_elm[vnum]], 1)

        # Mask days not in valid months
        ndays = len(self.obs[vars_elm[vnum]])
        nyears = ndays // 365
        mymask = np.zeros([ndays], bool)
        month_day_start = 0
        month_day_end = ndaysm[0]
        for m in range(1, 13):
          if (m in valid_months):
            for y in range(0, nyears):
              for day in range(month_day_start, month_day_end):
                mymask[y * 365 + day] = True
          month_day_start = month_day_start + ndaysm[m - 1]
          month_day_end = month_day_start + ndaysm[min(m, 11)]
        self.obs[vars_elm[vnum]][~mymask] = -9999
        self.obs_err[vars_elm[vnum]][~mymask] = -9999

        # ADD TIME AVERAGING FOR DAILY DATA (if requested)
        if time_average > 1:
          print(f"Applying {time_average}-day averaging to daily observations")

          # take care of misalignment between output and obs by padding
          min_start_year = min(self.postproc_startyear, file_ystart)
          max_end_year = max(self.postproc_endyear, file_yend)

          daily_obs = np.full((max_end_year-min_start_year+1)*365, -9999.0)
          daily_obs[(file_ystart-min_start_year)*365:(file_yend-min_start_year+1)*365] = self.obs[vars_elm[vnum]].copy()

          daily_obs_err = np.full((max_end_year-min_start_year+1)*365, -9999.0)
          daily_obs_err[(file_ystart-min_start_year)*365:(file_yend-min_start_year+1)*365] = self.obs_err[vars_elm[vnum]].copy()

          n_periods = len(daily_obs) // time_average
          averaged_obs = np.full(n_periods, -9999.0)
          averaged_obs_err = np.full(n_periods, -9999.0)
          for i in range(n_periods):
            start_idx = i * time_average
            end_idx = start_idx + time_average
            obs_chunk = daily_obs[start_idx:end_idx]
            err_chunk = daily_obs_err[start_idx:end_idx]
            valid_obs = obs_chunk[obs_chunk > -9999]
            valid_err = err_chunk[err_chunk > -9999]
            if len(valid_obs) > 0:
              averaged_obs[i] = np.mean(valid_obs)
              if len(valid_err) > 0:
                if len(valid_err) == 1:
                  averaged_obs_err[i] = valid_err[0]
                else:
                  averaged_obs_err[i] = np.sqrt(np.mean(valid_err ** 2)) / np.sqrt(len(valid_err))
              else:
                averaged_obs_err[i] = -9999
          self.obs[vars_elm[vnum]] = averaged_obs
          self.obs_err[vars_elm[vnum]] = averaged_obs_err

          return min_start_year, max_end_year

    return file_ystart, file_yend
#-----------------------end of CallMIP netCDF branch-----------------------

#------------Processing for regular FLUXNET CSV files (if not CALLMIP netCDF)-----------
  #myvars = ['TBOT','FSDS','WS','RAIN','VPD','NEE','GPP','ER','EFLX_LH_TOT','FSH']
  #myvars   = ['FPSN','FSH','EFLX_LH_TOT']

  myobsfiles = os.listdir(myobsdir+'/'+tstep+'/')

  for f in myobsfiles:
   if site in f and '.csv' in f and 'FULLSET' in f:
    myobsfile = myobsdir+'/'+tstep+'/'+f
    if (os.path.exists(myobsfile)):
        print('Observation file: '+myobsfile)
        thisrow=0
        myobs_input = open(myobsfile)
        if (ystart <= 0 and yend >= 9000):
          print ('Getting start and end year information from observation file')
          for j in myobs_input:
            if thisrow == 1:
                ystart = int(j[0:4])+1
            elif (thisrow > 1):
                yend = int(j[0:4])
            thisrow=thisrow+1
          myobs_input.close
          nrows = thisrow-1

        print(ystart, yend)
        nrows = (yend-ystart+1)*nstep
        myobs = np.zeros([nrows],float)
        myobs_err = np.zeros([nrows],float)
        myobs_in = open(myobsfile)
        thisrow=0
        thisob=0
        for j in myobs_in:
            if (thisrow == 0):
                header = j.split(',')
            else:
                myvals = j.split(',')
                thiscol=0
                if int(myvals[0][0:4]) >= ystart and int(myvals[0][0:4]) <= yend:
                  isgood=False
                  for h in header:
                    if (h.strip() == vars_fluxnet[vnum]):
                      tempob = float(myvals[thiscol])
                    if (h.strip() == vars_unc[vnum]):
                      tempob_err = float(myvals[thiscol])
                    if (h.strip() == vars_qc[vnum] and vars_qc[vnum] != 'NA'):
                      #if float(myvals[thiscol]) > 0.8 and int(myvals[0][4:8]) != 229:
                      if int(myvals[0][4:8]) != 229:
                        isgood=True  #only advance if quality flag > 80, not leap day%
                    else:
                      isgood-True
                    thiscol=thiscol+1
                  if (isgood):
                    myobs[thisob]     = tempob
                    if (fluxnet_var == 'NEP'):
                        myobs[thisob]     = tempob*-1.0
                    myobs_err[thisob] = tempob_err
                    if fluxnet_var == 'FPSN' or fluxnet_var == 'GPP':
                       myobs_err[thisob] = max(myobs_err[thisob], 1.0)
                    if fluxnet_var == 'EFLX_LH_TOT':
                       myobs_err[thisob] = max(myobs_err[thisob], 10.0)  
                  else:
                    myobs[thisob] = -9999
                    myobs_err[thisob] = -9999
                  if (int(myvals[0][4:8]) != 229):
                    #only increment if not leap day
                    thisob=thisob+1
            thisrow=thisrow+1
        self.obs[vars_elm[vnum]]=myobs
        self.obs_err[vars_elm[vnum]]=myobs_err
        if (tstep == 'monthly'):
            nmonths = len(self.obs[vars_elm[vnum]])
            nyears = nmonths // 12
            mymask = np.zeros([nmonths],bool)
            for m in valid_months:
              for y in range(0,nyears):
                mymask[y*12+(m-1)] = True
            self.obs[vars_elm[vnum]][~mymask] = -9999
            self.obs_err[vars_elm[vnum]][~mymask] = -9999
        if (tstep == 'daily'):
            #Shift obs by 1 day (Model timestamp repsresents previous day)
            self.obs[vars_elm[vnum]] = np.roll(self.obs[vars_elm[vnum]], 1)
            self.obs_err[vars_elm[vnum]] = np.roll(self.obs_err[vars_elm[vnum]], 1)
            
            #Mask days not in valid months
            ndays = len(self.obs[vars_elm[vnum]]) 
            nyears = ndays // 365
            mymask = np.zeros([ndays],bool)
            month_day_start = 0
            month_day_end = ndaysm[0]
            for m in range(1,13):
              if (m in valid_months):
                for y in range(0,nyears):
                   for day in range(month_day_start, month_day_end):
                        mymask[y*365+day] = True
              month_day_start = month_day_start+ndaysm[m-1]
              month_day_end   = month_day_start+ndaysm[min(m,11)]
            self.obs[vars_elm[vnum]][~mymask] = -9999
            self.obs_err[vars_elm[vnum]][~mymask] = -9999
            
            # ADD TIME AVERAGING FOR DAILY DATA
            if time_average > 1:
                print(f"Applying {time_average}-day averaging to daily observations")
                # Get the original daily data
                daily_obs = self.obs[vars_elm[vnum]].copy()
                daily_obs_err = self.obs_err[vars_elm[vnum]].copy()
                
                # Calculate number of averaged periods
                n_periods = len(daily_obs) // time_average
                # Initialize averaged arrays
                averaged_obs = np.full(n_periods, -9999.0)
                averaged_obs_err = np.full(n_periods, -9999.0)
                
                for i in range(n_periods):
                    start_idx = i * time_average
                    end_idx = start_idx + time_average
                    
                    # Get the chunk of data
                    obs_chunk = daily_obs[start_idx:end_idx]
                    err_chunk = daily_obs_err[start_idx:end_idx]
                    
                    # Only average if we have valid data (not all -9999)
                    valid_obs = obs_chunk[obs_chunk > -9999]
                    valid_err = err_chunk[err_chunk > -9999]
                    
                    if len(valid_obs) > 0:
                        # Calculate mean of valid observations
                        averaged_obs[i] = np.mean(valid_obs)
                        
                        # For errors, use root-mean-square if we have multiple valid values
                        if len(valid_err) > 0:
                            if len(valid_err) == 1:
                                averaged_obs_err[i] = valid_err[0]
                            else:
                                # RMS error for averaged data
                                averaged_obs_err[i] = np.sqrt(np.mean(valid_err**2)) / np.sqrt(len(valid_err))
                        else:
                            averaged_obs_err[i] = -9999
                    # If no valid data, leave as -9999 (already initialized)
                
                # Replace the daily data with averaged data
                self.obs[vars_elm[vnum]] = averaged_obs
                self.obs_err[vars_elm[vnum]] = averaged_obs_err
                
                print(f"Averaged from {len(daily_obs)} daily values to {len(averaged_obs)} {time_average}-day values")


