
"""
calibration related functions which define algorithms (such as custom optimization algorithms or platoon formation algorithms)

@author: rlk268@cornell.edu
"""
import numpy as np 
from . import helper
import networkx as nx
import copy 
import scipy.stats as ss

def makefollowerchain2(leadID, dataset, n=1, picklane = 0 ):
	
    #this is the older version. This one will end up selecting more "whole" trajectories (i.e. those without LC). See makefollowerchain for documentation 
    #but will also sometimes give gaps in the trajectories. 
    #the newer version will get EVERY vehicle in the lane, but perhaps not in a great order, and certain vehicles might only be simulated a very short time. 
    
    #note that this isn't the same as makeplatooninfo: main differences are that followers each have only 1 leader, all vehicles are in the same lane
    #this function is good if you want to grab a platoon with no lane changing
    #it should be possible to use any "plots" or "calibration" functions on the output even though it is slightly different than makeplatooninfo. 

    meas = {} #this is where the measurements (from data) go 
    followerchain = {} #helpful information about the platoon and the followers

    
    lead = dataset[dataset[:,0]==leadID] #get all data for lead vehicle
    lanes, lanes_count = np.unique(lead[:,7], False, False, True) #get all lanes lead vehicle has been in. you can specify a lane manually, default to most traveled lane
    if picklane == 0: #default to most traveled lane if no lane given 
        picklane = lanes[np.argmin(-lanes_count)]
    lead = lead[lead[:,7]==picklane] #get all lead trajectory data for specific lane 
    
    lead, _= helper.checksequential(lead) #we only want sequential data for the lead trajectory i.e. don't want leader to change lanes and then change back to first lane 
    leadID = lead[0,0]
    #now we have sequential measurments for the leadID in the lane picklane. we want to get followers and form a platoon of size n
    followerchain[leadID] = [int(lead[0,1]), int(lead[0,1]), int(lead[0,1]), int(lead[-1,1]), -1, -1,-1, []] #we give leader a followerchain entry as well. unused entries are set equal to -1 
    
    for i in range(n):
        meas[leadID] = lead #add data of lead vehicle
        followers, followers_count = np.unique(lead[:,5], False, False, True) #get all followers for specific leader in specific lane 
        pickfollower = followers[np.argmin(-followers_count)] #next follower is whichever follower has most observations 
        fullfollower = dataset[np.logical_and(dataset[:,0]==pickfollower, dataset[:,7]==picklane)] #get all measurements for follower in current lane 
        curfollower = fullfollower[fullfollower[:,4]==leadID] #get all measurements for follower with specific leader 
        
        followerchain[leadID][-1].append(pickfollower) #append the new follower to the entry of its leader so we can get the platoon order if needed 
        
        #if curfollower is empty it means we couldn't find a follower 
        testshape = curfollower.shape

        if testshape[0] ==0:
            print('warning: empty follower')
            return meas, followerchain
        
    
        #need to check all measurements are sequential
        curfollower, _ = helper.checksequential(curfollower) #curfollower is where we have the lead measurements for follower 
        extrafollower = fullfollower[fullfollower[:,1]>curfollower[-1,1]] #extrafollower is where all the "extra" measurements for follower go - no leader here
        extrafollower, _ = helper.checksequential(extrafollower, 1, True)
        
        testshape1 = extrafollower.shape #this prevents index error which occurs when extrafollower is empty
        if testshape1[0]==0: 
            T_n = curfollower[-1,1]
        else: 
            T_n = extrafollower[-1,1]
        
        if curfollower[-1,1]< lead[-1,1]:
            print('warning: follower trajectory not available for full lead trajectory') #you will get this print out when you use makefollowerchain on data with lane changing.
            #the print out doesn't mean anything has gone wrong, it is just to let you know that for certain vehicles in the platoon, those vehicles can't be simulated
            #for as long as a time as they should, essentially because they, or their leaders, change lanes 
            
        followerchain[pickfollower]= [int(fullfollower[0,1]), int(curfollower[0,1]), int(curfollower[-1,1]), int(T_n), [leadID], curfollower[0,2], curfollower[0,3], []]
        
        #update iteration 
#        lead = np.append(curfollower,extrafollower, axis = 0)
        lead = fullfollower #this is what lead needs to be to be consistent with the conventions we are using in makeplatooninfo and makeplatoon
        leadID = pickfollower
        
    meas[leadID] = lead #add data of last vehicle
    return meas, followerchain 

def makefollowerchain(leadID, dataset, n=1, picklane = 0 ):
	#	given a lead vehicle, makefollowerchain forms a platoon that we can calibrate. The platoon is formed is such a way that there is no lane changing, 
	#Mainly meant for testing and plotting, you probably want to use makeplatoonlist unless for some reason you don't want to have any lane changing in your calibration 
	
	#input: 
	#    leadID: vehicle ID of leader. this is the first vehicle in the platoon, so the next vehicle will be the follower of this vehicle, and then the vehicle after will be the follower of 
	#    that vehicle, etc. 
	#    
	#    dataset: source of data. it needs to have all the entries that are in dataind for each observation (as well as the vehicle ID and frame ID entries) 
	#    
	#    n = 1: this is how many following vehicles will be in the followerchain. 
	#        
	#    picklane = 0 : laneID for leader (optional). If you give default value of 0, we just give the lane that has the most observations for the leader as the lane to use
	#    
	#output: 
	#    meas: all measurements with vehID as key, values as dataset[dataset==meas.val()] i.e. same format as dataset
	#    This is only for the vehicles in followerchain, and not every single vehicle in the dataset
	#    
	#    followerchain: dictionary with key as vehicle ID
	#    value is array containing information about the platoon and calibration problem 
	#        0 - t_nstar (first recorded time)
	#        1 - t_n (first simulated time)
	#        2 - T_nm1 (last simulated time) (read as T_{n minus 1})
	#        3 - T_n (last recorded time)
	#        4 - leader ID (in an array so that it is consistent with platooninfo)
	#        5 - position IC 
	#        6 - speed IC 
	#        7 - follower ID (in an array)
	
    #this is the newer version of makefollowerchain which always gets all vehicles in the lane, even ones which are only simulated a short time. 
    #however, there is still one thing in this unclear to me which is how it is going to handle the case of a vehicle which is in the lane then merges out of the lane 
    #and then back in at a later time. I think in that case, it only selects the longest continuous trajectory and ignores the other part. 
    #so this edge case you need to be careful with. 
    

    meas = {} #this is where the measurements (from data) go 
    followerchain = {} #helpful information about the platoon and the followers

    
    lead = dataset[dataset[:,0]==leadID] #get all data for lead vehicle
    lanes, lanes_count = np.unique(lead[:,7], False, False, True) #get all lanes lead vehicle has been in. you can specify a lane manually, default to most traveled lane
    if picklane == 0: #default to most traveled lane if no lane given 
        picklane = lanes[np.argmin(-lanes_count)]
    lead = lead[lead[:,7]==picklane] #get all lead trajectory data for specific lane 
    
    lead, _= helper.checksequential(lead) #we only want sequential data for the lead trajectory i.e. don't want leader to change lanes and then change back to first lane 
    leadID = lead[0,0]
    #now we have sequential measurments for the leadID in the lane picklane. we want to get followers and form a platoon of size n
    followerchain[leadID] = [int(lead[0,1]), int(lead[0,1]), int(lead[0,1]), int(lead[-1,1]), -1, -1,-1, []] #we give leader a followerchain entry as well. unused entries are set equal to -1 
   #modification
    backlog = []
    leadlist = []
    i = 1
    
    while i < n:
#        print(i)
#        print(leadlist)
        leadlist.append(leadID)
        meas[leadID] = lead #add data of lead vehicle
        followers, followers_count = np.unique(lead[:,5], False, False, True) #get all followers for specific leader in specific lane 
        #modification
#        if len(backlog) == 0:
#            pickfollower = followers[np.argmin(-followers_count)] #next follower is whichever follower has most observations #before it was just this
#        else: 
#            pickfollower = backlog.pop()
        for j in followers: 
            if j ==0:#don't add 0 
                continue
            elif j in leadlist or j in backlog:
                continue
            backlog.append(j) #add everything to the backlog

        pickfollower = backlog[0] #take out the first thing 
        backlog.remove(pickfollower)
        
            
        fullfollower = dataset[np.logical_and(dataset[:,0]==pickfollower, dataset[:,7]==picklane)] #get all measurements for follower in current lane 
        #need to change this line 
#        curfollower = fullfollower[fullfollower[:,4]==leadID] #get all measurements for follower with specific leader 
        curfollower = []
        for j in range(len(fullfollower)):
            if fullfollower[j,4] in leadlist:
                curfollower = np.append(curfollower,fullfollower[j,:])
        curfollower = np.reshape(curfollower,(int(len(curfollower)/9),9))
        
        
        followerchain[leadID][-1].append(pickfollower) #append the new follower to the entry of its leader so we can get the platoon order if needed 
        #modification
        
        #if curfollower is empty it means we couldn't find a follower 
        testshape = curfollower.shape

        if testshape[0] ==0:
            print('warning: empty follower')
#            return meas, followerchain
            continue
        
    
        #need to check all measurements are sequential
        curfollower, _ = helper.checksequential(curfollower) #curfollower is where we have the lead measurements for follower 
        extrafollower = fullfollower[fullfollower[:,1]>curfollower[-1,1]] #extrafollower is where all the "extra" measurements for follower go - no leader here
        extrafollower, _ = helper.checksequential(extrafollower, 1, True)
        
        testshape1 = extrafollower.shape #this prevents index error which occurs when extrafollower is empty
        if testshape1[0]==0: 
            T_n = curfollower[-1,1]
        else: 
            T_n = extrafollower[-1,1]
        
        if curfollower[-1,1]< lead[-1,1]:
            print('warning: follower trajectory not available for full lead trajectory') #you will get this print out when you use makefollowerchain on data with lane changing.
            #the print out doesn't mean anything has gone wrong, it is just to let you know that for certain vehicles in the platoon, those vehicles can't be simulated
            #for as long as a time as they should, essentially because they, or their leaders, change lanes 
            
        followerchain[pickfollower]= [int(fullfollower[0,1]), int(curfollower[0,1]), int(curfollower[-1,1]), int(T_n), [leadID], curfollower[0,2], curfollower[0,3], []]
        
        #update iteration 
#        lead = np.append(curfollower,extrafollower, axis = 0)
        lead = fullfollower #this is what lead needs to be to be consistent with the conventions we are using in makeplatooninfo and makeplatoon
        leadID = pickfollower
        i += 1
        
    meas[leadID] = lead #add data of last vehicle
    return meas, followerchain 



def makeplatooninfo(dataset, simlen = 50):
#	This looks at the entire dataset, and makes a platooninfo entry for every single vehicle. The platooninfo tells us during which times we calibrate a vehicle. It also contains
#the vehicles intial conditions, as well as the vehicles leaders, and any followers the vehicle has. note that we modify the folowers it has during the time 
#we use the makeplatoon function. 
#The function also makes the outputs leaders, G (follower network), simcount, curlead, totfollist, followers, curleadlist
#All of those things we need to run the makeplatoon function, and all of those are modified everytime makeplatoon runs. 
#
#input:     
#    dataset: source of data, 
#    
#    dataind: column indices for data entries. e.g. [3,4,9,8,6,2,5] for reconstructed. [5,11,14,15,8,13,12] for raw/reextracted. (optional)
#    NOTE THAT FIRST COLUMN IS VEHICLE ID AND SECOND COLUMN IS FRAME ID. THESE ARE ASSUMED AND NOT INCLUDED IN DATAIND
#            0- position, 
#            1 - speed, 
#            2 - leader, 
#            3 - follower. 
#            4 - length, 
#            5 - lane, 
#            6 - length
            #7 -lane
            #8 - acceleration
#            e.g. data[:,dataind[0]] all position entries for entire dataset, data[data[:,1]] all frame IDs for entire dataset
#            
#    simlen = 50: this is the minimum number of observations a vehicle has a leader for it to be calibrated. 
#    
#output: 
#    meas: all measurements with vehID as key, values as dataset[dataset==meas.val()] i.e. same format as dataset
            #rows are observations. 
            #columns are: 
            #0 - id
            #1 - time
            #2 - position
            #3 - speed
            #4 - leader 
            #5 - follower
            #6 - length
            #7 - lane
            #8 - acceleration
#    
#    platooninfo: dictionary with key as vehicle ID, (excludes lead vehicle)
#    value is array containing information about the platoon and calibration problem 
#        0 - t_nstar (first recorded time, t_nstar = t_n for makefollowerchain)
#        1 - t_n (first simulated time)
#        2 - T_nm1 (last simulated time)
#        3 - T_n (last recorded time)
#        4 - array of lead vehicles
#        5 - position IC 
#        6 - speed IC 
#        7 - [len(followerlist), followerlist], where followerlist is the unique simulated followers of the vehicle. note followerlist =/= np.unique(LCinfo[:,2])
#        
#    leaders: list of vehicle IDs which are not simulated. these vehicles should not have any leaders, and their times should indicate that they are not simulated (t_n = T_nm1)
#    
#    G: directed graph (digraph) where nodes are all vehicles, and edges point from each node to any vehicles which have the parent node as a leader.  (not outputed anymore)
#    example:
#    G.nodes() 
#    NodeView((1,2,4))
#    G.edges()
#    EdgeView([(1,2), (1,4)])
#    There are 3 vehicles total. vehicle 1 has vehicles 2 and 4 as followers. Vehicles 2 and 4 do not have any followers. 
#    
#    simcount: count of how many vehicles in the dataset have 1 or more followers that need to be simulated. If simcount is equal to 0, then 
#    there are no more vehicles that can be simulated. Simcount is not the same as how many vehicles need to be simulated. In above example, simcount is 1. 
#    If vehicles 2 and 4 are both simulated, the simcount will drop to 0, and all vehicles that can be simulated have been simulated.
#    
#    curlead: this is needed for makeplatoon. We assign it as None for initialization purposes. This is the most recent vehicle added as a leader to curleadlist
#    
#    totfollist: this represents ALL possible followers that may be able to be added based on all the vehicles currently in leaders. list. needed for makeplatoon
#    
#    followers: this is NOT all possible followers, ONLY of any vehicle that has been assigned as 'curlead' (so it is the list of all vehicles that can follow anything in curleadlist).
#    The purpose of this variable in addition to totfollist is that we want to prioritize vehicles that have their leader in the current platoon.
#    
#    curleadlist: this is needed for makeplatoon. the current list of leaders that we try to add followers for
	##########
    #inputs - dataset. it should be organized with rows as observations and columns have the following information
    #dataind: 0 - vehicle ID, 1- time,  2- position, 3 - speed, 4 - leader, 5 - follower. 6 - length, 7 - lane, 8 - acceleration 
    #the data should be sorted. Meaning that all observations for a vehicle ID are sequential (so all the observations are together)
    #additionally, within all observations for that vehicle time should be increasing. 
    
    #simlen = 50 - vehicles need to have a leader for at least this many continuous observations to be simulated. Otherwise we will not simulate. 
    
    #this takes the dataset, changes it into a dictionary where the vehicle ID is the key and values are observations. 
    
    vehlist, vehind, vehct = np.unique(dataset[:,0], return_index =True, return_counts = True) #get list of all vehicle IDs. we will operate on each vehicle. 
    
    meas = {} #data will go here 
    platooninfo = {} #output 
    masterlenlist = {} #this will be a dict with keys as veh id, value as length of vehicle. needed to make vehlen, part of platooninfo. not returned 
    leaders = [] #we will initialize the leader information which is needed for makeplatoon 
    
    for z in range(len(vehlist)): #first pass we can almost do everything 
        i = vehlist[z] #this is what i used to be
        curveh = dataset[vehind[z]:vehind[z]+vehct[z],:] #current vehicle data 
#        LCinfo = curveh[:,[1,dataind[2], dataind[3]]] #lane change info #i'm taking out the LCinfo from the platooninfo since the information is all in meas anyway
        lanedata = np.nonzero(curveh[:,4])[0] #row indices of LCinfo with a leader 
        #the way this works is that np.nonzero returns the indices of LCinfo with a leader. then lanedata increases sequentially when there is a leader, 
        #and has jumps where there is a break in the leaders. so this is the exact form we need to use checksequential.
        mylen = len(lanedata)
        lanedata = np.append(lanedata, lanedata) #we need to make this into a np array because of the way checksequential works so we'll just repeat the column
        lanedata = lanedata.reshape((mylen,2) , order = 'F')
        unused, indjumps = helper.checksequential(lanedata) #indjumps returns indices of lanedata, lanedata itself are the indices of curveh. 
        t_nstar = int(curveh[0,1]) #first time measurement is known
        T_n = int(curveh[-1,1]) #last time measurement is known 

        masterlenlist[i] = curveh[0,6] #add length of vehicle i to vehicle length dictionary 
        meas[i] = curveh #add vehicle i to data 
        
        if np.all(indjumps == [0,0]) or curveh[0,6]==0: #special case where vehicle has no leaders will cause index error; we cannot simulate those vehicles
            #also if the length of the vehicle is equal to 0 we can't simulate the vehicle. If we can't simulate the vehicle, t_nstar = t_n = T_nm1
            t_n = t_nstar  #set equal to first measurement time in that case. 
            T_nm1 = t_nstar
            platooninfo[i] = [t_nstar, t_n, T_nm1, T_n, [], curveh[0,2], curveh[0, 3], [0, []]]
