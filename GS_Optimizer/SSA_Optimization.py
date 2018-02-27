# Copyright (c) 2018, The Fraunhofer Center for Sustainable Energy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# This material was prepared as an account of work sponsored by an agency
# of the United States Government.  Neither the United States Government
# nor any agency thereof, nor Fraunhofer, nor any of their employees,
# makes any warranty, express or implied, or assumes any legal liability
# or responsibility for the accuracy, completeness, or usefulness of any
# information, apparatus, product, or process disclosed, or represents
# that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or service
# by trade name, trademark, manufacturer, or otherwise does not necessarily
# constitute or imply its endorsement, recommendation, or favoring by the
# United States Government or any agency thereof, or Fraunhofer.  The
# views and opinions of authors expressed herein do not necessarily state
# or reflect those of the United States Government or any agency thereof.

from math import floor, exp
import copy
import json
import csv
import sys
import numpy
from random import *
from SunDialResource import SundialSystemResource, SundialResource, SundialResourceProfile, export_schedule
from datetime import datetime, timedelta
import logging
from gs_identities import (SSA_SCHEDULE_RESOLUTION, SSA_SCHEDULE_DURATION, SSA_PTS_PER_SCHEDULE)
from gs_utilities import get_schedule

_log = logging.getLogger("SSA")


