import numpy
import pandas
import os
import pytz
from datetime import datetime, timedelta
import isodate
import copy
import csv
from gs_identities import *

STANDALONE = False

##############################################################################
class ObjectiveFunction():

    ##############################################################################
    def __init__(self, desc="", init_params=None, **kwargs): #fname, schedule_timestamps, sim_offset=timedelta(0), desc=""):
        """
        loads a file of dates / values.  retrieves a pandas data frame of for the specified time window.
        1. load data file
        2. retrieve data corresponding to time window
        3. resample if necessary
        :param self:
        :return:
        """
        print(desc)
        self.desc   = desc
        self.init_params = {}
        self.cfg_params  = ""

        for k, v in init_params.iteritems():
            try:
                self.init_params.update({k: kwargs[k]})
            except:
                print("Warning in ObjectiveFunction.py " + self.desc + "  __init__: '" + k + "' undefined - using default value")
                self.init_params.update({k: init_params[k]})


    ##############################################################################
    def obj_fcn_cfg(self, **kwargs):
        pass

    ##############################################################################
    def load_data_file(self, fname):
        """
        Loads time-series cost data from an excel file
        column 1 = datetime
        column 2-n = cost information
        row 1 = column headers
        :param fname: filename
        :return: self.obj_fcn_data --> dataframe of time series cost data
        """
        if STANDALONE == False:
            volttron_root = os.getcwd()
            volttron_root = volttron_root + "/../../../../gs_cfg/"
        else:
            volttron_root = ""
        fname_fullpath = volttron_root+fname

        df = pandas.read_excel(fname_fullpath, header=0, index_col=0)
        #tst = numpy.array([pandas.Timestamp(t).replace(tzinfo=pytz.UTC).to_pydatetime() for t in df.index])
        new_df = df.resample(str(SSA_SCHEDULE_RESOLUTION) + 'T').bfill()
        new_df.index = [pandas.Timestamp(t).replace(tzinfo=pytz.UTC).to_pydatetime() for t in new_df.index]
        return new_df

    ##############################################################################
    def lookup_data(self, schedule_timestamps, sim_offset=timedelta(0)):
        """
        looks up cost data from a time-series dataframe for a time window defined by schedule_timestamps
        :param schedule_timestamps:
        :param sim_offset:
        :return:
        """
        print("sim_offset = "+str(sim_offset))

        #### Find the time window corresponding to the current set of timestamps:
        # slow!~ could be optimized.

        # FOR each element of the database
        # for each timestamp value
        # find the difference between all db elements and the timestamp
        # assign the closest one to that timestamp
        # this is very inefficient
        # instead...
        # 1. I get a timestamp
        # 2. I round down to the nearest time step


        ### what am I having problems with?
        # options -

        start_ind = numpy.argmin(numpy.abs(self.obj_fcn_data.index - (schedule_timestamps[0] + sim_offset)))

        if self.obj_fcn_data.index[start_ind] > schedule_timestamps[0]:
            start_ind -= 1


        cur_data = self.obj_fcn_data.iloc[start_ind:start_ind + SSA_PTS_PER_SCHEDULE]
        cur_data.index = schedule_timestamps

        #indices = [numpy.argmin(
        #    numpy.abs(
        #        numpy.array([pandas.Timestamp(t).replace(tzinfo=pytz.UTC).to_pydatetime() for t in self.obj_fcn_data.index]) -
        #        (ts.replace(minute=0, second=0, microsecond=0) + sim_offset))) for ts in schedule_timestamps]
        print(cur_data)
        return numpy.array(cur_data.transpose())
        #numpy.array(self.obj_fcn_data.iloc[indices].transpose())  #obj_fcn_data.loc[offset_ts].interpolate(method='linear')



    ##############################################################################
    def get_obj_fcn_data(self):
        return self.init_params["cur_cost"]


##############################################################################
class EnergyCostObjectiveFunction(ObjectiveFunction):

    ##############################################################################
    def __init__(self, desc="", init_params=None, **kwargs):
        init_params = {'fname': None}

        # duration --> 'time_step': isodate.parse_duration('PT60M')


        #cfg_params  = {'schedule_timestamps': [0],
        #               'sim_offset': timedelta(0)}

        ObjectiveFunction.__init__(self, desc=desc, init_params=init_params, **kwargs)
        #fname = kwargs["fname"]
        #schedule_timestamps = kwargs["schedule_timestamps"]
        self.obj_fcn_data = self.load_data_file(self.init_params["fname"]) #, self.init_params["schedule_timestamps"])
        self.cfg_params = ["schedule_timestamps", "self.sim_offset"]
        #"schedule_timestamps=schedule_timestamps, sim_offset=self.sim_offset"

    ##############################################################################
    def obj_fcn_cfg(self, **kwargs):
        self.init_params["cur_cost"] = self.lookup_data(kwargs["schedule_timestamps"],
                                                        kwargs["sim_offset"])

    ##############################################################################
    def obj_fcn_cost(self, profile):
        cost = sum(self.init_params["cur_cost"][0] * profile)
        return cost

    ##############################################################################
    def get_obj_fcn_data(self):
        return self.init_params["cur_cost"][0].tolist()