#            platooninfo[i] = [t_nstar, t_n, T_nm1, T_n, [], [0, []]]
            continue
            
        t_n = int(curveh[lanedata[indjumps[0],0],1]) #simulated time is longest continuous episode with a leader, slice notation is lanedata[indjumps[0]]:lanedata[indjumps[1]]
        T_nm1 = int(curveh[lanedata[indjumps[1]-1,0],1])
        
        if (T_nm1 - t_n) < simlen: #if the simulated time is "too short" (less than 5 seconds) we will not simulate it (risk of overfitting/underdetermined problem)
            t_n = t_nstar
            T_nm1 = t_nstar
            
        
        platooninfo[i] = [t_nstar, t_n, T_nm1, T_n, [], curveh[t_n-t_nstar,2], curveh[t_n-t_nstar, 3], [0, []]] #put in everything except for vehicle len and the follower info 
#        platooninfo[i] = [t_nstar, t_n, T_nm1, T_n, [], [0, []]]
    for i in vehlist: #second pass we need to construct vehlen dictionary for each vehicle ID. we will also put in the last entry of platooninfo, which gives info on the followers
#        vehlen = {} #initialize vehlen which is the missing entry in platooninfo for each vehicle ID 
        curinfo = platooninfo[i] #platooninfo for current veh 
        t_nstar, t_n, T_nm1 = curinfo[0], curinfo[1], curinfo[2]
        leaderlist = list(np.unique(meas[i][t_n-t_nstar:T_nm1-t_nstar+1,4])) #unique leaders 
        if 0 in leaderlist: #don't care about 0 entry remove it 
            leaderlist.remove(0)
        for j in leaderlist: #iterate over each leader
#            if j == 0.0: #vehID = 0 means no vehicle (in this case, no leader)
#                continue 
#            vehlen[j] = meas[j][0,dataind[4]] #put in vehicle length of each leader during simulated times 
            #now we will construct the last entry of platooninfo
            platooninfo[j][-1][1].append(i) #vehicle j has vehicle i as a follower.
            platooninfo[j][-1][0] += 1 #add 1 to the counter of followers that will need to be simulated
        platooninfo[i][4] = leaderlist #put in the leader information 
        
        #now we have identified all the necessary information to setup the optimization problem.
        #first thing to do is to identify the vehicles which are not simulated. These are our lead vehicles. 
        if (T_nm1 - t_n) == 0: #if vehicle not simulated that means it is always a leader    
#            curfollowers = np.unique(LCinfo[:,2]) #all unique followers of leader. NOTE THAT JUST BECAUSE IT IS A FOLLOWER DOES NOT MEAN ITS SIMULATED
            leaders.append(i)
            
    
    #explanation of how makeplatoon works:    
    #the main problem you can run into when forming platoons is what I refer to as "circular dependency". this occurs when veh X has veh Y as BOTH a leader AND follower. 
    #This is a problem because veh X and Y depend on each other, and you have to arbitrarily pick one as only a leader in order to resolve the loop
    #this can occur when a follower overtakes a leader. I'm not sure how common that is, but in the interest of generality we will handle these cases. 
    #the other thing to keep in mind is related to efficiency. since we need to iterate over lists of vehicles twice to form platoons (O(n**2)), if the lists of candidate 
    #vehicles, or leaders, becomes long, forming the platoons can potentially be very inefficient. size m vehicle platoon, size n lists, potentially m*n**2. 
    #however, if you are smart about how you form the platoons you can keep the follower list and leader list fairly short, so n will be small. 
    #We want to take out leaders once all their followers are in platoons. this keeps the leader list short.
    #to keep the follower list short, you need to check for circular dependency, and also search depth first instead of breadth. (e.g. try to go deep in single lane)
    #end explanation
    
    #now all the "pre-processing" has been completed.
    
    #now we will initialize the platoon formationation algorithm
    
    #first make sure there are vehicles which can be used as lead vehicles 
    #actually you don't necessarily have to do this because you can resolve the circular dependency. 
    if len(leaders)==0:
        print('no leaders identified in data. data is either loaded incorrectly, or lead vehicles have circular dependency')
        print('we will automatically get a leader')
        newlead = None
        newleadt_nstar= float('inf')#initialized as arbitrarily large value
        for i in vehlist: 
            if platooninfo[i][0] < newleadt_nstar:
                newleadt_nstar = platooninfo[i][0]
                newlead = i
        platooninfo[newlead][1] = platooninfo[newlead][0] #define the new leader as a vehicle that is never simulated
        platooninfo[newlead][2] = platooninfo[newlead][0] #define the new leader as a vehicle that is never simulated
        leaders.append(newlead)
            
        
        

   
    
    curlead = None #initialize curlead as None 
    
    for i in leaders: #this will ensure that every vehicle designed as a leader has no leaders and no vehicle has a follower which is designated as a leader. 
        chklead = platooninfo[i][4].copy() #copy because we will potentially be modifying this pointer
        for j in chklead: 
            platooninfo[j][-1][1].remove(i) #remove leader from the follower list of the leader's leaders; meaning the leader is not a follower
            platooninfo[j][-1][0] += -1 #adjust index to be consistent with above line
            platooninfo[i][4].remove(j) #the leader should not have any leaders. 
            
    #want to make sure there are not any leaders with no followers since we don't want that.         
    leadersc = leaders.copy()
    for i in leadersc:#initialize the simulation with the trajectory of the leaders 
        if platooninfo[i][-1][0] ==0: #in case there are any leaders without followers #probably don't need this if but meh we'll leave it in 
            leaders.remove(i)
            
    simcount = 0 #simcount keeps track of how many vehicles still have followers we can simulate. Once no vehicles have followers we can simulate, it means 
    #we must have simulated every vehicle that we can (thus our job is done)
    for i in vehlist: 
        if platooninfo[i][-1][0]>0:
            simcount += 1
            
    totfollist = []
    followers = []
    curleadlist = []
        #we need to initialize totfollist before we move into the while loop
    for i in leaders: 
        #add in all the followers into totfollist, unless i = curlead 
#        if i == curlead:  #don't need this part when it's in makeplatooninfo because curlead is just None
#            continue #don't append the thing if i == curlead because it will be done in the beginning of the while loop 
        for j in platooninfo[i][-1][1]: 
            totfollist.append(j) #append all of the followers for vehicle i
    totfollist = list(set(totfollist)) #make list of followers unique
    
    
     #We return the objects we constructed, and can begin to form the platoons iteratively using makeplatoon. 
    return meas, platooninfo, leaders, simcount, curlead, totfollist, followers, curleadlist


""" 
// //
TO DO 
// //

Would like makeplatoon to work more simply, and avoid the problem it currently has where the platoons tend to get spread out among many lanes. 
Want something that will try to keep to the same lane, so ideally we get in situations where all vehicles being calibrated are in a long chain
Some notes about this are on my phone. 

Note also that the current makeplatoon depends on the output of makeplatooninfo

Other consideration is that we want an algorithm that can handle time varying platoon order. 
"""
def makeplatoon(platooninfo, leaders, simcount, curlead, totfollist, followers, curleadlist, n=10):
#	input: 
#    meas, (see function makeplatooninfo)
#    
#    platooninfo, (see function makeplatooninfo) - note that makeplatoon will modify the last argument of platooninfo; which is only used for makeplatoon
#    
#    leaders, (see function makeplatooninfo) - note that makeplatoon will remove vehicles from leaders after they are no longer needed
#    
#    G, (see function makeplatooninfo) - note that makeplatoon will remove vehicles from G after they are no longer needed (not longer used)
#    
#    simcount (see function makeplatooninfo), - note that makeplatoon modifies this value; it keeps track of how many vehicles still have followers yet to be simulated
#    
#    curlead - output from makeplatooninfo. This controls what vehicle we currently prioritize; that vehicle followers are attempted to be added first. updated 
#    during the execution and outputted to be used in the next platoon. 
#    
#    totfollist - output from makeplatooninfo. updated during execution. this is all followers of every vehicle in leaders
#    
#    followers - output from makeplatooninfo. updated during execution. vehicles in followers have priority of being added. 
#    
#    n = 10: n controls how big the maximum platoon size is. n is the number of following vehicles (i.e. simulated vehicles)
#    
#    dataind = [3,4,9,8,6,2,5]: dataind specifies the column indices for data entries. see makeplatooninfo
#    
#    
#output: 
#    platooninfo, which is updated as we simulate more vehicles
#    
#    leaders, which are vehicles either already simulated or vehicles that were never simulated. everything in leaders is what we build platoons off of!
#    NOTE THAT LEADERS ARE NOT ALL LEADERS. it is only a list of all vehicles we are currently building stuff off of. we remove vehicles from leaders 
#    after they have no more followers we can simulate
#    
#    G, updated network of follower dependencies (no longer used)
#    
#    simcount, how many more vehicles have followers that can be simulated. when simcount = 0 all vehicles in the data have been simulated. 
#    
#    curlead - current leader. this will be the last vehicle added. 
#    
#    totfollist - updated total list of followers. updated because any simulted vehicle is added as a new leader
#    
#    followers - updated current candidate followers. updated as we add new leaders to curleadlist and simulate followers. 
#    
#    platoons - platoons[1:] is the list of vehicles, and platoons[0] gives some information related to any circular dependencies/loops in the data
#    
#    main output is platoons, which is a list of the vehicles that we will simulate in the platoon. the first entry of this list is an array that has special meaning: 
#        the special meaning depends on whether we are using the 'strategy 1' or 'strategy 2' which are two different ways we can resolve loops in the data
#        
#        for strategy 1, the first entry indicates what vehicles are taken directly from the meas to do the simulation for the platoon
#        e.g. platoons = [[5,14],17] means that the platoon consists only of vehicle 17. vehicles 5 and 14 are taken from the measurements to do the simulation
#        [[],17,18,19] means that the platoons consists of vehicles 17, 18, and 19. the only vehicles we need to do the simulation are either never simulated, or already simulated. 
#        
#        for strategy 2, the first entry indicates what times the platoon holds for
#        e.g. platoons = [[1000,1200],17,18,19] means that we have the platoon order of 17 18 19 for times 1000-1200
	
    #################
    #current code: 
    #we have leaders, all possible vehicles which may have followers that can be added
    #curleadlist, which is a smaller subset of leaders
    #followers, which is all the followers of curleadlist 
    #totfollist, which is all the followers of leaders
    #the code works as follows. We have 3 different operations, in different priorities: 
    
    #0.add curlead to the curleadlist and insert its following vehicles into the front of followers to be checked first
    #1.try to add followers of vehicles in curleadlist. vehicles are only added if all their leaders are in curleadlist 
    #if a follower is added, that vehicle becomes the curlead and is added to curleadlist.
    
    #2.if 1 can't be done, then add a random vehicle from leaders into curleadlist. Only leaders that may potentially result in followers being added can be selected
    
    #3. if 1 and 2 can't be done, then there must be some loop that we will resolve 
    
    #we could try adding: 
    #1.b. if there are any followers of curleadlist that could be added if we used leaders instead of curleadlist, add those followers. (need a seperate followers list for this since we remove followers after checking them)
    #####################
#    other thing is that I think we can also just try something super simple where instead of 1-2 we just have 1 strategy where we iterate over all the followers, 
#    and if we can add any of them do add them. so in total that's 3 similar versions of this program we can try. 
    #####################
    platoons = [] #current followers list for platoon; these are the vehicles which have been successfully added to the platoon
#    totfollist = [] #list of every single follower of leaders; followers variables only has leaders that are in curleadlist
    curn = 0 #current n value
    

    
    while curn < n and simcount > 0: #loop which will be exited when the platoon is of size desired n or when no more vehicles can be added 
        breaknow = False 
        if curlead is not None:            
            curleadlist.insert(0,curlead) #append current leader to current leader list
            for i in platooninfo[curlead][-1][1]: #append all of the current leader's followers to the current follower list
                followers.insert(0,i) 
#                totfollist.insert(0,i)
            followers = list(set(followers)) #remove any duplicate entries from followers; we don't want to check the same vehicle multiple times!
#            totfollist = list(set(totfollist))
            
            
            
        followersc = followers.copy() #followersc is a copy of followers because we need to modify followers while iterating over it 
        for i in followersc: #check if any candidate followers can be added. we iterate over the copy of followers since we will be deleting entries from the list 
            chklead = platooninfo[i][4] #these are all the leaders needed to simulate vehicle i
            if all(j in curleadlist for j in chklead): #will be true if curlead contains all vehicles in chklead; in that case vehicle i can be simulated
                #after we add a follower, we want to remove the follower from the graph, remove it from the leaders' followers (in platooninfo), and subtract 1 from the number of followers each vehicle has 
                platoons.append(i) #append vehicle i to list of followers in current platoon
                curn += 1 #we have added a following vehicle. if curn reaches n, then the platoon is of desired size 
                curlead  = i #newly added follower becomes the new leader
                leaders.insert(0,curlead) #append newly added follower to the leader list as well; we have simulated vehicle i, and can now treat it as a leader 
                #note that leaders can either be vehicles which are never simulated, or vehicles that we have put in a platoon successfully (and thus can be simulated)
                followers.remove(curlead) #delete i from followers
                totfollist.remove(curlead) #delete i from the total follower list 
                for j in chklead: 
                    platooninfo[j][-1][1].remove(i) #remove i from each of the leader's followers
                    platooninfo[j][-1][0] += -1 #subtract 1 from the total number of followers yet to be added 
                    if platooninfo[j][-1][0] < 1: #if a leader has no more followers
                        simcount += -1 #adjust simcount. if simcount reaches 0 our job is finished and we can return what we have, even if curn is not equal to n
                        leaders.remove(j) #remove it from the list of leaders
                        curleadlist.remove(j) #remove it from the curleadlist. Note that we know that that any vehicle in curleadlist MUST ALSO BE in leaders
                        #note that vehicles in leaders are not necessarily in curleadlist. We know that every vehicle in chklead must be in curleadlist in this case, 
                        #since we were only able to add vehicle i to the platoon because curleadlist has all of vehicle i's leaders
                if platooninfo[curlead][-1][0]<1: #need to do something different if the curlead turns out not to have any followers
                    leaders.remove(curlead) #remove it from the leader list
                    curlead = None #specify None as leader; the first part of while loop will handle special case if followers is empty and curlead is None
                    #otherwise, it's OK for curlead to be None, we can still check the followers as long as followers isn't empty. 
                else: #if above is false then we need to add things to totfollist
                    for j in platooninfo[curlead][-1][1]:
                        totfollist.insert(0,j)
                    totfollist = list(set(totfollist))
                break #stop checking followers; go back to while loop
            followers.remove(i) #don't need to keep checking vehicle i if we can't add it the first time; if we add a new lead vehicle with vehicle i as a follower
            #it will be readded to the followers list 
            
        else: #no vehicles in followers could be added
#            print('no candidate followers could be added - attempting to add more lead vehicles')
            #there are two possible scenarios at this point. Either we can keep adding followers, and we are just missing some vehicles from leaders
            #the other possibility is that we can't add any followers, even if we added every leader, which means there must be a circular dependency among the followers. 
            #we want to figure out which possibility it is, because we don't want to keep checking for, and resolving, loops unless we have to. 
            
            #note if we get the print out in the else statement the alg should fail so it doesnt so that suggests a bug 
            for i in totfollist: #iterate over every possible follower (total follower list)
                chklead = platooninfo[i][4] #get leaders for each candidate follower
                if all(j in leaders for j in chklead): #if true, more vehicles can be simulated 
                    for j in chklead: #check all of the potential new leaders
                        if j not in curleadlist: #if any of the leaders is not in the current leader list
                            curlead = j #we will assign that leader as curlead, and exit both the nested loops, returning to the while loop where we will add it, and its candidate followers
                            breaknow = True
                            break #break out of inner for loop
                if breaknow:
                    break #break out of the outer for loop and return to the while loop
            else: #otherwise we need to resolve a circular dependency
#                print('no lead vehicles found, attempting to resolve loop among followers')
                bestG = None
                bestGlen = float('inf')
                bestGedge = float('inf')
                for j in totfollist: #for loop to choose the smallest network possible
                    
                    G = nx.DiGraph()
                    prevfolfix = [] #vehicles that we have already added all of their problem leaders to the network 
                    nextfolfix = [] #these are vehicles we need to add their problem leaders to the network after we deal with the current folfix
                    folfix = j #nothing in totfollist can be added, so we'll pick a random entry as the follower to "fix" 
                    G.add_node(folfix) #add follower to the network
                    chklead = platooninfo[folfix][4] #get leaders
                    for i in chklead: 
                        if i not in leaders: #if the leaders arent in the list of leaders (variable leaders)
                            G.add_node(i) #add them to network
                            G.add_edge(folfix,i) #add an edge from folfix to the leader its missing (i)
                            if i not in prevfolfix: #if we haven't already done this for i 
                                nextfolfix.append(i) #add i to the list of vehicles we need to check
                    prevfolfix.append(folfix) #after we have checked i we don't have to check it again so put it in prevfolfix
                    while len(nextfolfix) > 0:  #keep checking everything in netfolfix until everything needed is in prevfolfix: at that point netfolfix can't get bigger
                        folfix = nextfolfix.pop()
                        chklead = platooninfo[folfix][4]
                        for i in chklead: 
                            if i not in leaders:
                                G.add_node(i)
                                G.add_edge(folfix,i)
                                if i not in prevfolfix:
                                    nextfolfix.append(i)
                        prevfolfix.append(folfix)
