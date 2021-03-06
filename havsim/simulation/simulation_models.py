"""
For subclassed Vehicles to be used in Simulation.
"""
from havsim.simulation import vehicles
from havsim.simulation import models
import math

class OVMVehicle(vehicles.Vehicle):
    """Optimal Velocity Model Implementation."""
    def cf_model(self, p, state):
        return models.OVM(p, state)
    
    def eqlfun(self, p, s):
        return models.OVM_eql(p, s)
    
    def free_cf(self, p, v):
        return models.OVM_free(p, v)
    
    
class SKARelaxIDM(vehicles.Vehicle):
    def initialize(self, pos, spd, hd, starttime):
        super().initialize(pos, spd, hd, starttime)
        self.max_relax = self.cf_parameters[1]
        self.relax_end = math.inf
    
    def set_relax(self, timeind, dt):
        self.relax_start = 'r'  # give special value 'r' if we need to adjust the time headway
        temp = dt/self.relax_parameters[1]
        self.cf_parameters[1] = (self.relax_parameters[0] - self.max_relax*temp)/(1-temp)  # handle first
        # relaxation value correctly (because it will be updated once before being used)
        
    def update(self, timeind, dt):
        super().update(timeind, dt)
        
        if self.relax_start == 'r':
            temp = dt/self.relax_parameters[1]
            self.cf_parameters[1] += (self.max_relax-self.cf_parameters[1])*temp