##############################################################################
class dkWObjectiveFunction(ObjectiveFunction):
    """
    assigns a cost to change in power (dPwr/dt)
    """
    def __init__(self, desc="", init_params=None, **kwargs):
        ObjectiveFunction.__init__(self, desc=desc, init_params={}, **kwargs)
        self.init_params["cost_per_dkW"] = 0.005

    def obj_fcn_cost(self, profile):
        return sum(abs(numpy.ediff1d(profile)))*self.init_params["cost_per_dkW"]

    def get_obj_fcn_data(self):
        return self.init_params["cost_per_dkW"]

##############################################################################
class DemandChargeObjectiveFunction(ObjectiveFunction):

    ##############################################################################
    def __init__(self, desc="", init_params=None, **kwargs):
        init_params = {'threshold': 250,
                       'cost_per_kW': 10}

        ObjectiveFunction.__init__(self, desc=desc, init_params=init_params, **kwargs)

        self.cfg_params = "cost_per_kW=10.0, threshold=tariffs['demand_charge_threshold']"

        #try:
        #    self.params.update({'threshold': kwargs["threshold"]})
        #except:
        #    print("ERROR in DemandChargeObjectiveFunction __init__ - invalid threshold undefined - using default value")
        #    self.params.update({'threshold': 250})

        #try:
        #    self.params.update({'cost_per_kW': kwargs["cost_per_kW"]})
        #except:
        #    print("ERROR in DemandChargeObjectiveFunction __init__ - invalid threshold undefined - using default value")
        #    self.params.update({'cost_per_kW': 10})


    ##############################################################################
    def obj_fcn_cfg(self, **kwargs):
        for k, v in self.init_params.iteritems():
            print("k="+str(k)+"; v="+str(v))
            try:
                self.init_params.update({k: kwargs["tariffs"][k]})
            except:
                pass

        print(self.init_params)
        #self.init_params["threshold"] = kwargs["threshold"]
        #self.init_params["cost_per_kW"] = kwargs["cost_per_kW"]

    ##############################################################################
    def obj_fcn_cost(self, profile):
        """
        placeholder for a function that calculates a demand charge for a given net demand profile
        :return: cost of executing the profile, in $
        """
        #demand = numpy.array(profile)

        max_demand = max(profile)
        if max_demand > self.init_params["threshold"]: #self.threshold:
            cost = self.init_params["cost_per_kW"] * (max_demand - self.init_params["threshold"])
        else:
            cost = 0.0
        return cost

    ##############################################################################
    def get_obj_fcn_data(self):
        return self.init_params["threshold"]


##############################################################################
class TieredEnergyObjectiveFunction():
    """
    placeholder for a function that calculates a demand charge for a given net demand profile
    :return: cost of executing the profile, in $
    """
    ##############################################################################
    def __init__(self, desc):
        # fname, schedule_timestamps, sim_offset=timedelta(0)
        pass


    ##############################################################################
    def obj_fcn_cost(self, profile):

        max_bf = max(profile)

        # tier at 200, 100, 10
        cost = 0.0
        for p in profile:
            cost += max(p - 400.0, 0) * 100.0
            cost += max(p - 250.0, 0) * 50.0
            cost += max(p - 200.0, 0) * 25.0
            cost += max(p - 150.0, 0) * 10.0
            cost += max(p - 100.0, 0) * 5.0
            cost += max(p - 50.0, 0) * 3.0
            cost += max(p, 0.0) * 1.0

            #if p > 0:
            #    cost += p*p


        # if max_bf < 0: #self.demand_threshold:
        #    cost = self.demand_cost_per_kW*(-1*max_bf)
        # else:
        #    cost = 0
        return cost


##############################################################################
class LoadShapeObjectiveFunction(ObjectiveFunction):

    ##############################################################################
    def __init__(self, desc="", **kwargs): #fname, schedule_timestamps, sim_offset=timedelta(0), desc=""):
        init_params = {'fname': None,
                       'schedule_timestamps':[0]}
        ObjectiveFunction.__init__(self, desc=desc, init_params=init_params, **kwargs)

        self.obj_fcn_data = self.load_data_file(self.init_params["fname"])
        self.cfg_params   = "schedule_timestamps=schedule_timestamps, sim_offset=self.sim_offset"

        self.cost = 0.0
        self.err  = 0.0

    ##############################################################################
    def obj_fcn_cfg(self, **kwargs):
        self.init_params["cur_cost"] = self.lookup_data(kwargs["schedule_timestamps"],
                                                        kwargs["sim_offset"])

    ##############################################################################
    def obj_fcn_cost(self, profile):
        """
        imposes a cost for deviations from a target load shape.
        cost is calculated as square of the error relative to the target load shape.
        :return: cost of executing proposed profile, in $
        """
        price = 10.0  # sort of arbitrary, just needs to be a number big enough to drive behavior in the desired direction.
        #demand = numpy.array(profile)

        self.err = (profile - self.init_params["cur_cost"][0]) ** 2
        self.cost = sum(self.err) * price
        return self.cost

    ##############################################################################
    def get_obj_fcn_data(self):
        return self.init_params["cur_cost"][0].tolist()