#                    print(len(G.nodes())) #debug
                    
                    if len(G.nodes()) < bestGlen or len(G.edges())<bestGedge:
                        bestG = G.copy()
                        bestGlen = len(G.nodes())
                        bestGedge = len(G.edges())
#                print('best G nodes are '+str(len(bestG.nodes()))) #debug
                #now we have created a network that shows the dependency among some the vehicles we are unable to add. 
                #there must exist cycles among these vehicles that prevent us from adding them - we will find a cycle basis for these.
                #we will resolve these cycles with the `strategy 1' where we solve the hitting set problem on the cycle basis. For the results of that, 
                #every vehicle identified in the hitting set will be solved using a heuristic where they are simulated with the problem leaders taken from measurements
                #in 'strategy 2' you would resolve these loops by having a time varying platoon order
#                print('number of nodes in G is '+str(len(bestG.nodes())))
#                print(G.nodes())
#                print(G.edges())
#                print('length of totfollist is '+str(len(totfollist)))
                cyclebasis = nx.simple_cycles(bestG) #get cycle basis (this is a generator)
                #can we not use cycle basis instead (convert to undirected graph?)
                ###########
                #time is dominated by the below segment; we have made a better version but the time is still dominated by this section. 
                #time to resolve loops is exponetial with the size of the network G. 
                #overall calibration time is dominated by the time to do the calibration though; ultimately this function is a small amount of the total work needed
#                subsets = [] 
#                universe = set()
#                start = time.time()
#                for i in cyclebasis: 
#                    subsets.append(set(i)) #this is all of the subsets
#                    universe = universe.union(set(i)) #this is the "universe" which is the union of all the subsets
#                end = time.time()
#                print(str(end-start))
                
                universe = list(bestG.nodes()) #universe for set cover
#                start = time.time()
                subsets = list(cyclebasis) #takes a long time to convert generator to list when the generator is very long; this is what dominates the cost
                for i in range(len(subsets)):
                    subsets[i] = set(subsets[i])
#                end = time.time()
#                print(str(end-start))
                #now we have what is needed for the set cover problem, and we need to convert this into a hitting set problem. 
                HSuni = list(range(len(subsets))) #read variable name as hitting set universe; universe for the hitting set HSuni[0] corresponds to subsets[0]
                HSsubsets = [] #this is the list of subsets for the hitting set
                for i in range(len(universe)): #each member of universe we need to replace with a set
                    curveh = universe[i] #current member of universe 
                    cursubset = set() #initialize the set we will replace it with 
                    for j in range(len(subsets)): #
                        if curveh in subsets[j]: # if i is in subsets[j] then we add the index to the current set for i
                            cursubset.add(j)
                    HSsubsets.append(cursubset)
#                print('number of subsets (nodes) is '+str(len(HSsubsets))+' ('+str(len(universe))+')') #DEBUG
#                print('number of universe (cycles) is '+str(len(HSuni))+' ('+str(len(subsets))+')') #DEBug
#                start = time.time()
                result = helper.greedy_set_cover(HSsubsets,HSuni) #solve the set cover problem which gives us the HSsubsets which cover HSuni
#                end = time.time()
#                print(str(end-start))
                #now we have to convert the output of the set cover algorithm back to the actual vehicles we will be simulating 
                #we will also put what needs to be taken from the measurements for the platoon to be simulated
                #we will also need to update followers, totfollist, and leaders according to the updates we make
                for i in result: 
                    curfix = []
                    curveh = universe[HSsubsets.index(i)] #vehicle ID of the corresponding vehicle in the hitting set
                    curfix.append(curveh)
                    chklead = platooninfo[curveh][4]
                    
                    leaders.insert(0,curveh) #curveh will be simulated now so we can insert it into leaders
                    #also need to add all the followers into totfollist because we may potentially add several leaders in this section of the code 
                    if curveh in totfollist:
                        totfollist.remove(curveh)
                    if curveh in followers: 
                        followers.remove(curveh)
                    
                    for j in chklead: 
                        platooninfo[j][-1][1].remove(curveh)
                        platooninfo[j][-1][0] += -1
                        if j not in leaders: #j might be in followers or totfollist in this special case where we resolve loops
                            curfix.append(j)
                        if platooninfo[j][-1][0] < 1: 
                            simcount += -1
                            if j in leaders:
                                leaders.remove(j)
                            if j in curleadlist: 
                                curleadlist.remove(j)
                    curlead = curveh #make curlead the last vehicle we have resolved using resolution strategy 
                    if platooninfo[curlead][-1][0] < 1: #unless curlead has no followers in which case we'll let curlead be None 
                        curlead = None
                        leaders.remove(curlead)
                    else: 
                        for j in platooninfo[curlead][-1][1]:
                            totfollist.insert(0,j)
                        totfollist = list(set(totfollist))
#                    platoons[0].append(curfix)
                    platoons.append(curfix) #new version works with new platoon format maybe
                    #actually what happens is we get nested platoons
                
                
            
    return platooninfo, leaders, simcount, curlead, totfollist, followers, curleadlist, platoons



def makeplatoonlist(data, n=1, form_platoons = True, extra_output = False,lane= None, vehs = None):
    
    #this runs makeplatooninfo and makeplatoon on the data, returning the measurements (meas), information on each vehicle (platooninfo), 
    #and the list of platoons to calibrate 
	
	#inputs -
	# data - data in numpy format with correct indices 
	# n = 1 - specified size of platoons to form 
	# form_platoons = True - if False, will just return meas and platooninfo without forming platoons 
	# extra_output = False - option to give extra output which is just useful for debugging purposes, making sure you are putting all vehicles into platoon 
	
	# lane = None - If you give a float value to lane, will only look at vehicles in data which travel in lane
	# vehs = None - Can be passed as a list of vehicle IDs and the algorithm will calibrate starting from that first vehicle and stopping when it reaches the second vehicle. 
	# lane and vehs are meant to be used together, i.e. lane = 2 vehs = [582,1146] you can form platoons only focusing on a specific portion of the data. 
	#I'm not really sure how robust it is, or what will happen if you only give one or the other. 
	
	#outputs - 
	# meas - dictionary where keys are vehicles, values are numpy array of associated measurements, in same format as data
	# platooninfo - dictionary where keys are vehicles, value is list of useful information 
	# platoonlist - list of lists where each nested list is a platoon to be calibrated 
	

    meas, platooninfo, leaders, simcount, curlead, totfollist, followers, curleadlist = makeplatooninfo(data)
    num_of_leaders = len(leaders)
    num_of_vehicles = len(meas.keys()) - num_of_leaders 
    platoonoutput = [] 
    platoonlist = []
    
    if not form_platoons: 
        return meas, platooninfo
    
    if vehs is not None: #in this special case we are giving vehicles which we want stuff to be calibrated between 
        #one thing I don't like about this is that the first vehicle in vehs is not included, when really I want it to be. 
        #also any other vehicles designated as `leaders` aren't included either. It's a small thing but could be nice to change. 
        
        """
        #note to self: another way to implement this is to use the new sort vehicle function :) 
        looks like you could just do lanvehlist(data, lane, vehs), and then sortveh3(). 
        """
        
        vehlist, unused = helper.lanevehlist(data,lane,vehs) #special functions gets only the vehicles we want to simulate out of the whole dataset
        #after having gotten only the vehicles we want to simulate, we modify the platooninfo, leaders , totfollist, to reflect this
        #lastly we can seed curlead as the vehs[0] to start
        platooninfovehs = platooninfo
        platooninfo = {}
        for i in vehlist: 
            platooninfo[i] = copy.deepcopy(platooninfovehs[i])
            templead = []
            tempfol = []
            for j in platooninfo[i][4]:
                if j in vehlist: 
                    templead.append(j)
            for j in platooninfo[i][-1][1]:
                if j in vehlist: 
                    tempfol.append(j)
            lentempfol = len(tempfol)
                    
            platooninfo[i][4] = templead
            platooninfo[i][-1] = [lentempfol,tempfol]
        
        #platooninfo is updated now we need to update the totfollist, simcount, and leaders.
        curlead = vehs[0] #curlead (first vehicle algo starts from) should be the first vehicle in vehs
        simcount = 0
        for i in vehlist:
            if platooninfo[i][-1][0] >0:
                simcount += 1
        leaders = []
        for i in vehlist: 
            if len(platooninfo[i][4]) == 0:
                leaders.append(i)
        totfollist = []
        for i in leaders:
            for j in platooninfo[i][-1][1]:
                totfollist.append(j)
        totfollist = list(set(totfollist))
    
    while simcount > 0:
        #make a platoon
        platooninfo, leaders, simcount, curlead, totfollist, followers, curleadlist, platoons = makeplatoon(platooninfo, leaders, simcount, curlead, totfollist, followers, curleadlist, n)
        #append it to platoonoutput (output from the function) and platoonlist (actual platoons we will be calibrating)
        platoonoutput.append(platoons)
        #old code worked with the empty list in platoons
#        if platoons[0] == []:
##        if True:
#            platoonlist.append(platoons)
#        else: 
#            for j in platoons[0]:
#                newplatoon = []
#                newplatoon.append(j[0])
#                platoonlist.append(newplatoon) #append all the loop vehicles as 
#            newplatoon = []
#            newplatoon = newplatoon + platoons[1:]
#            platoonlist.append(newplatoon)
        
        #new code will work without the empty list in platoons
        newp = []
        for i in platoons: 
            if type(i) == np.float64:
                newp.append(i)
            elif type(i) == list: 
                platoonlist.append(i)
        platoonlist.append(newp)
    
    if vehs is not None:
        platooninfo = platooninfovehs #go back to the original platooninfo after we have made the platoons; this is only for special case where we are calibrating between vehs
    
    if not extra_output:
        return meas, platooninfo, platoonlist
    else: 
        return meas, platooninfo, platoonlist, platoonoutput, num_of_leaders, num_of_vehicles

def makeplatoonlist_s(data, n = 1, lane = 1, vehs = []):
    meas, platooninfo = makeplatoonlist(data,1,False)
    
    vehIDs = np.unique(data[data[:,7]==lane,0])
    sortedvehID = sortveh3(vehIDs,lane,meas,platooninfo) #algorithm for sorting vehicle IDs
    
    sortedplatoons = []
    nvehs = len(sortedvehID)
    cur, n = 0, 5
    while cur < nvehs: 
        curplatoon = []
        curplatoon.extend(sortedvehID[cur:cur+n])
        sortedplatoons.append(curplatoon)
        cur = cur + n
    return meas, platooninfo, sortedplatoons

def sortveh3(vehlist,lane,meas,platooninfo):
    #third attempt at a platoon ordering algorithm 
    #this one is more hueristic based but should work pretty much always 
    """
    main way to improve this functions 
    
    -come up with some clever way to sort vehicles. I've thought about it for a long time and this is pretty much the best I came up with. 
    
    -main way to improve speed is that when you are going over the leftover, you should check if you can add stuff to vehfollist, and potentially use the sortveh_disthelper again. 
    because the way we are adding vehicles in the leftover is very very slow (n^2) and the way sortveh_disthelper does it looks like (n), so if a bunch of stuff ends up in leftover
    it can potentially kill your performance. so if you need to sort stuff where alot of the vehicles end up in leftover you probably want to make that modification. 
    """
    
    #initialization 
    vehlist = sorted(list(vehlist), key = lambda veh: platooninfo[veh][0]) #initial guess of order
    out = [vehlist[0]] #initialize output 
    
    end = False #keep iterating while end is False
    curveh = out[0] #the first vehicle. 
    
    #get vehfollist, list of following vehicles which we will add.
    temp = meas[curveh]
    temp = temp[temp[:,7]==lane]
    vehfollist = np.unique(temp[:,5])
    temp = []
    for i in vehfollist: 
        if i == 0 : 
            continue
        if i in vehlist: 
            temp.append(i)
    vehfollist = temp
    
    #the way this works is that we keep adding things to vehfollist and they are sorted as they are added to the output. 
    #So we keep adding followers and followers of followers. This won't necessarily add all vehicles though, because we can also have leaders of followers, 
    #and also because we don't know the order in the beginning we don't necessarily begin with the first vehicle, so there may be leaders of the initial curveh. 
    
    count = 0 
    while not end: 
        count += 1 
        #
        if len(out)==len(vehlist): # if everything is added to out it means that everything is done
            end = True
            
        elif len(vehfollist) == 0: #if there are no followers to add but there are still vehicles we need to order then we need to do something about the rest of
            #the vehicles 
            #leftover has all vehicles which haven't been added/sorted yet. 
            leftover = vehlist.copy()
            for i in out: 
                leftover.remove(i)
                
            leftover = sortveh3(leftover,lane,meas,platooninfo) #order the leftover 
            leftover.reverse() #iterate over it in reverse 
            
            for i in leftover: #if we have leftover, we will go through and add each vehicle one at a time. 
                #first check if we can trivially add the vehicle to either the beginning or end. 
                platoont_nstar = platooninfo[out[0]][0] #first time in the platoon 
                platoonT_n = platooninfo[out[-1]][3] #last time in the platoon 
                if platooninfo[i][3] < platoont_nstar: 
#                    newout = out.copy()
#                    newout.insert(0,i)
                    out.insert(0,i)
                    continue
                if platooninfo[i][0] > platoonT_n:
#                    newout = out.copy()
#                    newout.append(i)
                    out.append(i)
                    continue 
                    
                #now we will go through each vehicle in the platoon and measure distance from the vehicle to the leftover. The very first vehicle with a positive value
                #must be the vehicle which is directly after the leftover. 
                leftovermeas = meas[i]
                leftovermeas = leftovermeas[leftovermeas[:,7]==lane]
#                times = leftovermeas[:,1] #times the vehicle is in the target lane 
                leftovert_nstar = platooninfo[i][0] #t_nstar for the leftover
                
                count2 = 0 #keep track of which vehicle we are currently on 
                case = False
                for j in out: #now we need to iterate over each vehicle in the platoon to get the distance for the leftover. 
                    curmeas = meas[j]
                    curmeas = curmeas[curmeas[:,7]==lane]
#                    curmeas = curmeas[curmeas[:,1]==times] #correct times #bug here 
                    curleftovermeas, curmeas = overlaphelp(leftovermeas,curmeas)
                    if len(curmeas) >0: #assuming we have any sort of overlap we can compute the distance
#                        timeinds = curmeas[:,1]-leftovert_nstar
#                        curleftovermeas = leftovermeas[timeinds]
                        curdist = np.mean(curleftovermeas[:,2]-curmeas[:,2]) #get dist for the current vehicle j 
                        if curdist > 0: #you are directly behind the current vehicle 
                            newout = copy.deepcopy(out) #need to create copy becuase for loop goes over out
                            newout.insert(count2,i)
                            break #exit loop
                        else: 
                            lastgood = count2
                            case = True
                    count2 += 1
                else: #if we can't put it in front of any of the vehicles then we can safely add it to the end, or we can put it after the last good vehicle we got 
                    if case: 
                        newout = copy.deepcopy(out)
                        newout.insert(lastgood+1,i)
                    else:
                        count2 = 0
                        lasttime = leftovermeas[-1,1]
                        for j in out: #can potentially get put in the middle in special case 
                            curmeas = meas[j]
                            curmeas = curmeas[curmeas[:,7]==lane]
                            t_n = curmeas[0,1]
                            if lasttime < t_n: 
                                newout = copy.deepcopy(out)
                                newout.insert(count2,i)
                        else: #put at end 
                            newout = copy.deepcopy(out)
                            newout.append(i)
                    #note that there is still one edge case we don't handle, where there is no overlap at all, but it doesn't actually
                    #go to the end, it's just kind of snuck in there
                    
                out = newout
                #improvement would be after you successfully add i, see if you can add to vehfollist, and if you can then you can use sortveh_disthelper again. 

            ################
            #deprecated  -  we always just want to call the sortveh_disthelper unless we don't have anything to add. 
#        elif len(vehfollist)==1: #just 1 follower can just add it don't need to get any special ordering. 
#            out.append(vehfollist[0])
            ###################
            
        else: #get order among followers, this should only be called once, and then we should either go to the if and immediately terminate or go to the elif
            #note that this is pretty slow to only call this once potentially, since we don't like adding leftovers. So if you wanted to optimize this you could 
            #make it so if you add a leftover which has followers, you can then use sortveh_disthelper again, add everything 
            if count > 1: #count should be 1 and it should never be any other value. 
                print('bug')
            out = sortveh_disthelper(out, curveh, vehfollist, vehlist, lane, meas, platooninfo)
            vehfollist = []
            #old notes 
            #possibly sortveh2 is the better approach. see notes we can have lists of vehicles you follow to try to get ordering, need to check for times we get multiple on same
            #level, and check for circular dependency. Can resolve these using average distance between follower and leader as discussed below.
            #for after having added multiple followers need a way to dealing with possibly getting multiple followers again. maybe just use last trajectory and do some thing
            #with the ranking. 
            
            #thinking its possible to order this by looking at distance between followers and their leader. then order by the average distance. 
            #edge cases of vehicle which does not follow anything else in platoon. these can be moved in front of their follower. if there are two such vehicles 
            #and they have same follower can do distance compared to the follower. 
            #after adding multiple followers, need to add all followers of followers, so may have multiple followers to add again. 
            #if this happens, compare everything to the leader which origianlly gave multiple followers. keep adding followers until we get to case where there is only 
            #1 vehicle to logically add next. Note that trajectories can be extended using np.diff or similar if needed. 
            pass
            
            
    return out

