
"""
Plotting some trajectories from merging vehicles from NGSIM
"""
import havsim
import havsim.plotting as hp
import numpy as np
import matplotlib.pyplot as plt

# meas, platooninfo = havsim.calibration.algs.makeplatoonlist(data, 1, False)

#%%
mergelist = []
for i in platooninfo.keys():
    t_nstar, t_n = platooninfo[i][:2]
    if meas[i][0,7] == 7:
        if meas[i][t_n-t_nstar,7]==6:
            mergelist.append(i)

lane6vehlist = []
for i in platooninfo.keys():
    if 6 in np.unique(meas[i][:,7]):
        lane6vehlist.append(i)
sortedvehlist = havsim.calibration.platoon_formation.sortveh(6, meas, lane6vehlist)

#%%
hp.animatevhd(meas, None, platooninfo, sortedvehlist[50:52], interval = 30, lane = 6)

#%%
hp.animatetraj(meas, platooninfo, platoon = sortedvehlist)

#%%
veh = mergelist[5]
hp.plotvhd(meas, None, platooninfo, [mergelist[5]], draw_arrow = True, plot_color_line = True)

plt.figure()
t_nstar, t_n = platooninfo[veh][:2]
plt.plot(meas[veh][0:t_n-t_nstar,3])

#%%
hp.plotflows(meas,[[670,870],[1200,1400]],[0,10*60*14.5],30*10, method = 'area', space_units=3280.84)
hp.plotflows(meas,[[670,770]],[0,10*60*14.5],30*10,lane = 6, method = 'area', space_units=3280.84)
#%%
hp.platoonplot(meas, None, platooninfo, lane = 5, opacity = 0)
hp.platoonplot(meas, None, platooninfo, lane = 6, opacity = 0)
hp.platoonplot(meas, None, platooninfo, lane = 7, opacity = 0)
#%%
hp.plotspacetime(meas, platooninfo, lane = 5)
hp.plotspacetime(meas, platooninfo, lane = 6)
hp.plotspacetime(meas, platooninfo, lane = 7)