############################
class SimulatedAnnealer():

    def __init__(self):
        # SSA configuration parameters:
        self.init_run    = 1            # number of runs to estimate initial temperature and weight
        self.nIterations = 50000           # Number of iterations
        self.temp_decrease_pd = 600 # Number of iterations betweeen temperature decrease
        self.jump_decrease_pd = 100 # Number of iterations betweeen jump size decrease
        self.jump             = 1.0 #0.5 # initial maximum jump
        self.fract_jump       = 0.95 # amount by which jump is decreased every jump_decrease_pd steps
        self.fract_T          = 0.85
        self.O2T              = 0.05  # Conversion of objective function into initial T


        self.display_pd = 5000; # update output for printing m and drawning

        self.tResolution_min          = SSA_SCHEDULE_RESOLUTION # time resolution of SSA optimizer control signals, in minutes
        self.optimizationPd_hr        = SSA_SCHEDULE_DURATION # period of the SSA time horizon, in hrs
        self.nOptimizationPtsPerPd    = SSA_PTS_PER_SCHEDULE

    ############################
    def scale_battery_weights(self, max_ess_energy, weight_disch, tResolution_hr):
        """
        NOT CURRENTLY USED
        Normalizes battery charge / discharge commands to the size of the energy
        storage system.

        As currently implemented, the function limit checks that ESS value at
        the end of the optimization period is less than capacity, and greater
        than zero.  This is a little bit of a shortcut - it does not check if
        battery exceeds limits DURING the optimization period (a separate
        limit check is performed when power commands are generated).  This may
        be (a) inefficient; and (b) introduce a bias in the weight maps that
        get generated.  Future mod should also parameterize upper and lower
        limits on ESS targets (i.e., rather than implicitly defining SOC range as 0-100%).

        :return:
        """

        discharge_weight_factor = min(1, max_ess_energy/abs(sum(weight_disch*tResolution_hr)))
        return weight_disch * discharge_weight_factor

    ############################
    def calc_jump(self, x, jump, lb, ub):
        """
        Returns a new value for an SSA weight by perturbing the current weight x by a random amount between +/- jump.
        The new weight is subject to upper and lower bounds set by ub and lb, respectively
        :return:
        """
        y2 = (random() - .5) * 2 * jump
        y3 = x + y2
        return max(min(y3,ub), lb)


    ############################
    def get_resource(self, sundial_profiles, resource_type):
        """
        searches a SundialProfile tree for instances whose resource_types that matches SundialProfile.resource_type
        :param sundial_profiles: an instance of SundialProfile class
        :param resource_type: resource type (e.g., ESSCtrlNode, PVCtrlNode, LoadShiftCtrlNode, Load, or System)
        :return: returns a list of SundialProfile class instances matching resource_type
        """
        resources = [] #None

        for virtual_plant in sundial_profiles.virtual_plants:
            resources.extend(self.get_resource(virtual_plant, resource_type))

        if resource_type == sundial_profiles.sundial_resources.resource_type:
            _log.info(sundial_profiles.sundial_resources.resource_id+" is a "+sundial_profiles.sundial_resources.resource_type)
            resources.append(sundial_profiles)

        return resources



    ############################
    def copy_profile(self, source, target):
        """
        does a deep copy of a SundialProfile instance from source to target by recursively traversing
        nodes.  Source and target must have the same tree topology
        :param source: SunDialProfile instance
        :param target: SunDialProfile instance
        :return: target - SundialProfile instance
        """
        for (source_child, target_child) in zip(source.virtual_plants, target.virtual_plants):
            target_child = self.copy_profile(source_child, target_child)

        if target.sundial_resources.update_required == 1:
            target.state_vars = copy.deepcopy(source.state_vars)
            target.cost       = source.cost #copy.deepcopy(source.cost)
            target.total_cost = source.total_cost #copy.deepcopy(source.total_cost)

        return target



    ############################
    def run_ssa_optimization(self, sundial_resources, timestamps):

        """
        Executes simulated Annealing optimization algorithm.

        Inputs:
        - sundial_resources is a SundialResource data object that acts as a container for information about the system
          we are trying to optimize.  Each node in the sundial_resources tree represents an aggregation of DERs whose behavior is driven by a
          common set of objective functions.  A sundial_resource node needs to be populated with:
           - in state_vars - a baseline forecast for the resource's net demand over the optimization period defined by
             SSA_SCHEDULE_DURATION, at time resolution of SSA_SCHEDULE_RESOLUTION
           - in state_vars - information about the resource's current state (E.g., battery SOE) and resource information
           - a list of one or more objective functions and/or constraints that equate the resource's behavior to cost,
             and associated cost parameters
        - timestamps - used to provide a time reference for schedules that get generated.

        Outputs:
        The primary output of run_ssa_optimization is schedule information for each resource in the Sundial system that
        reflects a global least-cost solution for the given combination of forecasts, objective functions, and starting
        conditions.  On completion, run_ssa_optimization
        (1) dumps the orgiinal adn new schedule profiles to a csv file - each row is a different profile,
            columns represent time
        (2) copies least_cost_soln to the schedule_vars data structure to each resource in the sundial_resources tree.
            schedule_vars is used to determine set points in the Global Scheduler

        Overview of run_ssa_optimization:

        For each resource in the sundial_resources tree, run_ssa_optimization instantiates three different
        SundialResourceProfile instances - "init_soln", "least_cost_soln", and "current_soln"
        A SundialResourceProfile is a class that holds information about a proposed load shape.
        - init_soln - corresponds to the initial values for the optimization pass
        - current_soln - corresponds to proposed load profile for the current test case
        - least_cost_soln - corresponds to the least cost load profile that has been found during this optimization pass

        The simulated annealing algorithm references the following parameters:
        - self.nIterations - Number of iterations to
        - self.temp_decrease_pd - Number of iterations betweeen temperature decrease
        - self.jump_decrease_pd - Number of iterations betweeen jump size decrease
        - self.jump - initial maximum jump
        - self.fract_jump - amount by which jump is decreased every jump_decrease_pd iterations
        - self.fract_T - amount by which temperature is decreased every temp_decrease_pd iterations
        - self.O2T  - Conversion of objective function cost into initial T

        Execution of the Simulated Annealing algorithm is as follows:
        1. Initialize init_soln, current_soln, and least_cost_soln to a set of common baseline profiles
        2. calculate cost of the initial solution.  This is used to establish T0 - the initial temperature of the system
        3. Iteratively seek a least-cost solution (based on self.nIterations)
           - periodically decrease temperature and jump size, based on configured parameters to "cool" the system
           - select a controllable resource. NOTE - current implementation assumes a single ESS
           - perturb a single point in the resource's current_soln profile by a random amount, constrained by jump
           - check to make sure that this change has not violated a constraint (e.g., exceed upper or lower bound on
             SOE).  modify profile if necessary
           - update other resource profiles, as necessary
           - calculate cost of the current_soln.
           - compare to cost of the least_cost_soln: if the proposed solution (current_soln) is least_cost, adopt this
             as the new least cost solution.  If cost is higher, adopt as the new least_cost_soln with a probability
             dictated by the system's temperature

        The current implementation implicitly assumes that the only controllable resource is a single ESS.  This is a
        a shortcut towards getting a minimum version running.  Modest changes would support multiple controllable
        resources.


        TODO - check relationship between delta and self.O2T - does delta need to be convereted to T??

        :param sundial_resources: A SundialResource instance - referencing to the top of the SundialResource tree for
        the system in question.
        :param timestamps: list of timestamps, length of SSA_PTS_PER_SCHEDULE, that correpond to the time at which
        schedule_var data points are valid
        :return: None
        """

        # get an initial set of commands to seed the ssa process
        # then, set least_cost_soln AND current_soln to initiate the SSA
        init_soln       = SundialResourceProfile(sundial_resources, timestamps)
        current_soln    = SundialResourceProfile(sundial_resources, timestamps)
        least_cost_soln = SundialResourceProfile(sundial_resources, timestamps)


        # For convenience - this extracts specific resource types from the Sundial tree structure and puts them
        # in a flat list, grouped by resource type.  Just simplifies data handling, speeds execution, particularly
        # for simple system topology
        # Currently, we are only handling a single SundialResource per resource_type.
        self.load       = self.get_resource(current_soln, "Load")[0]
        self.load_shift = self.get_resource(current_soln, "LoadShiftCtrlNode")[0]
        self.pv         = self.get_resource(current_soln, "PVCtrlNode")[0]
        self.ess        = self.get_resource(current_soln, "ESSCtrlNode")[0]
        self.system     = self.get_resource(current_soln, "System")[0]

        self.ess_least_cost = self.get_resource(least_cost_soln, "ESSCtrlNode")[0]


        # set initial tempearture
        T0   = abs(self.O2T*init_soln.cost)
        T    = T0;

        _log.info("Jump is: "+str(self.jump))
        _log.info("T is: "+str(T))
        _log.info("Init Least Cost Solution is: "+str(least_cost_soln.total_cost))

        copy_time   = 0
        constraint_time = 0
        cost_time = 0
        loop_time = 0

        t0 = datetime.now()

        # From the initial solution, follow the simulated annealing logic: disturb
        # 1 point and check if there is improvement.
        for ii in range(self.nIterations):

            if (ii % self.display_pd == 0): # for debug - periodically publish results
                _log.info("Iteration "+str(ii)+": T="+str(T)+"; Least Cost Soln = "+str(least_cost_soln.total_cost))

            if ((ii+1) % self.jump_decrease_pd) == 0: # check if it's time to decrease jump size.
                # decrease jump size
                self.jump = self.jump*self.fract_jump
                #print("ii = "+str(ii)+"; Jump decrease - jump = " + str(self.jump))

            if ((ii+1) % self.temp_decrease_pd) == 0: # check if it's time to decrease temperature
                # decrease temperature, reset jump to the starting value from the last jump decrease
                T         = self.fract_T*T
                n         = floor(self.temp_decrease_pd/self.jump_decrease_pd)
                self.jump = self.jump/(self.fract_jump**n)
                #print("ii = "+str(ii)+"; Temp decrease - "+str(T)+"; jump = "+str(self.jump))
                #print("ESS Weight is: " + str(self.ess.current_soln.weight))

            # FIXME - Much of the following is taking advantage of a simple system topology by directly referencing
            # FIXME - into system nodes.  The universal version should do much of the following by recursively
            # FIXME - traversing the SundialResource tree.

            t2     = datetime.now()  # time stamp at start of copy
            # set the current test profile to the current least-cost solution
            current_soln = self.copy_profile(least_cost_soln, current_soln) # set current soln to least cost soln
            t3         = datetime.now() # time stamp at end of copy
            deltaT     = t3-t2
            copy_time += deltaT.total_seconds()  # running tally of how long we spend on copy operations

            # Randomly perturb a single point by a random value dictated by the size of the jump parameter
            # FIXME: currently this just deals with battery charge / discharge instructions - not other resources
            # FIXME: e.g., PV curtailment
            ind = int(floor(random()*self.nOptimizationPtsPerPd))
            self.ess.state_vars["Weight"][ind]   = self.calc_jump(self.ess.state_vars["Weight"][ind], self.jump, -1, 1)  # FIXME: -1 to 1 should not be fixed.

            # Then: check for constraints.
            # TODO - right now, just checking for battery limit violations.  Eventually put in ability to include
            # TODO - additional constraints
            self.system.state_vars["DemandForecast_kW"] = self.system.state_vars["DemandForecast_kW"] - \
                                                          self.ess.state_vars["DemandForecast_kW"]
            self.ess.state_vars["DemandForecast_kW"] = self.ess.state_vars["Weight"] * self.ess.sundial_resources.state_vars["Nameplate"]
            self.ess.state_vars    = self.ess.sundial_resources.check_constraints(self.ess.state_vars, ind)


            # then: update resources.  This is a shortcut
            # update overall "system" with new ESS profile - above, subtracted old ESS profile.  next line adds new profile
            self.system.state_vars["DemandForecast_kW"] = self.system.state_vars["DemandForecast_kW"] + \
                                                          self.ess.state_vars["DemandForecast_kW"]
            #current_soln.update_state() # not implemented


            # Sanity check to make sure that constraint check is working.  probably unnecessary at this pont.
            if max(self.ess.state_vars["EnergyAvailableForecast_kWh"])>float(self.ess.sundial_resources.state_vars["MaxSOE_kWh"])+0.001:
                _log.info("ii= "+str(ii)+": Max Constraint Error!!  "+str(max(self.ess.state_vars["EnergyAvailableForecast_kWh"])))

            if min(self.ess.state_vars["EnergyAvailableForecast_kWh"])<float(self.ess.sundial_resources.state_vars["MinSOE_kWh"])-0.001:
                _log.info("ii= "+str(ii)+": Min Constraint Error!! - "+str(min(self.ess.state_vars["EnergyAvailableForecast_kWh"])))

            # timestamps for how cumulative time it takes to check constraints / update resources.
            t5         = datetime.now()
            deltaT     = t5-t3
            constraint_time += deltaT.total_seconds()


            # Now calculate cost of the current solution and get timing for cumulative time on doing cost calcs.
            total_cost = current_soln.calc_cost()
            #print ("total cost = "+str(total_cost))
            t6         = datetime.now()
            deltaT     = t6-t5
            cost_time += deltaT.total_seconds()

            # Calculate delta cost between this test value and the current least cost solution
            delta = total_cost - least_cost_soln.total_cost

            if delta < 0:
                # Current test value is a new least-cost solution.  Use this!
                least_cost_soln = self.copy_profile(current_soln, least_cost_soln)  # set least cost soln to current soln

            elif delta > 0:
                # Current test value is worse than current least-cost solution
                # Adopt the current test value along a probabilistic
                # distribution according to SSA parameters
                # NOTE -- T must be greater than zero!!!  Need to watch out for this depending on obj fcn calcs.
                th = exp(-delta / T)
                r  = random()
                if r < th:
                    #print("non best solution adopted.  r="+str(r)+"; Th = "+str(th)+"; T="+str(T)+"; delta = "+str(delta))
                    least_cost_soln = self.copy_profile(current_soln, least_cost_soln)  # set least cost soln to current soln

            # end of main loop (nIterations)

        t8 = datetime.now()
        deltaT = t8 - t0
        total_time = deltaT.total_seconds()

        _log.info("least cost soln is "+str(least_cost_soln.total_cost))
        _log.info("time results: copy: "+str(copy_time)+"; Constraint: "+
              str(constraint_time)+"Cost: "+str(cost_time))

        _log.info("loop time: "+str(loop_time)+"; total time: "+str(total_time))

        # exports least_cost_soln to sundial_resources.schedule_vars
        export_schedule(least_cost_soln, timestamps)
        _log.info("Time Stamps are:"+str(least_cost_soln.sundial_resources.schedule_vars["timestamp"]))
        _log.info("ESS profile: "+str(self.ess_least_cost.state_vars["DemandForecast_kW"]))
        _log.info("System profile: " + str(least_cost_soln.state_vars["DemandForecast_kW"]))
        _log.info("System profile: " + str(least_cost_soln.sundial_resources.schedule_vars["DemandForecast_kW"]))
        for virtual_plant in least_cost_soln.virtual_plants:
            _log.info(virtual_plant.sundial_resources.resource_id+": "+str(virtual_plant.state_vars["DemandForecast_kW"]))
            _log.info(virtual_plant.sundial_resources.resource_id + ": " +
                      str(virtual_plant.sundial_resources.schedule_vars["DemandForecast_kW"]))


        # dump some data to a csv file
        csv_name = ("/home/parallels/sundial/ssa_results.csv")
        with open(csv_name, 'wb') as csvfile:
            results_writer = csv.writer(csvfile)
            results_writer.writerow(least_cost_soln.state_vars["DemandForecast_kW"])
            results_writer.writerow(init_soln.state_vars["DemandForecast_kW"])
            results_writer.writerow(self.ess_least_cost.state_vars["DemandForecast_kW"])
            results_writer.writerow(self.ess_least_cost.state_vars["EnergyAvailableForecast_kWh"])
            results_writer.writerow(self.pv.state_vars["DemandForecast_kW"])
            results_writer.writerow(self.load.state_vars["DemandForecast_kW"])
            #results_writer.writerow(self.pv.init_solution.schedule)
            #results_writer.writerow(self.demand.least_cost_soln.schedule)