def overlaphelp(meas1, meas2):
    #for two vehicles meas1 and meas2, computes the overlap between them and returns the data which can be directly compared; this is useful for various things 
    #this is meant to be used when you have somethign like meas[meas[:,7] == lane] and meas2[meas2[:,7] == lane] and then you want all the times where there is overlap. 
    #uses functions sequential and indjumps from calibration 
    
    #get indices of the sequential data 
    ind1 = helper.sequential(meas1)
    ind2 = helper.sequential(meas2)
    
    #change the indices into times 
    times1 = helper.indtotimes(ind1,meas1)
    times2 = helper.indtotimes(ind2,meas2)
    #booking keeping, output will be the parts of meas we can use to compute the distance 
    outtimes = []
    outind1 = []
    outind2 = []
    #need to keep track of where we are 
    count1 = 0 
    count2 = 0
    while count1 < len(times1): #iterate over the first meas
        cur1 = times1[count1]
        while count2 < len(times2): #iterate over the second meas 
            cur2 = times2[count2]
            if cur2[0] < cur1[0] and cur2[1] < cur1[0]: #trivial case, check next 2 block 
                count2 += 1
                continue
            elif cur2[0] > cur1[1] and cur2[1] > cur1[1]: #other trivial case, done checking 2 blocks and check next 1 block 
                count2 = 0
                count1 += 1
                break 
            elif cur2[0] <= cur1[0] and cur2[1] >= cur1[0] and cur2[1] <= cur1[1]:
                curtimes = (cur1[0], cur2[1])
                #code to convert the times back into indices
                outtimes.append(curtimes)
                temp1 = (curtimes[0]-cur1[0]+cur1[2], curtimes[1]-cur1[0]+cur1[2])
                outind1.append(temp1)
                temp1 = (curtimes[0]-cur2[0]+cur2[2],curtimes[1]-cur2[0]+cur2[2])
                outind2.append(temp1)
                #update for next iteration 
                #check the next 2 block 
                count2 += 1 
                continue
            elif cur2[0] <= cur1[0] and cur2[1] >= cur1[1]:
                curtimes = (cur1[0],cur1[1])
                
                outtimes.append(curtimes)
                temp1 = (curtimes[0]-cur1[0]+cur1[2], curtimes[1]-cur1[0]+cur1[2])
                outind1.append(temp1)
                temp1 = (curtimes[0]-cur2[0]+cur2[2],curtimes[1]-cur2[0]+cur2[2])
                outind2.append(temp1)
                #check the next 1 block 
                count1 += 1 
                break
            elif cur1[0] <= cur2[0] and cur1[1] >= cur2[1]:
                curtimes = (cur2[0],cur2[1])
                
                outtimes.append(curtimes)
                temp1 = (curtimes[0]-cur1[0]+cur1[2], curtimes[1]-cur1[0]+cur1[2])
                outind1.append(temp1)
                temp1 = (curtimes[0]-cur2[0]+cur2[2],curtimes[1]-cur2[0]+cur2[2])
                outind2.append(temp1)
                #check the next 2 block 
                count2 += 1
                continue
            else: #cur1[0] < cur2[0] and cur1[1] < cur2[1]
                curtimes = (cur2[0], cur1[1])
                
                outtimes.append(curtimes)
                temp1 = (curtimes[0]-cur1[0]+cur1[2], curtimes[1]-cur1[0]+cur1[2])
                outind1.append(temp1)
                temp1 = (curtimes[0]-cur2[0]+cur2[2],curtimes[1]-cur2[0]+cur2[2])
                outind2.append(temp1)
                
                #check next 1 block
                count1 += 1
                break
        count1 += 1
            
    #now get the final data to return
    dim = np.shape(meas1)[1]
    out1 = np.zeros((0,dim))
    for i in outind1:
        out1 = np.append(out1,meas1[int(i[0]):int(i[1])],axis=0)
    out2 = np.zeros((0,dim))
    for i in outind2:
        out2 = np.append(out2,meas2[int(i[0]):int(i[1])],axis=0)
    
    return out1, out2
    

def sortveh_disthelper(out, curveh, vehfollist,vehlist, lane, meas, platooninfo):
    #note that this can still potentially fail in some special cases:
    #   say you have two followers, one is directly behind you, and then the other followers behind the person behind you. The first follower is only there for a short time, 
    # and then they change lanes. Then the person behind them gets very close to you. This algorithm will put the 2nd follower first, when they should be second, because we are 
    #computing the average distances to the followers. 
    
    #circular dependencies will always have the offending vehicle added in the beginning of the loop. 
    
    #this can fail to give a correct order in some weird cases, where we can't compare all followers, and we also can't compare all followers to a single leader. 
    
    #so some edge cases potentially wrong but overall I think this should be pretty robust. 
    
    #in this rewritten version of the original function, we don't assign distance scores, instead we get all the followers, sort them and add them, and then repeat. So you can never have a follower
    #which is ahead of you. Any circular dependencies will result in 
    
    #curveh - vehicles are sorted relative to this vehicle 
    
    #given an initial vehicle and list of vehicles to add, gets the distance of each trajectory from the initial vehicle, and then 
    #sorts all vehicles based on this distance. 
    distlist = {} #initialized as 0 because the curveh is 0 distance from itself. 
    curveht_nstar = platooninfo[curveh][0]
    out = [curveh]
    
    newfolveh = set()
    curmeas = meas[curveh]
    curmeas = curmeas[curmeas[:,7]==lane]
    for i in vehfollist: 
        #first need to get times when vehicle is following the curveh. 
        temp = meas[i]
        temp = temp[temp[:,7]==lane]
#        print(curveh)
#        print(i)
        lead,fol = overlaphelp(curmeas,temp) #something is wrong with overlaphelp it seems like its not working properly 
        
        curdist = np.mean(lead[:,2] - fol[:,2])
        distlist[i] = curdist #
        
        curfolveh = np.unique(temp[:,5])
#        curfolveh = platooninfo[i][-1][1] #here 
        for j in curfolveh: 
            if j == 0:
                continue 
            if j in vehlist: 
                if j not in vehfollist and j not in out:
                    newfolveh.add(j)
    
    out2 = list(distlist.keys())
    out2 = sorted(out2, key = lambda veh: distlist[veh])
    curlen = len(newfolveh)
    while curlen>0:
        #check if all new followers can be sorted according to a single follower 
        for i in newfolveh: 
            curmeas = meas[i]
            curmeas = curmeas[curmeas[:,7]==lane]
            distlist = {i:0}
            for j in newfolveh: 
                if j==i:
                    continue
                temp = meas[j]
                temp = temp[temp[:,7]==lane]
                
                lead,fol = overlaphelp(curmeas,temp)
                if len(lead) == 0: #failed for vehicle j, so try for other vehicles 
                    break
                else: 
                    curdist = np.mean(lead[:,2]-fol[:,2])
                    distlist[j] = curdist 
            else: 
                #no break in j loop means we succeeded for vehicle i 
                out2 = distlist.keys()
                out2 = sorted(out2,key = lambda veh: distlist[veh]) #sort the new vehicles 
                
#                out.extend(out2) #add all the new vehicles. now we need to get all the new vehicles 
                #to prevent any orders being off by 1, we always check if the order makes sense wehn we add a new vehicle 
                for k in out2: 
                    lastveh = out[-1]
                    lastmeas = meas[lastveh]
                    lastmeas = lastmeas[lastmeas[:,7]==lane]
                    temp = meas[k]
                    temp = temp[temp[:,7]==lane]
                    last, cur = overlaphelp(lastmeas,temp)
                    if len(last) == 0: #nbothing to check 
                        out.append(k)
                    elif np.mean(last[:,2]-cur[:,2]) > 0: #if this is positive it means the order is right 
                        out.append(k)
                    else: 
                        out.insert(-1,k) #it's before the last one in this case. 
                
                oldnewfolveh = newfolveh.copy() #copy of old we will iterate over this and make the new
                newfolveh = set()
                for k in oldnewfolveh: 
                    temp = meas[k]
                    temp = temp[temp[:,7]==lane]
                    curfolveh = np.unique(temp[:,5])
        #            curfolveh = platooninfo[i][-1][1] #and here 
                    for l in curfolveh: 
                        if l == 0:
                            continue 
                        if l in vehlist: #has to be a vehicle we are sorting 
                            if l not in out: #can't be a vehicle already sorted
                                newfolveh.add(l)
                curlen = len(newfolveh)
                break #this is beraking the first loop over i 
        else: #this else is with the first loop over i 
        #this means we weren't able to sort the new vehicles with respect to each other, so we'll try to sort them with respect to one of the leaders already added. 
            #first we have to figure out what leaders we can potentially use 
            for i in range(len(out)): #we will go backwards over everything in out 
                
                curveh = out[int(-(i+1))] #go backwards 
                curmeas = meas[curveh]
                curmeas = curmeas[curmeas[:,7]==lane]
                lasttime = curmeas[-1,1]
                distlist = {}
                
                for j in newfolveh:
                    temp = meas[j]
                    temp = temp[temp[:,7]==lane]
                    if temp[0,1] > lasttime:  #simple check if failed to potentially save a lot of time 
                        break
                    
                    lead,fol = overlaphelp(curmeas,temp)
                    if len(lead) == 0:  #failed 
                        break
                    else: 
                        curdist = np.mean(lead[:,2] - fol[:,2])
                        distlist[j] = curdist
                else: #succeeded
                    out2 = distlist.keys()
                    out2 = sorted(out2,key = lambda veh: distlist[veh]) #sort the new vehicles 
                    
#                    out.extend(out2) #add all the new vehicles. now we need to get all the new vehicles 
                    for k in out2: 
                        lastveh = out[-1]
                        lastmeas = meas[lastveh]
                        lastmeas = lastmeas[lastmeas[:,7]==lane]
                        temp = meas[k]
                        temp = temp[temp[:,7]==lane]
                        last, cur = overlaphelp(lastmeas,temp)
                        if len(last) == 0: #nbothing to check 
                            out.append(k)
                        elif np.mean(last[:,2]-cur[:,2]) > 0: #if this is positive it means the order is right 
                            out.append(k)
                        else: 
                            out.insert(-1,k) #it's before the last one in this case. 
                    
                    oldnewfolveh = newfolveh.copy() #copy of old we will iterate over this and make the new
                    newfolveh = set()
                    for k in oldnewfolveh: 
                        temp = meas[k]
                        temp = temp[temp[:,7]==lane]
                        curfolveh = np.unique(temp[:,5])
            #            curfolveh = platooninfo[i][-1][1] #and here 
                        for l in curfolveh: 
                            if l == 0:
                                continue 
                            if l in vehlist: #has to be a vehicle we are sorting 
                                if l not in out: #can't be a vehicle already sorted
                                    newfolveh.add(l)
                    curlen = len(newfolveh)
                    break #this is beraking the first loop over i 
                    
            else: #this is attached to the first loop over i, it means we have no idea how to sort the vehicles in newfolveh. 
                #in this case what we'll do is throw a warning, and not do anything with the vehicles, so they will get put into leftover. 
                print('we werent able to sort some vehicles, they will be handled as leftovers') #this should only happen rarely for a dataset with congestion in it. 
                oldnewfolveh = newfolveh.copy() #copy of old we will iterate over this and make the new
                newfolveh = set()
                for k in oldnewfolveh: 
                    temp = meas[k]
                    temp = temp[temp[:,7]==lane]
                    curfolveh = np.unique(temp[:,5])
        #            curfolveh = platooninfo[i][-1][1] #and here 
                    for l in curfolveh: 
                        if l == 0:
                            continue 
                        if l in vehlist: #has to be a vehicle we are sorting 
                            if l not in out: #can't be a vehicle already sorted
                                newfolveh.add(l)
                curlen = len(newfolveh)
                

    
    return out


def approx_hess(p,*args,gradfn = None, curgrad = None, **kwargs):
    #input the current point p, function to calculate the gradient gradfn with call signature 
    #grad = gradfn(p,*args,*kwargs)
    #and we will compute the hessian using a forward difference approximation. 
    #this will use n+1 gradient evaluations to calculate the hessian. 
    #you can pass in the current grad if you have it, this will save 1 gradient evaluation. 
    n = len(p)
    hess = np.zeros((n,n))
    if curgrad is None:
        grad = gradfn(p,*args,*kwargs) #calculate gradient for the unperturbed parameters
    else: 
        grad = curgrad
#    grad = np.asarray(grad) #just pass in a np array not a list...if you want to pass in list then you need to convert to np array here. 
    eps = 1e-8 #numerical differentiation stepsize
    for i in range(n):
        pe = p.copy()
        pe[i] += eps #perturbed parameters for parameter n
        gradn = gradfn(pe,*args,**kwargs) #gradient for perturbed parameters
#        gradn = np.asarray(gradn) #just pass in a np array not a list...if you want to pass in list then you need to convert to np array here. 
        hess[:,i] = gradn-grad #first column of the hessian without the 1/eps

    hess = hess*(1/eps)
    hess = .5*(hess + np.transpose(hess))
    return hess


def SPSA_grad(p,objfn, *args,q = 1, ck = 1e-8, **kwargs):
    #defines the SPSA gradient approximation. This can be used in place of a gradient function in any optimization algorithm; it is suggested to be used in a gradient descent algorithm with 
    #a fixed step length (see spall 1992)
    #each gradient approximation uses 2 objective evaluations. There are q gradient approximations total, and it returns the average gradient. 
    #therefore the functino uses 2q total objective evaluations; finite differences uses n+1 (n) evaluations, where n is the number of parameters. #(adjoint would use 2 (1) ), where 
    #you can possibly save 1 evaluation if you pass in the current objective evaluation (which is not done in this code). 
    #variable names follow the convention gave in spall 1992; except we call the c_k eps instead
    n  = len(p)
    grad = np.zeros((q,n)) #q rows of gradient with n columns
    eps = ck #numerical stepsize
    p = np.asarray(p) #need parameters to be an np array here
    for i in range(q): #
        delta = 2*ss.bernoulli.rvs(.5,size=n)-1 #symmetric bernoulli variables 
        pp = p + eps*delta #reads as p plus
        pm = p - eps*delta # p minus
        yp = objfn(pp,*args,**kwargs)
        ym = objfn(pm,*args,**kwargs)
        grad[i,:] = (yp-ym)/(2*eps*delta) #definition of the SPSA to the gradient
    
    grad = np.mean(grad,0) #average across the gradients 
    
    return grad



def pgrad_descent(fnc, fnc_der, fnc_hess, p, bounds, linesearch, args, t = 0,  eps = 1e-5, epsf = 1e-5, maxit = 1e3, der_only = False, BBlow = 1e-9, BBhi = 1,srch_type = 0,proj_type = 0,**kwargs):
    #minimize a scalar function with bounds using gradient descent
    #fnc - objective 
    #fnc_der - derivative or objective and derivative
    #fnc_hess - hessian (unused)
    #p - initial guess
    #linesearch - linesearch function 
    #bounds - box bounds for p 
    #args - arguments that are passed to fnc, fnc_der, fnc_hess
    
    #t = 0 - if 1 , we will use a non-monotone line search strategy, using the linesearch function to determine sufficient decrease 
    #otherwise, if t = 0 we will just use the linesearch function. 
    
    #eps = 1e-5 - termination if relative improvement is less than eps
    #epsf =1e-5 - termination if gradient norm is less than epsf
    #maxit = 1e3 - termination if iterations are more than maxit
    #der_only indicates fnc_der only gives derivative
    #kwargs - any special arguments for linesearch need to be in kwargs
    
    #srch_type = 0 - scale search direction either by norm of gradient (0), using barzilai borwein scaling (1), or no scaling (any other value)
    #what scaling works best depends on the problem. for example, BB scaling works very well for the rosenbrock function. 
    #for the car-following calibration, BB scaling seems to work poorly (I think because you often take small steps? )
    #in other problems, the scaling by norm of the gradient helps; for car following calibration it doesnt seem to help. 
    
    #proj_type = 0 - either project before the linesearch (0), or project in each step of the line search (1)
    #note that the fixedstep linesearch should use proj_type = 1; nonmonotone uses projtype = 0. backtrack and weakwolfe can use either. 
    #which projection type works better depends on the problem. 
    
    #in general, you would expect that srch_type = 1, proj_type = 1 would work the best (BB scaling with projection at every linesearch step).
    if der_only: 
        def fnc_objder(p, *args): 
            obj = fnc(p, *args)
            grad = fnc_der(p,*args)
            
            return obj, grad
    else: 
        fnc_objder = fnc_der
    
    obj, grad = fnc_objder(p, *args) #objective and gradient
    n_grad = np.linalg.norm(grad) #norm of gradient
    diff = 1 #checks reduction in objective (termination)
    iters = 1 #number of iterations (termination)
    totobjeval = 1 #keeps track of total objective and gradient evaluations
    totgradeval = 1
    
    if t != 0: 
        watchdogls = linesearch 
        linesearch = watchdog
#        ########compute the search direction in this case.....################ #actually don't do this 
#        temp = grad
#        if srch_type ==0: 
#            temp = temp/n_grad
#        if proj_type ==0: #each project first, then you won't have to project during line search 
#            d = projection(p-temp,bounds)-p #search direction for the projected gradient
#        else: 
#            d = -temp #search directino without projection
#        #########################################################################
        past = [[p, obj, grad],t+1] #initialize the past iterates for monotone 
    else: 
        watchdogls = None
        past = [None] #past will remain None unless we are doing the nonmonotone line search 

    s = [1] #initialize BB scaling 
    y = [1]
    
    while diff > eps and n_grad > epsf and iters < maxit:
#        print(obj)
        #do the scaling type; either scale by norm of gradient, using BB scaling, or no scaling 
        temp = grad
#        if srch_type ==0 or iters ==1:  #scale by norm of gradient
        if srch_type ==0: 
            temp = temp/n_grad
        elif srch_type ==1:  #BB scaling 
            BBscaling = np.matmul(s,y)/np.matmul(y,y) #one possible scaling 
#            BBscaling = np.matmul(s,s)/np.matmul(s,y) #this is the other possible scaling you can use 
#            if np.isnan(BBscaling): #don't need this 
#                BBscaling = 1/n_grad
#            print(BBscaling)
            if BBscaling < 0: 
                BBscaling = BBhi
            elif BBscaling < BBlow:
                BBscaling = BBlow
            elif BBscaling > BBhi:
                BBscaling = BBhi
            temp = BBscaling*temp
        #otherwise, there will be no scaling and the search direction will simply be -grad
        
        if proj_type ==0: #each project first, then you won't have to project during line search 
            d = projection(p-temp,bounds)-p #search direction for the projected gradient
        else: 
            d = -temp #search directino without projection
            
        if past[-1] == 0: #in this case we need to remember the search direction of the iterate; if past[-1] == 0 it means we might have to return to that point in the non monotone search. 
            past[0].append(d) #append search direction corresponding to the iterate 
            if past[0][2][0] == None: #depending on what watchdogls is, we  may need to update the current gradient as well. 
                past[0][2] = grad
            
#        dirder = np.matmul(grad,d) #directional derivative
        pn, objn, gradn, hessn, objeval, gradeval = linesearch(p,d,obj,fnc,fnc_objder,grad, args, iters, bounds, past, watchdogls, proj_type = proj_type, t = t, **kwargs)

        if gradn[0] == None: #if need to get new gradient
            objn, gradn = fnc_objder(pn,*args)
            totobjeval += 1
            totgradeval +=1
        
        if srch_type ==1:
            s = pn-p #definition of s and y for barzilai borwein scaling 
            y = gradn-grad
            
        #update iterations and current values 
        iters += 1
        totobjeval += objeval
        totgradeval += gradeval
        
        diff = abs(obj-objn)/obj #relative reduction in objective
        p = pn
        obj = objn
        grad = gradn 
        n_grad = np.linalg.norm(grad)
    #report reason for termination
    if n_grad <= epsf:
        exitmessage = 'Norm of gradient reduced to '+str(n_grad)
    elif diff <= eps: 
        exitmessage = 'Relative reduction in objective is '+str(diff)
    elif iters == maxit: 
        exitmessage = 'Reached '+str(maxit)+' iterations'
    
    if past[-1] != None: #in the case we did a non monotone search we have some special termination conditions (these take place inside watchdog function) and need an extra step to report the solution
        if past[0][1] < obj: 
            obj = past[0][1]
            p = past[0][0]
    out = []
    outdict = {}
    out.append(p)
    out.append(obj)
    outdict['grad'] = grad
    outdict['task'] = exitmessage
    outdict['gradeval'] = totgradeval
    outdict['objeval'] = totobjeval
    outdict['iter'] = iters
    out.append(outdict)
    
    return out

def pgrad_descent2(fnc, fnc_der, fnc_hess, p, bounds, linesearch, args, t = 0, eps = 1e-5, epsf = 1e-5, 
                   maxit = 1e3, der_only = False, BBlow = 1e-9, BBhi = 1, srch_type = 0,proj_type = 0,**kwargs):
    #this can be used for nmbacktrack. Otherwise you can use watchdog which is a different nonmonotone strategy that is called with pgrad_descent. This combined with nmbactrack typically works the best. 
    #minimize a scalar function with bounds using gradient descent
    #fnc - objective 
    #fnc_der - derivative or objective and derivative
    #fnc_hess - hessian (unused)
    #p - initial guess
    #linesearch - linesearch function 
    #bounds - box bounds for p 
    #args - arguments that are passed to fnc, fnc_der, fnc_hess
    
    #t = 0 - if 1 , we will use a non-monotone line search strategy, using the linesearch function to determine sufficient decrease 
    #otherwise, if t = 0 we will just use the linesearch function. 
    
    #eps = 1e-5 - termination if relative improvement is less than eps
    #epsf =1e-5 - termination if gradient norm is less than epsf
    #maxit = 1e3 - termination if iterations are more than maxit
    #der_only indicates fnc_der only gives derivative
    #BBlow, BBhi - lower and upper bounds for the stepsize given by BB scaling. 
    #kwargs - any special arguments for linesearch need to be in kwargs (adjust the parameters of the linesearch)
    
    #srch_type = 0 - scale search direction either by norm of gradient (0), using barzilai borwein scaling (1), or no scaling (any other value)
    #in general, BB scaling will work best, but you may need to adjust the safeguarding parameters; calibration seems to need BBlow very small, at least for the current loss function. 
    #note there are two different types of BB scaling, <s,y>/<y,y> or <s,s>/<s,y>, I think the first works better in this case. 
    
    #proj_type = 0 - either project before the linesearch (0), or project in each step of the line search (1)
    #note that the fixedstep linesearch should use proj_type = 1; nonmonotone uses projtype = 0. backtrack and weakwolfe can use either. 
    #which projection type works better depends on the problem. 
    
    #in general, you would expect that srch_type = 1, proj_type = 1 would work the best (BB scaling with projection at every linesearch step).
    
    ############overview of different algorithms##############
    
    #linesearches - 
    #fixed step : choose a constant step length that decreases with some power of the iterations
    #backtrack2 : choose a step length based on backtracking armijo linesearch with safeguarded interpolation. requires only objective evaluations
    #weakwolfe2: can choose a step length that satisfies either strong or weak wolfe conditions, uses interpolation and safeguarding. Requires both gradient and objective evaluations
    #two different nonmonotone searches; each of which can be based around either of the above two line searches (explained more below)
    
    #algorithms - 
    #pgrad_descent: can input keyword parameter t = n to use nonmonotone linesearch watchdog, which will take up to n relaxed steps before using some linesearch to enforce sufficient decrease 
    #pgrad_descent2: can call both nmbacktrack, and nmweakwolfe. These are nonmonotone linesearches for the corresponding program, which relax the sufficient decrease condition 
    #by only enforcing the decrease w.r.t the maximum of the past t = n iterations. 
    #in general, I have found pgrad_descent2 with nmbacktrack to work the best for the calibration problem. 
    #using watchdog (pgrad_descent with t \neq 0) seems to be worse than nmbacktrack, but better than nmweakwofe. So you can do watchdog for wolfe linesearch, otherwise use nmbacktrack. 
    
    #for any of the gradient descent algorithms, you definitly want to use srch_type = 1 to use BB scaling. You may have to adjust the safeguarding parameters to achieve good results. 
    #proj_type = 0 is the default. Sometimes you may find proj_type = 1 to work better, but in general proj_type = 0 (project the search direction only once) is much better. 
    ################################################################
    
    if der_only: 
        def fnc_objder(p, *args): 
            obj = fnc(p, *args)
            grad = fnc_der(p,*args)
            
            return obj, grad
    else: 
        fnc_objder = fnc_der
    
    obj, grad = fnc_objder(p, *args) #objective and gradient
    n_grad = np.linalg.norm(grad) #norm of gradient
    diff = 1 #checks reduction in objective (termination)
    iters = 1 #number of iterations (termination)
    totobjeval = 1 #keeps track of total objective and gradient evaluations
    totgradeval = 1
    
    #####################deprecated section from pgrad_descent#############
#    if t != 0: 
#        watchdogls = linesearch 
#        linesearch = watchdog
##        ########compute the search direction in this case.....################ #actually don't do this 
##        temp = grad
##        if srch_type ==0: 
##            temp = temp/n_grad
##        if proj_type ==0: #each project first, then you won't have to project during line search 
##            d = projection(p-temp,bounds)-p #search direction for the projected gradient
##        else: 
##            d = -temp #search directino without projection
##        #########################################################################
#        past = [[p, obj, grad],0] #initialize the past iterates for monotone 
#    else: 
#        watchdogls = None
#        past = [None] #past will remain None unless we are doing the nonmonotone line search 
    #####################################
    
    past = [obj] #this is how we initialize the past. In this code, we will have special functions to handle the non-monotone, 
    pastp = [p] #whereas before we were using watchdog which relied on some existing line search. 
    

    s = [1] #initialize BB scaling 
    y = [1]
    
    while diff > eps and n_grad > epsf and iters < maxit:
#        print(n_grad)
        #do the scaling type; either scale by norm of gradient, using BB scaling, or no scaling 
        temp = grad
#        if srch_type ==0 or iters ==1:  #scale by norm of gradient
        if srch_type ==0: 
            temp = temp/n_grad
        elif srch_type ==1:  #BB scaling 
            BBscaling = np.matmul(s,y)/np.matmul(y,y) #one possible scaling 
#            BBscaling = np.matmul(s,s)/np.matmul(s,y) #this is the other possible scaling you can use 
            if BBscaling < 0: 
                BBscaling = BBhi
            elif BBscaling < BBlow:
                BBscaling = BBlow
            elif BBscaling > BBhi:
                BBscaling = BBhi
            temp = BBscaling*temp
        #otherwise, there will be no scaling and the search direction will simply be -grad
        
        if proj_type ==0: #each project first, then you won't have to project during line search 
            d = projection(p-temp,bounds)-p #search direction for the projected gradient
        else: 
            d = -temp #search directino without projection
            
        ########deprecated
#        if past[-1] == 0: #in this case we need to remember the search direction of the iterate; if past[-1] == 0 it means we might have to return to that point in the non monotone search. 
#            past[0].append(d) #append search direction corresponding to the iterate 
#            if past[0][2][0] == None: #depending on what watchdogls is, we  may need to update the current gradient as well. 
#                past[0][2] = grad
        #########deprecated 
#        dirder = np.matmul(grad,d) #directional derivative #deprecated
        pn, objn, gradn, hessn, objeval, gradeval = linesearch(p,d,obj,fnc,fnc_objder,grad, args, iters, bounds, past, pastp, t, proj_type = proj_type, **kwargs)

        if gradn[0] == None: #if need to get new gradient
            objn, gradn = fnc_objder(pn,*args)
            totobjeval += 1
            totgradeval +=1
        
        if srch_type ==1:
            s = pn-p #definition of s and y for barzilai borwein scaling 
            y = gradn-grad
            
        #update iterations and current values 
        iters += 1
        totobjeval += objeval
        totgradeval += gradeval
        
        diff = abs(obj-objn)/obj #relative reduction in objective
        p = pn
        obj = objn
        grad = gradn 
        n_grad = np.linalg.norm(grad)
    #report reason for termination
    if n_grad <= epsf:
        exitmessage = 'Norm of gradient reduced to '+str(n_grad)
    elif diff <= eps: 
        exitmessage = 'Relative reduction in objective is '+str(diff)
    elif iters == maxit: 
        exitmessage = 'Reached '+str(maxit)+' iterations'
    
    if obj > min(past):
        ind = np.argmin(past)
        obj = past[ind]
        p = pastp[ind]
    out = []
    outdict = {}
    out.append(p)
    out.append(obj)
    outdict['grad'] = grad
    outdict['task'] = exitmessage
    outdict['gradeval'] = totgradeval
    outdict['objeval'] = totobjeval
    outdict['iter'] = iters
    out.append(outdict)
    
    return out

def SPSA(fnc, unused1, unused2, p, bounds, unused3, args, q = 1, maxit = 1e3, maxs = 50, **kwargs):
    #minimize a scalar function with bounds using SPSA
    #fnc - objective 
    #p - initial guess
    #bounds - box bounds for p 
    #args - arguments that are passed to fnc 
    #maxit = 1e3 - termination if iterations are more than maxit
    #q = 1 - number of times to do the SPSA gradient (q = 1 is a single realization of the stochastic perturbation \delta_k)
    #kwargs - can pass in kwargs to control constants for step length

    
#    obj = fnc(p, *args) #objective and gradient
    grad = SPSA_grad(p,fnc,*args)
    iters = 1 #number of iterations (termination)
    totobjeval = 2*q #keeps track of total objective and gradient evaluations
    totgradeval = 0
    diff = 0 
    stuck = 0
    
    while iters < maxit and stuck <maxs:
#        print(obj)
        d = -grad #search direction 
#        dirder = np.matmul(grad,d) #directional derivative
        pn, objn, gradn, hessn, objeval, gradeval = fixedstep(p,d,None,None,None,None,None,iters,bounds,**kwargs)
        
        if gradn[0] == None: #if need to get new gradient
            gradn = SPSA_grad(pn,fnc,*args)
            totobjeval += 2*q
            
        #update iterations and current values 
        diff = np.linalg.norm(pn-p)
        if diff ==0:
            stuck += 1
        else:
            stuck = 0
        iters += 1        
        p = pn
        grad = gradn 
        
    #report reason for termination
    if iters == maxit: 
        exitmessage = 'Reached '+str(maxit)+' iterations'
    if stuck ==maxs: 
        exitmessage = 'Unable to make progress in '+str(maxs)+' iterations'
    
    obj = fnc(p,*args)
    
    out = []
    outdict = {}
    out.append(p)
    out.append(obj)
    outdict['grad'] = grad
    outdict['task'] = exitmessage
    outdict['gradeval'] = totgradeval
    outdict['objeval'] = totobjeval+1
    outdict['iter'] = iters
    out.append(outdict)
    
    return out

def SQP(fnc, fnc_der, fnc_hess1, p, bounds, linesearch, args, t = 0, hessfn = False, eps = 1e-5, epsf = 1e-5, 
         maxit = 1e3, der_only = False, BBlow = 1e-9, BBhi = 1, proj_type = 0, hesslow = 1e-4, hesshi = 100, **kwargs):
    #fnc - objective 
    #fnc_der - derivative or objective and derivative
    #fnc_hess - input a function only returning the gradient with keyword hessfn=False, or you can input a function that will compute the hessian directly. 
    #p - initial guess
    #linesearch - linesearch function 
    #bounds - box bounds for p 
    #*args - arguments that are passed to fnc, fnc_der, fnc_hess
    #if hessfn is true fnc_hess1 gives explicit hessian. Otherwise the hessian will be approximated, and fnc_hess1 contains a function that will return gradient
    #eps = 1e-5 - termination if relative improvement is less than eps
    #epsf =1e-5 - termination if gradient norm is less than epsf
    #maxit = 1e3 - termination if iterations are more than maxit
    #der_only indicates fnc_der only gives derivative
    #kwargs - any special arguments for linesearch need to be in kwargs
    
    if der_only: 
        def fnc_objder(p, *args): 
            obj = fnc(p, *args)
            grad = fnc_der(p,*args)
            
            return obj, grad
    else: 
        fnc_objder = fnc_der
    
    if hessfn: 
        fnc_hess = fnc_hess1
    else: 
        def fnc_hess(p, args, curgrad, gradfn = fnc_hess1):
            hess = approx_hess(p,*args,gradfn = fnc_hess1,curgrad = curgrad)
            return hess
            
    obj, grad = fnc_objder(p, *args) #objective and gradient
#    hess = fnc_hess(p,*args, grad) #do it at top of loop 
    n_grad = np.linalg.norm(grad) #norm of gradient
    diff = 1 #checks reduction in objective (termination)
    iters = 1 #number of iterations (termination)
    totobjeval = 1 #keeps track of total objective and gradient evaluations
    totgradeval = 1
#    tothesseval = 1
    
    past = [obj] #this is how we initialize the past. In this code, we will have special functions to handle the non-monotone, 
    pastp = [p] #whereas before we were using watchdog which relied on some existing line search. 
    
    if t != 0: 
        watchdogls = linesearch 
        linesearch = watchdog
#        ########compute the search direction in this case.....################ #actually don't do this 
#        temp = grad
#        if srch_type ==0: 
#            temp = temp/n_grad
#        if proj_type ==0: #each project first, then you won't have to project during line search 
#            d = projection(p-temp,bounds)-p #search direction for the projected gradient
#        else: 
#            d = -temp #search directino without projection
#        #########################################################################
        past = [[p, obj, grad],t+1] #initialize the past iterates for monotone 
    else: 
        watchdogls = None
        past = [None] #past will remain None unless we are doing the nonmonotone line search 
    

    s = [1] #initialize BB scaling 
    y = [1]
    cur = 1e-2 #very small regularization prevents singular matrix
    while diff > eps and n_grad > epsf and iters < maxit:
        