if __name__ == '__main__':
    # Entry point for script

    ##### This section replicates the initialization of the system (done one time, when system starts up) ######

    # the following is a rough demo of how a system gets constructed.
    # this is a hard-coded version of what might happen in the executive
    # would eventually do all this via external configuration files, etc.

    _log.setLevel(logging.INFO)
    msgs = logging.StreamHandler(stream=sys.stdout)
    msgs.setLevel(logging.INFO)
    _log.addHandler(msgs)

    SundialCfgFile = "../cfg/SystemCfg/SundialSystemConfiguration.json"#"SundialSystemConfiguration2.json"
    sundial_resource_cfg_list = json.load(open(SundialCfgFile, 'r'))

    gs_start_time = datetime.datetime.strptime(get_schedule(),
                                               "%Y-%m-%dT%H:%M:%S.%f")
    sundial_resources = SundialSystemResource(sundial_resource_cfg_list, gs_start_time)

    #for resource in sundial_resources:
    #    print("Device ID: "+resource.resource_id, "; Device Type = "+resource.resource_type)

    optimizer = SimulatedAnnealer()

    #sundial_resources.init_test_values(24)  # initializes with some hard-coded known values

    ess_resources = sundial_resources.find_resource_type("ESSCtrlNode")[0]
    pv_resources = sundial_resources.find_resource_type("PVCtrlNode")[0]
    system_resources = sundial_resources.find_resource_type("System")[0]
    loadshift_resources = sundial_resources.find_resource_type("LoadShiftCtrlNode")[0]
    load_resources = sundial_resources.find_resource_type("Load")[0]


    #### Just load with example values - ######
    ess_forecast = [0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0]

    #ess_forecast = [-51.35175009, -51.37987963, -52.40495415, -55.7941499,
    #                -70.15320262, -193.91606361,   15.24561777, -13.75917004,
    #                63.47416001,  247.63232283, 350.72528327,  426.73011525,
    #                417.92689915,  357.44332889, 224.46714951, 16.86389897,
    #                0.0, 0.0, -136.28581942, -96.68917457,
    #                49.07769182, 97.72753814, 111.3388077, 0.0]

    ess_resources.load_scenario(init_SOE=500,
                                max_soe=2000,
                                min_soe=0,
                                max_chg=500,
                                max_discharge=500,
                                chg_eff=0.95,
                                dischg_eff=0.95,
                                demand_forecast=ess_forecast)

    pv_forecast = [0, 0, 0, 0,
                   0, -5.769, -93.4666, -316.934,
                   -544.388, -716.663, -822.318, -888.916,
                   -898.478, -839.905, -706.972, -512.013,
                   -265.994, -74.6933, -2.0346, 0,
                   0, 0, 0, 0]

    demand_forecast = [142.4973, 142.4973, 142.4973, 145.9894,
                       160.094, 289.5996, 339.7752, 572.17,
                       658.6025, 647.2883, 650.1958, 639.7053,
                       658.044, 661.158, 660.3772, 673.1098,
                       640.9227, 523.3306, 542.7008, 499.3727,
                       357.9398, 160.0936, 145.9894, 142.4973]

    pv_resources.load_scenario(demand_forecast = pv_forecast,
                               pk_capacity = 1000)

    load_resources.load_scenario(demand_forecast = demand_forecast,
                                 pk_capacity = 1000)

    loadshift_resources.load_scenario()
    system_resources.load_scenario()



    #########


    ##### This section replicates the periodic call of the optimizer ######
    # calls the actual optimizer.
    optimizer.run_ssa_optimization(sundial_resources,[])