#        cur = cur*2
#        print(obj)
        #do the scaling type; either scale by norm of gradient, using BB scaling, or no scaling 
        hess = fnc_hess(p, args, grad) #get new hessian
        hess = hess + cur*np.identity(len(p)) #regularization
        safeguard = False
        d = -np.linalg.solve(hess,grad) #newton search direction
        dnorm = np.linalg.norm(d)
#        print(np.matmul(-grad,d))
        if dnorm >= hesshi*n_grad: #safeguards on hessian being poorly conditioned
            d = -grad
            safeguard = True
        
        elif np.matmul(-grad,d) <= hesslow*n_grad*dnorm: #safeguard on hessian not giving a descent direction 
            d = -grad
            safeguard = True

#        print(safeguard)
#        if srch_type ==0 or iters ==1:  #scale by norm of gradient
        if safeguard:  #BB scaling 
#            cur= cur*1.5
#            print('hi')
            BBscaling = np.matmul(s,y)/np.matmul(y,y) #one possible scaling 
#            BBscaling = np.matmul(s,s)/np.matmul(s,y) #this is the other possible scaling you can use 
            if BBscaling < 0: 
                BBscaling = BBhi
            elif BBscaling < BBlow:
                BBscaling = BBlow
            elif BBscaling > BBhi:
                BBscaling = BBhi
            d = BBscaling*d
#        else: 
#            cur = cur/1.5
        #otherwise, there will be no scaling and the search direction will simply be -grad
        
        if proj_type ==0: #each project first, then you won't have to project during line search 
            d = projection(p+d,bounds)-p #search direction for the projected gradient
        
        if past[-1] == 0: #in this case we need to remember the search direction of the iterate; if past[-1] == 0 it means we might have to return to that point in the non monotone search. 
            past[0].append(d) #append search direction corresponding to the iterate 
            if past[0][2][0] == None: #depending on what watchdogls is, we  may need to update the current gradient as well. 
                past[0][2] = grad

        pn, objn, gradn, hessn, objeval, gradeval = linesearch(p,d,obj,fnc,fnc_objder,grad, args, iters, bounds, past, watchdogls, proj_type = proj_type, t = t, **kwargs)

        if gradn[0] == None: #if need to get new gradient
            objn, gradn = fnc_objder(pn,*args)
            totobjeval += 1
            totgradeval +=1
            
        
        
        
        s = pn-p #definition of s and y for barzilai borwein scaling #for safe guarding when needed 
        y = gradn-grad
            
        #update iterations and current values 
        iters += 1 
        totobjeval += objeval
        totgradeval += gradeval
#        tothesseval += 1
        
        diff = abs(obj-objn)/obj #relative reduction in objective
        p = pn
        obj = objn
        grad = gradn 
        n_grad = np.linalg.norm(grad)
        
    if past[-1] != None: #in the case we did a non monotone search we have some special termination conditions (these take place inside watchdog function) and need an extra step to report the solution
        if past[0][1] < obj: 
            obj = past[0][1]
            p = past[0][0]
    #report reason for termination
    if n_grad <= epsf:
        exitmessage = 'Norm of gradient reduced to '+str(n_grad)
    elif diff <= eps: 
        exitmessage = 'Relative reduction in objective is '+str(diff)
    elif iters == maxit: 
        exitmessage = 'Reached '+str(maxit)+' iterations'
        
    out = []
    outdict = {}
    out.append(p)
    out.append(obj)
    outdict['grad'] = grad
    outdict['task'] = exitmessage
    outdict['gradeval'] = totgradeval
    outdict['objeval'] = totobjeval
    outdict['iter'] = iters
    outdict['hesseval'] = iters - 1 #hessian evaluations is iters - 1 
    out.append(outdict)
    
    return out

def SQP2(fnc, fnc_der, fnc_hess1, p, bounds, linesearch, args, t = 0, hessfn = False, eps = 1e-5, epsf = 1e-5, 
         maxit = 1e3, der_only = False, BBlow = 1e-9, BBhi = 1, proj_type = 0, hesslow = 1e-4, hesshi = 100, **kwargs):
    #fnc - objective 
    #fnc_der - derivative or objective and derivative
    #fnc_hess - input a function only returning the gradient with keyword hessfn=False, or you can input a function that will compute the hessian directly. 
    #p - initial guess
    #linesearch - linesearch function 
    #bounds - box bounds for p 
    #*args - arguments that are passed to fnc, fnc_der, fnc_hess
    #if hessfn is true fnc_hess1 gives explicit hessian. Otherwise the hessian will be approximated, and fnc_hess1 contains a function that will return gradient
    #eps = 1e-5 - termination if relative improvement is less than eps
    #epsf =1e-5 - termination if gradient norm is less than epsf
    #maxit = 1e3 - termination if iterations are more than maxit
    #der_only indicates fnc_der only gives derivative
    #kwargs - any special arguments for linesearch need to be in kwargs
    
    if der_only: 
        def fnc_objder(p, *args): 
            obj = fnc(p, *args)
            grad = fnc_der(p,*args)
            
            return obj, grad
    else: 
        fnc_objder = fnc_der
    
    if hessfn: 
        fnc_hess = fnc_hess1
    else: 
        def fnc_hess(p, args, curgrad, gradfn = fnc_hess1):
            hess = approx_hess(p,*args,gradfn = fnc_hess1,curgrad = curgrad)
            return hess
            
    obj, grad = fnc_objder(p, *args) #objective and gradient
#    hess = fnc_hess(p,*args, grad) #do it at top of loop 
    n_grad = np.linalg.norm(grad) #norm of gradient
    diff = 1 #checks reduction in objective (termination)
    iters = 1 #number of iterations (termination)
    totobjeval = 1 #keeps track of total objective and gradient evaluations
    totgradeval = 1
#    tothesseval = 1
    
    past = [obj] #this is how we initialize the past. In this code, we will have special functions to handle the non-monotone, 
    pastp = [p] #whereas before we were using watchdog which relied on some existing line search. 
    

    s = [1] #initialize BB scaling 
    y = [1]
    cur = 1e-4 #very small regularization prevents singular matrix
    while diff > eps and n_grad > epsf and iters < maxit:
        
#        cur = cur*2
#        print(obj)
        #do the scaling type; either scale by norm of gradient, using BB scaling, or no scaling 
        hess = fnc_hess(p, args, grad) #get new hessian
        hess = hess + cur*np.identity(len(p)) #regularization
        safeguard = False
        d = -np.linalg.solve(hess,grad) #newton search direction
        dnorm = np.linalg.norm(d)
#        print(np.matmul(-grad,d))
#        print(dnorm)
        if dnorm >= hesshi*n_grad: #safeguards on hessian being poorly conditioned
            d = -grad
            safeguard = True
        
        elif np.matmul(-grad,d) <= hesslow*n_grad*dnorm: #safeguard on hessian not giving a descent direction 
            d = -grad
            safeguard = True

#        print(safeguard)
#        if srch_type ==0 or iters ==1:  #scale by norm of gradient
        if safeguard:  #BB scaling 
#            cur= cur*1.5
#            print('hi')
            BBscaling = np.matmul(s,y)/np.matmul(y,y) #one possible scaling 
#            BBscaling = np.matmul(s,s)/np.matmul(s,y) #this is the other possible scaling you can use 
            if BBscaling < 0: 
                BBscaling = BBhi
            elif BBscaling < BBlow:
                BBscaling = BBlow
            elif BBscaling > BBhi:
                BBscaling = BBhi
            d = BBscaling*d
#        else: 
#            cur = cur/1.5
        #otherwise, there will be no scaling and the search direction will simply be -grad
        
        if proj_type ==0: #each project first, then you won't have to project during line search 
            d = projection(p+d,bounds)-p #search direction for the projected gradient


        pn, objn, gradn, hessn, objeval, gradeval = linesearch(p,d,obj,fnc,fnc_objder,grad, args, iters, bounds, past, pastp, t, proj_type = proj_type, **kwargs)

        if gradn[0] == None: #if need to get new gradient
            objn, gradn = fnc_objder(pn,*args)
            totobjeval += 1
            totgradeval +=1
            
        
        
        
        s = pn-p #definition of s and y for barzilai borwein scaling #for safe guarding when needed 
        y = gradn-grad
            
        #update iterations and current values 
        iters += 1 
        totobjeval += objeval
        totgradeval += gradeval
#        tothesseval += 1
        
        diff = abs(obj-objn)/obj #relative reduction in objective
        p = pn
        obj = objn
        grad = gradn 
        n_grad = np.linalg.norm(grad)
    #report reason for termination
    if n_grad <= epsf:
        exitmessage = 'Norm of gradient reduced to '+str(n_grad)
    elif diff <= eps: 
        exitmessage = 'Relative reduction in objective is '+str(diff)
    elif iters == maxit: 
        exitmessage = 'Reached '+str(maxit)+' iterations'
    
    if obj > min(past):
        ind = np.argmin(past)
        obj = past[ind]
        p = pastp[ind]
    out = []
    outdict = {}
    out.append(p)
    out.append(obj)
    outdict['grad'] = grad
    outdict['task'] = exitmessage
    outdict['gradeval'] = totgradeval
    outdict['objeval'] = totobjeval
    outdict['iter'] = iters
    outdict['hesseval'] = iters - 1
    out.append(outdict)
    
    return out

def projection(p, bounds):
    n = len(p)
    for i in range(n):
        if p[i] < bounds[i][0]:
            p[i] = bounds[i][0]
        elif p[i] > bounds[i][1]:
            p[i] = bounds[i][1]
    return p

    
def backtrack(p,d,obj,fnc,fnc_objder, grad, args, iters, bounds, *fargs, c1=1e-4, gamma = .5, proj_type = 0, maxLSiter = 40, **kwargs):
    #deprecated; new backtrack2 uses interpolation with safeguarding and achieves better results. 
    #initialization 
    #attempts to satisfy a sufficient decrease condition by considering progressively shorter step lengths. 
    #c1 controls how much of a decrease constitutes a "sufficient" decrease. typical value is c1 = 1e-4
    #gamma controls how much to shorten the step length by. typicaly value is gamma = .5 
    #for calibration problem specifically I have found that using a smaller value like gamma = .2 seems to work better. 
    if proj_type ==0: #projection happens in optimization algorithm
        pn = p + d
        da = d
    else: #need to project every iteration in line search 
        pn = projection(p+d,bounds) 
        da = pn-p 
    
    dirder = np.matmul(grad,da) #directional derivative
    cdirder = c1*dirder
    objn = fnc(pn,*args)
    objeval = 1
    gradeval = 0 
    #backtracking procedure
    while objn > obj + cdirder: #if sufficient decrease condition is not met
        d = gamma*d
        #get new step if proj_type == 0 
        if proj_type ==0:
            cdirder = gamma*cdirder
            pn = p+d
        else: 
            pn = projection(p+d,bounds) #project onto feasible set
            da = pn - p #new search direction
            dirder = np.matmul(grad,da) #directional derivative
            cdirder = c1*dirder #for sufficient decrease condition
            
        
        objn = fnc(pn,*args)
        objeval += 1
        
        #need a way to terminate the linesearch if needed. 
        if objeval > maxLSiter: 
            print('linesearch failed to find a step of sufficient decrease')
            if objn >= obj: #if current objective is worse than original 
                pn = p #return original 
                objn = obj
            break
    
    gradn = [None]
    hessn = [None]  
    
    return pn, objn, gradn, hessn, objeval, gradeval

def backtrack2(p,d,obj,fnc,fnc_objder, grad, args, iters, bounds, *fargs, c1=1e-4, alo = .1, ahi = .9, gamma = .5, proj_type = 0, maxLSiter = 40, **kwargs):
    #this is the current backtracking algorithm, it uses interpolation to define steps.
    #really the only feature still missing is the ability to terminate the search when we are at the desired accuracy. This isn't really an issue for 
    #the calibration problem since we don't need machine epsilon precision, so we'll always terminate in the main algorithm and not ever in the line search. 
    #alo and ahi are safeguarding parameters. default .1 and .9. gamma = .5 is the step size used when the interpolation gives a result outside of the safeguards. 
    #can handle either projection in the algorithm, or projection inside this algorithm at each linesearch step. 
    
    #initialization 
    #attempts to satisfy a sufficient decrease condition by considering progressively shorter step lengths. 
    #c1 controls how much of a decrease constitutes a "sufficient" decrease. typical value is c1 = 1e-4
    #gamma controls how much to shorten the step length by. typicaly value is gamma = .5 
    #for calibration problem specifically I have found that using a smaller value like gamma = .2 seems to work better. 
    if proj_type ==0: #projection happens in optimization algorithm
        pn = p + d
        da = d
    else: #need to project every iteration in line search 
        pn = projection(p+d,bounds) 
        da = pn-p 
    
    dirder = np.matmul(grad,da) #directional derivative
#    cdirder = c1*dirder
    objn = fnc(pn,*args)
    objeval = 1
    gradeval = 0 
    a = 1
    #backtracking procedure
    while objn > obj + c1*dirder: #if sufficient decrease condition is not met
        #gamma is the current modifier to the step length
        #a is the total modifier
        #dirder is the current directional derivative times the step length. 
        #objb is the previous objective value, objn is the current objective value 
        gamman = -dirder*a/(2*(objn-obj-dirder)) #quadratic interpolation
        #safeguards 
#        if gamman < alo: #this is one way to safeguard
#            gamman = alo
#        elif gamman > ahi:
#            gamman = ahi
        if gamman < alo or gamman > ahi:  #this is how the paper recommends to safeguard
            gamman = gamma
        a = gamman*a #modify current step length
        d = gamman*d #modify current direction 
        #get new step if proj_type == 0 
        if proj_type ==0:
            dirder = gamman*dirder
            pn = p+d
        else: 
            pn = projection(p+d,bounds) #project onto feasible set
            da = pn - p #new search direction
            dirder = np.matmul(grad,da) #directional derivative
        
        objn = fnc(pn,*args)
        objeval += 1
        
        #need a way to terminate the linesearch if needed. 
        if objeval > maxLSiter: 
            print('linesearch failed to find a step of sufficient decrease')
            if objn >= obj: #if current objective is worse than original 
                pn = p #return original 
                objn = obj
            break
        
        
    
    gradn = [None]
    hessn = [None]  
    
    return pn, objn, gradn, hessn, objeval, gradeval

def nmbacktrack(p,d,obj,fnc,fnc_objder, grad, args, iters, bounds, past, pastp, t, *fargs, c1=1e-4, alo = .1, ahi = .9, gamma = .5, proj_type = 0, maxLSiter = 40, **kwargs):
    #non monotone backtracking with interpolation and safeguards; this is to be used with the pgrad_descent2 
    #attempts to satisfy a sufficient decrease condition by considering progressively shorter step lengths. 
    #c1 controls how much of a decrease constitutes a "sufficient" decrease. typical value is c1 = 1e-4
    #gamma controls how much to shorten the step length by. typicaly value is gamma = .5 
    #for calibration problem specifically I have found that using a smaller value like gamma = .2 seems to work better. 
    
    ##inputs
    #p - parameters for initial guess 
    #d - search direction (may not be same as gradient due to projection)
    #obj - objective function value 
    #fnc - function to evalate objective
    #fnc_objder - function to evaluate both objective and gradient
    #grad - gradient of objective w.r.t. current parameters
    #args - extra arguments to pass to objective/gradeint function
    #iters - numbers of iterations of optimization alg so far
    #bounds - bounds for parameters, list of tuple for each parameter with lower and upper bounds
    #past - past values of the objective (need this for nonmonotone part)
    #pastp - past values of the parameters
    #t - maximum number of iterations we can go without a sufficient decrease - if this is zero then this is just regular backtracking
    #*fargs  - any extra arguments that may be passed in (this is for other routines since they might have different inputs; in this code it is not used)
    #c1 - parameter controls sufficient decrease, if c1 is smaller, required decrease is also smaller. typically 1e-4 is used 
    #alo - minimum safeguard for interpolated step size, can usually leave as .1
    #ahi - maximum safeguard for interpolated step size, can usually leave as .9 
    #gamma - this is the modification to the step size in case the interpolation fails (typically left as .5)
    #proj_type = 0 - if proj type is zero we project every iteration in optimization algorithm (project search direction), otherwise everytime we get a new step size we will project (proj_type = 1)
    #maxLSiter = 40 - maximum number of iterations of linesearch algorithm before we return the best found value, typically this should find the step in ~2-3 iterations and if you get past 10 or 20 
    #it might mean the search direction has a problem
    
    #outputs
    #pn - new parameter values
    #objn - new objective value
    #gradn - new gradient value (false if not computed)
    #hessn - new hessian value (false if not computed)
    #objeval - number of objective evaluations 
    #gradeval - number of gradient evaluations
    
    #initialization 
    if proj_type ==0: #projection happens in optimization algorithm
        pn = p + d
        da = d
    else: #need to project every iteration in line search 
        pn = projection(p+d,bounds) 
        da = pn-p 
    
    dirder = np.matmul(grad,da) #directional derivative
#    cdirder = c1*dirder
    objn = fnc(pn,*args)
    objeval = 1
    gradeval = 0 
    a = 1
    if iters < t:
        maxobj = obj
    else: 
        maxobj = max(past)
    #backtracking procedure
    while objn > maxobj + c1*dirder: #if sufficient decrease condition is not met
        #gamma is the current modifier to the step length
        #a is the total modifier
        #dirder is the current directional derivative times the step length. 
        #objb is the previous objective value, objn is the current objective value 
        gamman = -dirder*a/(2*(objn-obj-dirder)) #quadratic interpolation
        #safeguards 
#        if gamman < alo: #this is one way to safeguard
#            gamman = alo
#        elif gamman > ahi:
#            gamman = ahi
        if gamman < alo or gamman > ahi:  #this is how the paper recommends to safeguard
#        if True: #deubgging purposes 
            gamman = gamma
        a = gamman*a #modify current step length
        d = gamman*d #modify current direction 
        #get new step if proj_type == 0 
        if proj_type ==0:
            dirder = gamman*dirder
            pn = p+d
        else: 
            pn = projection(p+d,bounds) #project onto feasible set
            da = pn - p #new search direction
            dirder = np.matmul(grad,da) #directional derivative
        
        objn = fnc(pn,*args)
        objeval += 1
        
        #need a way to terminate the linesearch if needed. 
        if objeval > maxLSiter: 
            print('linesearch failed to find a step of sufficient decrease')
            if objn >= obj: #if current objective is worse than original 
                pn = p #return original 
                objn = obj
            break
        
        
    if iters < t:
        past.append(objn) #add the value to the past
        pastp.append(pn)
    else: 
        past.pop(0) #remove the first value
        past.append(objn) #add the new value at the end 
        pastp.pop(0)
        pastp.append(pn)
    gradn = [None]
    hessn = [None]  
    
    return pn, objn, gradn, hessn, objeval, gradeval

def fixedstep(p,d,obj,fnc,fnc_objder,grad,args,iters, bounds, *fargs,c1 = 5e-4,c2 = 1, **kwargs):
    #fixed step length for line search. 
    #c1 is the initial step on the first iteration. 
    #the k^th step is c1 * k**c2
    #default values of c1 = 5e-4, c2 = 1. 
    step = c1*(iters**-c2) #fixed step size
    pn = p +step*d #definition of new solution
    pn = projection(pn,bounds) #project onto the feasible region
    fff = [None]
    
    return pn, fff,fff,fff, 0, 0
    
def weakwolfe(p,d,obj,fnc,fnc_objder, grad, args, iters, bounds, *fargs, c1=1e-4, c2 = .5, eps1 = 1e-1, eps2 = 1e-6, proj_type = 0, maxLSiter = 40, **kwargs):
    #currently deprecated; use weakwolfe2 it has slightly better performance. 
    #fulfills either strong or weak wolfe line search. 
    ######################
    #you just need to change one line in this program and one line in zoom and you can change this between strong wolfe 
    #and weak wolfe. I think strong wolfe tends to be slightly better
    ########################
    
    #for trajectory calibration though it seems backtracking LS works better than using the wolfe conditions, since here the gradient is relatively expensive compared to obj. (even using adjoint)
    
    #c1 - for sufficient decrease condition; lower = easier to accept
    #c2 - for curvature condition ; #higher = easier to accept. 
    #require 0 < c1 < c2 < 1; typically values are 1e-4, .5
    
    #eps1 - initial guess for the steplength ai; should choose something small, like 1e-2
    #eps2 - termination length for zoom function (accuracy for final step length); should choose something small
    
    #proj_type = 0 - either we project before the linesearch (0), or we project every iteration in linesearch (1)
    #maxLSiter = 40 - number of iterations we will attempt 
    
    #aib and amax specify the range of step lengths we will consider; defined between [0,1]
    aib = 0 
    amax = 1
    ai = eps1 #initial guess for step length
    objb = obj #initialize previous objective value 
    
    
    #linedir(a) will return the trial point and search direction for step length a depending on the chosen projection strategy 
    #accepts step length a, 
    #returns new point pn, which is in direction da/a, and has directional derivative dirdera/a
    if proj_type ==0: 
        dirder = np.matmul(grad,d)
        def linedir(a, p=p,d = d, bounds=bounds, dirder = dirder):
            pn = p + a*d 
            da = a*d
            dirdera = a*dirder
            return pn, da, dirdera
    else: 
        def linedir(a, p=p, d=d,  bounds=bounds, grad = grad):
            pn = projection(p+a*d,bounds)
            da = pn-p
            dirdera = np.matmul(grad,da)
            return pn, da, dirdera
    
    objdereval = 0 #count number of objective and gradient evaluations; they are always the same for this strategy. 
    for i in range(maxLSiter): #up to maxLSiter to find the bounds on a
        pn, da, dirdera = linedir(ai) #new point for the line search 
        objn, gradn = fnc_objder(pn,*args) #objective and gradient for the new point 
        objdereval += 1
        
        if objn > obj+c1*dirdera or (objn >= objb and objdereval > 1): #if sufficient decrease is not met then ai must be an upper bound on a good step length 
            out = zoom(aib,ai, eps2, linedir, fnc_objder,args, p,grad, obj, objb, objdereval, c1, c2) #put bounds into zoom to find good step length 
            return out
            
        ddirder = np.matmul(gradn,da)/ai #directional derivative at new point
#        if ddirder >= c2*dirdera/ai: #if weak wolfe conditions are met 
        if abs(ddirder) <= -c2*dirdera/ai: #if strong wolfe conditions are met 

            return pn, objn, gradn, [None], objdereval, objdereval #we are done
            
        if ddirder >= 0:  #I don't really understand this one to be honest. 
            out = zoom(ai,aib, eps2, linedir, fnc_objder,args, p,grad, obj, objn, objdereval, c1 , c2) #put bounds into zoom to find good step length 
            return out
        
        if i == maxLSiter-1:
            print('failed to find suitable range for stepsize')
            if objn >= obj:
                pn = p
                objn = obj
                gradn = grad
            break
        
        #interpolate to get next point 
        if objdereval ==1: #quadratic interpolation first time
            aif = -dirdera*ai/(2*(objn-obj-dirdera)) #next ai to check
        else: 
            d1 = ddirderb+ddirder-3*((objb-objn)/(aib-ai))
            d2 = np.sign(ai-aib)*(d1**2-ddirderb*ddirder)**.5
            aif = ai-(ai-aib)*((ddirder+d2-d1)/(ddirder-ddirderb+2*d2))
            
        if aif < ai or aif < 0 or np.isnan(aif): #if interpolation gives something screwy 
            aif = 2*ai #increase by fixed amount
        aif = min(aif,amax) #next step length must be within range 
        
#        #other strategy 
#        aif = 2* ai
#        if aif > amax: 
#            out = zoom(0,amax, eps2, linedir, fnc_objder,args, p,grad, obj, obj, objdereval, c1 , c2)
#            return out 
            
        #progress iteration
        aib = ai 
        ai = aif 
        ddirderb = ddirder
        objb = objn
        
        
    return pn, objn, gradn, [None], objdereval, objdereval #shouldn't reach here ideally; should terminate due to an if statement 

def zoom(alo, ahi, eps2, linedir, fnc_objder, args, p,grad,obj, objlo, objdereval, c1, c2 ): 
    #most recent zoom function is zoom3
    if abs(ahi-alo) <= eps2: #special case where bounds are already tight enough 
        aj = (alo+ahi)/2 #bisection 
        pn, da, dirdera = linedir(aj) #get new point, new direction, new directional derivative
        objn, gradn = fnc_objder(pn,*args) #evaluate new point 
        objdereval +=1 
        return pn, objn, gradn, [None], objdereval, objdereval
    
    #try modifying so if something satisfies sufficient decrease we will remember it 
    count = 0
    best = (p, obj, grad) #initialize best solution to return if can't satisfy curvature condition 
    while abs(ahi-alo) > eps2: #iterate until convergence to good step length 
        if count ==0:
            aj = (alo+ahi)/2
        count += 1
        pn, da, dirdera = linedir(aj)
        objn, gradn = fnc_objder(pn,*args)
        objdereval +=1 
        
        ddirder = np.matmul(gradn,da)/aj
        if objn > obj + c1*dirdera or objn >= objlo: #if sufficient decrease not met lower the upper bound 
            ahi = aj
        else: 
#            if ddirder >= c2*dirdera/aj: #if weak wolfe conditions are met return the solution 
            if abs(ddirder) <= -c2*dirdera/aj: #if stronge wolfe conditions are met 

                return pn, objn, gradn, [None], objdereval, objdereval 
            if objn < best[1]: #keep track of best solution which only satisfies sufficient decrease #can get rid of this 
                best = (pn, objn, gradn)
            if ddirder*(ahi-alo) >= 0: #otherwise do this 
                ahi = alo
            alo = aj #pretty sure this is supposed to be here. 
        
        if count ==1: #quadratic interpolation first time
            aif = -dirdera*aj/(2*(objn-obj-dirdera)) #next ai to check
        else: 
            d1 = ddirderb+ddirder-3*((objb-objn)/(aib-aj))
            d2 = np.sign(aj-aib)*(d1**2-ddirderb*ddirder)**.5
            aif = aj-(aj-aib)*((ddirder+d2-d1)/(ddirder-ddirderb+2*d2))
            
        if aif < alo or aif > ahi or np.isnan(aif): #if interpolation gives something screwy (this happens occasionally so need safeguard)
            aif = (alo+ahi)/2 # use bisection
        aib = aj
        aj = aif
        ddirderb = ddirder
        objb = objn
        
            
    print('failed to find a stepsize satisfying weak wolfe conditions')
    if objn < best[1]: #if current step is better than the best #y
        best = (pn, objn, gradn) 
    
    return best[0], best[1], best[2], [None], objdereval, objdereval

def weakwolfe2(p,d,obj,fnc,fnc_objder, grad, args, iters, bounds, *fargs, c1=1e-4, c2 = .5, eps1 = 1e-1, eps2 = 1e-6, proj_type = 0, maxLSiter = 20, **kwargs):
    #fulfills either strong or weak wolfe line search. it's currently used as strong wolfe
    #compared to the original wolfe search, this one uses a (safeguarded) quadratic interpolation to give the first trial step for the zoom function; previously this was done using bisection. 
    ######################
    #you just need to change one line in this program and one line in zoom and you can change this between strong wolfe 
    #and weak wolfe. I think strong wolfe tends to be slightly better
    ########################
    
    #for trajectory calibration though it seems backtracking LS works better than using the wolfe conditions, since here the gradient is relatively expensive compared to obj. (even using adjoint)
    #in general we're going to be constrained by the budget, so even though wolfe can give us better steps, we'd rather do more iterations with slightly worse steps at each iteration. 
    #note that the wolfe linesearches require the gradient to be evaluated at every trial step length, whereas backtrack/armijo only requires the objective to be evaluated
    
    #c1 - for sufficient decrease condition; lower = easier to accept
    #c2 - for curvature condition ; #higher = easier to accept. 
    #require 0 < c1 < c2 < 1; typically values are 1e-4, .5 or 1e-4, .9. stronger curvature condition c2 = better steps, but more evaluations 
    
    #eps1 - initial guess for the steplength ai; should choose something small, like 1e-2
    #eps2 - termination length for zoom function (accuracy for final step length); should choose something small
    
    #proj_type = 0 - either we project before the linesearch (0), or we project every iteration in linesearch (1)
    #maxLSiter = 40 - number of iterations we will attempt 
    
    #aib and amax specify the range of step lengths we will consider; defined between [0,1]
    aib = 0 
    amax = 1
    ai = eps1 #initial guess for step length
    objb = obj #initialize previous objective value 
#    dirderb = 0 #initialize directional derivative w.r.t. aib 
    
    #linedir(a) will return the trial point and search direction for step length a depending on the chosen projection strategy 
    #accepts step length a, 
    #returns new point pn, which is in direction da/a, and has directional derivative dirdera/a
    if proj_type ==0: 
        dirder = np.matmul(grad,d)
        def linedir(a, p=p,d = d, bounds=bounds, dirder = dirder):
            pn = p + a*d 
            da = a*d
            dirdera = a*dirder
            return pn, da, dirdera
    else: 
        def linedir(a, p=p, d=d,  bounds=bounds, grad = grad):
            pn = projection(p+a*d,bounds)
            da = pn-p
            dirdera = np.matmul(grad,da)
            return pn, da, dirdera
    
    objdereval = 0 #count number of objective and gradient evaluations; they are always the same for this strategy. 

        
    for i in range(maxLSiter): #up to maxLSiter to find the bounds on a
        pn, da, dirdera = linedir(ai) #new point for the line search 
        objn, gradn = fnc_objder(pn,*args) #objective and gradient for the new point 
        objdereval += 1
        
        if objn > obj+c1*dirdera or (objn >= objb and objdereval > 1): #if sufficient decrease is not met then ai must be an upper bound on a good step length 

            atrial = -dirdera*ai/(2*(objn-obj-dirdera))
            out = zoom3(aib,ai, eps2, linedir, fnc_objder,args, p,grad, obj, objb, objdereval, c1, c2,atrial) #put bounds into zoom to find good step length 
            
            return out
            
        ddirder = np.matmul(gradn,da)/ai #directional derivative at new point
#        if ddirder >= c2*dirdera/ai: #if weak wolfe conditions are met 
        if abs(ddirder) <= -c2*dirdera/ai: #if strong wolfe conditions are met 

            return pn, objn, gradn, [None], objdereval, objdereval #we are done
            
        if ddirder >= 0:  #if the directional derivative is positive it means we went too far; therefore we found an upperbound  

            atrial = -dirdera*ai/(2*(objn-obj-dirdera))
            out = zoom3(ai,aib, eps2, linedir, fnc_objder,args, p,grad, obj, objn, objdereval, c1 , c2, atrial) #put bounds into zoom to find good step length 
            return out
        
        if i == maxLSiter-1:
            print('failed to find suitable range for stepsize')
            if objn >= obj:
                pn = p
                objn = obj
                gradn = grad
            break
        
        #interpolate to get next point 
        if objdereval ==1: #quadratic interpolation first time
            aif = -dirdera*ai/(2*(objn-obj-dirdera)) #next ai to check
        else: 
            d1 = ddirderb+ddirder-3*((objb-objn)/(aib-ai))
            d2 = np.sign(ai-aib)*(d1**2-ddirderb*ddirder)**.5
            aif = ai-(ai-aib)*((ddirder+d2-d1)/(ddirder-ddirderb+2*d2))
            
        if aif < ai or aif < 0 or np.isnan(aif): #if interpolation gives something screwy 
            aif = 2*ai #increase by fixed amount
        aif = min(aif,amax) #next step length must be within range 
        
#        #other strategy 
#        aif = 2* ai
#        if aif > amax: 
#            out = zoom(0,amax, eps2, linedir, fnc_objder,args, p,grad, obj, obj, objdereval, c1 , c2)
#            return out 
            
        #progress iteration
        aib = ai 
        ai = aif 
        ddirderb = ddirder
        objb = objn
#        dirderb = dirdera #we potentially need this for the new trial step for zoom 
        
        
    return pn, objn, gradn, [None], objdereval, objdereval #shouldn't reach here ideally; should terminate due to an if statement 

def zoom3(alo, ahi, eps2, linedir, fnc_objder, args, p,grad,obj, objlo, objdereval, c1, c2, atrial ): 
    #most recent zoom function corresponding to weakwolfe2. 
    if abs(ahi-alo) <= eps2: #special case where bounds are already tight enough 
        aj = (alo+ahi)/2 #bisection 
        pn, da, dirdera = linedir(aj) #get new point, new direction, new directional derivative
        objn, gradn = fnc_objder(pn,*args) #evaluate new point 
        objdereval +=1 
        return pn, objn, gradn, [None], objdereval, objdereval
    
    #try modifying so if something satisfies sufficient decrease we will remember it 
    count = 0
    best = (p, obj, grad) #initialize best solution to return if can't satisfy curvature condition 
    
    if atrial <= alo or atrial >= ahi or np.isnan(atrial):
#        print('safeguard')
        aj = (alo+ahi)/2
    else: 
#        print('not safeguard')
        aj = atrial
    
    while abs(ahi-alo) > eps2: #iterate until convergence to good step length 
        pn, da, dirdera = linedir(aj)
        objn, gradn = fnc_objder(pn,*args)
        objdereval +=1 
        count += 1
        
        ddirder = np.matmul(gradn,da)/aj
        if objn > obj + c1*dirdera or objn >= objlo: #if sufficient decrease not met lower the upper bound 
            ahi = aj
        else: 
#            if ddirder >= c2*dirdera/aj: #if weak wolfe conditions are met return the solution 
            if abs(ddirder) <= -c2*dirdera/aj: #if stronge wolfe conditions are met 

                return pn, objn, gradn, [None], objdereval, objdereval 
            if objn < best[1]: #keep track of best solution which only satisfies sufficient decrease #can get rid of this 
                best = (pn, objn, gradn)
            if ddirder*(ahi-alo) >= 0: #otherwise do this 
                ahi = alo
            alo = aj #pretty sure this is supposed to be here. 
        
        if count ==1: #quadratic interpolation first time
            aif = -dirdera*aj/(2*(objn-obj-dirdera)) #next ai to check
        else: 
            d1 = ddirderb+ddirder-3*((objb-objn)/(aib-aj))
            d2 = np.sign(aj-aib)*(d1**2-ddirderb*ddirder)**.5
            aif = aj-(aj-aib)*((ddirder+d2-d1)/(ddirder-ddirderb+2*d2))
            
        if aif < alo or aif > ahi or np.isnan(aif): #if interpolation gives something screwy (this happens occasionally so need safeguard)
            aif = (alo+ahi)/2 # use bisection
        aib = aj
        aj = aif
        ddirderb = ddirder
        objb = objn
        
            
    print('failed to find a stepsize satisfying weak wolfe conditions')
    if objn < best[1]: #if current step is better than the best #y
        best = (pn, objn, gradn) 
    
    return best[0], best[1], best[2], [None], objdereval, objdereval

def nmweakwolfe(p,d,obj,fnc,fnc_objder, grad, args, iters, bounds, past, pastp, t, *fargs, c1=1e-4, c2 = .5, eps1 = 1e-1, eps2 = 1e-6, proj_type = 0, maxLSiter = 40, **kwargs):
    #fulfills either strong or weak wolfe line search. it's currently used as strong wolfe
    #compared to the original wolfe search, this one uses a (safeguarded) quadratic interpolation to give the first trial step for the zoom function; previously this was done using bisection. 
    ######################
    #you just need to change one line in this program and one line in zoom and you can change this between strong wolfe 
    #and weak wolfe. I think strong wolfe tends to be slightly better
    ########################
    
    #for trajectory calibration though it seems backtracking LS works better than using the wolfe conditions, since here the gradient is relatively expensive compared to obj. (even using adjoint)
    #in general we're going to be constrained by the budget, so even though wolfe can give us better steps, we'd rather do more iterations with slightly worse steps at each iteration. 
    #note that the wolfe linesearches require the gradient to be evaluated at every trial step length, whereas backtrack/armijo only requires the objective to be evaluated
    
    #c1 - for sufficient decrease condition; lower = easier to accept
    #c2 - for curvature condition ; #higher = easier to accept. 
    #require 0 < c1 < c2 < 1; typically values are 1e-4, .5 or 1e-4, .9. stronger curvature condition c2 = better steps, but more evaluations 
    
    #eps1 - initial guess for the steplength ai; should choose something small, like 1e-2
    #eps2 - termination length for zoom function (accuracy for final step length); should choose something small
    
    #proj_type = 0 - either we project before the linesearch (0), or we project every iteration in linesearch (1)
    #maxLSiter = 40 - number of iterations we will attempt 
    
    #aib and amax specify the range of step lengths we will consider; defined between [0,1]
    aib = 0 
    amax = 1
    ai = eps1 #initial guess for step length
    objb = obj #initialize previous objective value 
#    dirderb = 0 #initialize directional derivative w.r.t. aib 
    
    #linedir(a) will return the trial point and search direction for step length a depending on the chosen projection strategy 
    #accepts step length a, 
    #returns new point pn, which is in direction da/a, and has directional derivative dirdera/a
    if proj_type ==0: 
        dirder = np.matmul(grad,d)
        def linedir(a, p=p,d = d, bounds=bounds, dirder = dirder):
            pn = p + a*d 
            da = a*d
            dirdera = a*dirder
            return pn, da, dirdera
    else: 
        def linedir(a, p=p, d=d,  bounds=bounds, grad = grad):
            pn = projection(p+a*d,bounds)
            da = pn-p
            dirdera = np.matmul(grad,da)
            return pn, da, dirdera
    
    objdereval = 0 #count number of objective and gradient evaluations; they are always the same for this strategy. 
    
    if iters < t:
        maxobj = obj
    else: 
        maxobj = max(past)

        
    for i in range(maxLSiter): #up to maxLSiter to find the bounds on a
        pn, da, dirdera = linedir(ai) #new point for the line search 
        objn, gradn = fnc_objder(pn,*args) #objective and gradient for the new point 
        objdereval += 1
        
        if objn > maxobj+c1*dirdera or (objn >= objb and objdereval > 1): #if sufficient decrease is not met then ai must be an upper bound on a good step length 

            atrial = -dirdera*ai/(2*(objn-obj-dirdera))
            out = zoom4(aib,ai, eps2, linedir, fnc_objder,args, p,grad, obj, objb, objdereval, c1, c2,atrial, iters, past, pastp, t, maxobj) #put bounds into zoom to find good step length 
            
            return out
            
        ddirder = np.matmul(gradn,da)/ai #directional derivative at new point
#        if ddirder >= c2*dirdera/ai: #if weak wolfe conditions are met 
        if abs(ddirder) <= -c2*dirdera/ai: #if strong wolfe conditions are met 
            if iters < t:
                past.append(objn) #add the value to the past
                pastp.append(pn)
            else: 
                past.pop(0) #remove the first value
                past.append(objn) #add the new value at the end 
                pastp.pop(0)
                pastp.append(pn)

            return pn, objn, gradn, [None], objdereval, objdereval #we are done
            
        if ddirder >= 0:  #if the directional derivative is positive it means we went too far; therefore we found an upperbound  

            atrial = -dirdera*ai/(2*(objn-obj-dirdera))
            out = zoom4(ai,aib, eps2, linedir, fnc_objder,args, p,grad, obj, objn, objdereval, c1 , c2, atrial, iters, past, pastp, t, maxobj) #put bounds into zoom to find good step length 
            return out
        
        if i == maxLSiter-1:
            print('failed to find suitable range for stepsize')
            if objn >= obj:
                pn = p
                objn = obj
                gradn = grad
            break
        
        #interpolate to get next point 
        if objdereval ==1: #quadratic interpolation first time
            aif = -dirdera*ai/(2*(objn-obj-dirdera)) #next ai to check
        else: 
            d1 = ddirderb+ddirder-3*((objb-objn)/(aib-ai))
            d2 = np.sign(ai-aib)*(d1**2-ddirderb*ddirder)**.5
            aif = ai-(ai-aib)*((ddirder+d2-d1)/(ddirder-ddirderb+2*d2))
            
        if aif < ai or aif < 0 or np.isnan(aif): #if interpolation gives something screwy 
            aif = 2*ai #increase by fixed amount
        aif = min(aif,amax) #next step length must be within range 
        
#        #other strategy 
#        aif = 2* ai
#        if aif > amax: 
#            out = zoom(0,amax, eps2, linedir, fnc_objder,args, p,grad, obj, obj, objdereval, c1 , c2)
#            return out 
            
        #progress iteration
        aib = ai 
        ai = aif 
        ddirderb = ddirder
        objb = objn
#        dirderb = dirdera #we potentially need this for the new trial step for zoom 
        
    if iters < t: #you should never get here but in case you do. 
        past.append(objn) #add the value to the past
        pastp.append(pn)
    else: 
        past.pop(0) #remove the first value
        past.append(objn) #add the new value at the end 
        pastp.pop(0)
        pastp.append(pn)
    return pn, objn, gradn, [None], objdereval, objdereval #shouldn't reach here ideally; should terminate due to an if statement 

def zoom4(alo, ahi, eps2, linedir, fnc_objder, args, p,grad,obj, objlo, objdereval, c1, c2, atrial,iters, past, pastp, t, maxobj ): 
    #zoom that works with the nmweakwolfe 
    if abs(ahi-alo) <= eps2: #special case where bounds are already tight enough 
        aj = (alo+ahi)/2 #bisection 
        pn, da, dirdera = linedir(aj) #get new point, new direction, new directional derivative
        objn, gradn = fnc_objder(pn,*args) #evaluate new point 
        objdereval +=1 
        return pn, objn, gradn, [None], objdereval, objdereval
    
    #try modifying so if something satisfies sufficient decrease we will remember it 
    count = 0
    best = (p, obj, grad) #initialize best solution to return if can't satisfy curvature condition 
    
    if atrial <= alo or atrial >= ahi or np.isnan(atrial):
#        print('safeguard')
        aj = (alo+ahi)/2
    else: 
#        print('not safeguard')
        aj = atrial
    
    while abs(ahi-alo) > eps2: #iterate until convergence to good step length 
        pn, da, dirdera = linedir(aj)
        objn, gradn = fnc_objder(pn,*args)
        objdereval +=1 
        count += 1
        
        ddirder = np.matmul(gradn,da)/aj
        if objn > maxobj + c1*dirdera or objn >= objlo: #if sufficient decrease not met lower the upper bound 
            ahi = aj
        else: 
#            if ddirder >= c2*dirdera/aj: #if weak wolfe conditions are met return the solution 
            if abs(ddirder) <= -c2*dirdera/aj: #if stronge wolfe conditions are met 
                if iters < t: #you should never get here but in case you do. 
                    past.append(objn) #add the value to the past
                    pastp.append(pn)
                else: 
                    past.pop(0) #remove the first value
                    past.append(objn) #add the new value at the end 
                    pastp.pop(0)
                    pastp.append(pn)

                return pn, objn, gradn, [None], objdereval, objdereval 
            if objn < best[1]: #keep track of best solution which only satisfies sufficient decrease #can get rid of this 
                best = (pn, objn, gradn)
            if ddirder*(ahi-alo) >= 0: #otherwise do this 
                ahi = alo
            alo = aj #pretty sure this is supposed to be here. 
        
        if count ==1: #quadratic interpolation first time
            aif = -dirdera*aj/(2*(objn-obj-dirdera)) #next ai to check
        else: 
            d1 = ddirderb+ddirder-3*((objb-objn)/(aib-aj))
            d2 = np.sign(aj-aib)*(d1**2-ddirderb*ddirder)**.5
            aif = aj-(aj-aib)*((ddirder+d2-d1)/(ddirder-ddirderb+2*d2))
            
        if aif < alo or aif > ahi or np.isnan(aif): #if interpolation gives something screwy (this happens occasionally so need safeguard)
            aif = (alo+ahi)/2 # use bisection
        aib = aj
        aj = aif
        ddirderb = ddirder
        objb = objn
        
            
    print('failed to find a stepsize satisfying weak wolfe conditions')
    if objn < best[1]: #if current step is better than the best #y
        best = (pn, objn, gradn) 
        
    if iters < t: #you should never get here but in case you do. 
        past.append(objn) #add the value to the past
        pastp.append(pn)
    else: 
        past.pop(0) #remove the first value
        past.append(objn) #add the new value at the end 
        pastp.pop(0)
        pastp.append(pn)
    
    return best[0], best[1], best[2], [None], objdereval, objdereval

def zoom2(alo, ahi, eps2, linedir, fnc_objder, args, p,grad,obj, objlo, objdereval, c1, c2 ): 
    #deprecated zoom. New zoom function uses interpolation to get next step length; also it will remember past iterates and will attempt to satisfy sufficient decrease only 
    #in the case where it is not possible to satisfy the curvature condition. 
    if abs(ahi-alo) <= eps2: #special case where bounds are already tight enough 
        aj = (alo+ahi)/2 #bisection 
        pn, da, dirdera = linedir(aj) #get new point, new direction, new directional derivative
        objn, gradn = fnc_objder(pn,*args) #evaluate new point 
        objdereval +=1 
        return pn, objn, gradn, [None], objdereval, objdereval
    
    #try modifying so if something satisfies sufficient decrease we will remember it 
        
    while abs(ahi-alo) > eps2: #iterate until convergence to good step length 
        aj = (alo+ahi)/2
        pn, da, dirdera = linedir(aj)
        objn, gradn = fnc_objder(pn,*args)
        objdereval +=1 
        
        
        if objn > obj + c1*dirdera or objn >= objlo: #if sufficient decrease not met lower the upper bound 
            ahi = aj
        else: 
            ddirder = np.matmul(gradn,da)/aj
#            if ddirder >= c2*dirdera/aj: #if weak wolfe conditions are met return the solution 
            if abs(ddirder) <= -c2*dirdera/aj: #if stronge wolfe conditions are met 

                return pn, objn, gradn, [None], objdereval, objdereval
            if ddirder*(ahi-alo) >= 0: #otherwise do this 
                ahi = alo
            alo = aj #in textbook the indentations are wrong but I'm pretty sure this is supposed to be here. 
            
    print('failed to find a stepsize satisfying weak wolfe conditions')
    if objn >= obj:
        pn = p
        objn = obj
        gradn = grad
    
    return pn, objn, gradn, [None], objdereval, objdereval

def watchdog(p,d,obj,fnc,fnc_objder, grad, args, iters, bounds, past, watchdogls, *fargs, t = 3, c0 = 1,  c1 = 1e-4, **kwargs):
    #this can be called with pgrad_descent, but not pgrad_descent2. It sometimes works better than nmbacktrack, but usually is slightly worse. 
    
    #this assumes the search direction has already been projected; i.e. projtype = 0
    
    #in addition to normal calling signature, watchdog accepts: 
    #past - information on the past iterates; we might have to return to those in this algorithm. since past is a list of lists, and we only operate on the inner lists, 
    #past will be updated without the need to explicitly return it. (I'm pretty sure this is correct)
    
    #watchdogls is used to perform linesearches when needed. this can be any linesearch (weak, strong or backtracking). When accepting the steps however, we will only check that the 
    #sufficient decrease conditions are met. 
    
    #c1 = 1e-4 is the parameter for sufficient decrease 
    
    #c0 controls the default step size. It is reasonable to just take this as being 1.
#    print(past)
    if past[1] ==t+1: #special case corresponding to last else of the below main block
        pn3, objn3, gradn3, hessn3, objeval, gradeval = watchdogls(p,d,obj,fnc,fnc_objder,grad,args,iters,bounds,kwargs,c1=c1)
        past[0] = [pn3, objn3, gradn3]
        past[-1] = 0
        return pn3, objn3, gradn3, hessn3, objeval, gradeval
        
        
    elif past[-1] < t: #past[-1] is number of steps taken not satisfying sufficient decrease. t is total number of those steps we are allowed to take. 
#        print('relaxed step')
        pn = p+c0*d #new point 
        objn, gradn = fnc_objder(pn,*args)
        
        dirder = np.matmul(past[0][2], past[0][3])
        
        if objn <= past[0][1] + c1*c0*dirder:  #if we meet the sufficient decrease
#            print('sufficient decrease for relaxed step')
            past[0] = [pn,objn,gradn] #update the best iteration
            past[-1] = 0 #reset the number of relaxed steps to 0 
        else: 
            past[-1] += 1 #otherwise we took a relaxed step; so update past to reflect that
        
        return pn, objn, gradn, [None], 1, 1 #return the new step
    else: #we have taken the maximum number of relaxed steps and now need to ensure sufficient decrease. 
        pn2, objn2, gradn2, hessn2, objeval, gradeval = watchdogls(p,d,obj,fnc,fnc_objder,grad,args,iters,bounds,  kwargs, c1 = c1) #need to do a linesearch on the current iterate
        
        dirder = np.matmul(past[0][2],past[0][3]) #recall past represents the last known point that was "good" i.e. it gave a sufficient decrease
        if obj <= past[0][1] or objn2 <=  past[0][1] + c1*c0*dirder: #if the new step gives a sufficient decrease with respect to the last known good step
#            print('sufficient decrease')
            past[0] = [pn2,objn2,gradn2] #update the best iteration
            past[-1] = 0 #reset the number of relaxed steps to 0 
            return pn2, objn2, gradn2, hessn2, objeval, gradeval #then we can return the new step we found
        
        elif objn2 > past[0][1]: #at this point, we have taken a number of relaxed steps, and then a sufficient step from the relaxed steps. We haven't yet managed to get sufficient decrease, 
            #with respect to the previous step we knew gave a sufficient decrease. Therefore we must either return to the original best known point, or take another sufficient step from the point 
            #we just found.
            #in this case, we will return to the original, last known step past[0][0] which gave us a sufficient decrease. 
#            print('return to best step')
            
            pn3, objn3, gradn3, hessn3, objeval3, gradeval3 = watchdogls(past[0][0],past[0][3], past[0][1], fnc, fnc_objder, past[0][2], args, iters, bounds,  kwargs, c1=c1)
            if objn3 == past[0][1]: #it's possible we can make no progress from the linesearch. If this happens then we will get stuck in a loop, so we will need to terminate
                #we will return the same point input into watchdog. this will cause the algorithm to terminate due to the objective not decreasing. 
                return p, obj, grad, [None], objeval+objeval3, gradeval + gradeval3 
            past[0] = [pn3, objn3, gradn3] #assuming the linesearch was successful, we have a new point with sufficient decrease and can update the best iteration
            past[-1] = 0 
            return pn3, objn3, gradn3, hessn3, objeval+objeval3, gradeval+gradeval3
            
        else: #the last possibiliity is that we will continue to search from the point corresponding to objn2. 
#            print('continue with search')
            past[-1] = t+1 #in this case we will give the past[-1] a special argument so we will perform a special action on the next iteration of the algorithm
            #the search direction is updated inside the algorithm. 
            return pn2, objn2, gradn2, hessn2, objeval, gradeval 
        
    
    return #this will never be reached. 

