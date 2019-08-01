# Copyright (c) 2017, The Fraunhofer Center for Sustainable Energy
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

from datetime import datetime, timedelta
import os

###################################
# execution flags, change these to modify modes of operation
USE_SIM      = 0      # Change for running in non-real time
DEPLOYED     = True  # Change for deployed / not deployed
USE_VOLTTRON = 1

USE_SOLAR_SIM  = 1   # use simulated solar vs real solar data. only valid when USE_SIM==1
USE_DEMAND_SIM = 1   # use simulated load vs real loads.  only valid when USE_SIM==1
USE_SCALED_LOAD = True #False
SIM_SCENARIO   = 5
USE_CONFIGURABLE_OBJ_FCNS = True
USE_STRATEGIC_SCHEDULE = False   # toggle to True/False depending on if strategic objectives are used

ALIGN_SCHEDULES = True
REGULATE_ESS_OUTPUT = True # True = Match system's output in real time to scheduled output using ESS; False = use scheduled ESS value regardless of divergence from forecast
USE_FORECAST_VALUE = True
SMOOTH_RAMP = False
IMPORT_CONSTRAINT = False    # fail safe to ensure that storage does not charge from the grid
SEARCH_LOADSHIFT_OPTIONS = False # If True, the optimizer will search through all load shift options available (as opposed to searching a single option)
ENABLE_LOAD_SELECT = False # If True, GS will propagate load shift commands to the FLAME.  If False, Load shift selection will be logged, but not transmitted.


###################################
### Internal operating clocks.
EXECUTIVE_CLKTIME = 1 # period, in seconds, at which the executive polls system state
DATA_LOG_SCHEDULE = 1  # period at which state vars are logged, in executive clock cycles
ENDPT_UPDATE_SCHEDULE  = DATA_LOG_SCHEDULE # period at which sundial system resource objects are updated
GS_SCHEDULE       = 4*60 #2880/6  # GS optimizer period, in executive clock cycles
ESS_SCHEDULE      = 2 # ess regulation period, in executive clock cycles
UI_CMD_POLLING_FREQUENCY = 5 # period, in seconds, at which the UI agent polls UI_cmd.json for a new msg
STRATEGIC_SCHEDULE = 24*60*60/2 #240

ESS_CMD_PUBLICATION_INTERVAL       = 10
SUNDIAL_STATE_PUBLICATION_INTERVAL = 10
EXECUTIVE_STATUS_PUBLICATION_INTERVAL = 10

####################################
### Some basic device and objective fcn configuration options:
DEMAND_CHARGE_THRESHOLD = 300 #250
UPDATE_THRESHOLD = True

# FIXME - ESS_RESERVE_xx should be set in absoluate terms, not relative terms - won't work if ESS_MIN is 0
ESS_MAX = 0.98
ESS_MIN = 0.05
ESS_RESERVE_HIGH = 0.95  # relative to ESS_MAX
ESS_RESERVE_LOW  = 1.5   # relative to ESS_MIN

USE_PV_ADJUST = 1 # 0 = no adjust; 1 = Use hour lookup adjust
PV_ADJUST = 1.0 #0.65
DEMAND_ADJUST = 1.0
#ERROR_MARGIN  = 1.1



#######################################################
## Constants, do not edit

# Site Operating Modes
SITE_IDLE    = 0
SITE_RUNNING = 1

# Plant vs Device Level Ctrl
PLANT_LEVEL  = 0
DEVICE_LEVEL = 1

# Site System Control Modes
AUTO        = 0
INTERACTIVE = 1
STARTING    = 2
READY       = 3

DISABLED = 0
ENABLED  = 1

SEC_PER_MIN = 60.0
MINUTES_PER_HR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HR
START_OF_YR = datetime(year=2018, month=1, day=1, hour=0, minute=0, second=0) # anchor point for simulations
EPSILON = 0.001
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


# Directories
GS_ROOT_DIR     = os.environ['GS_ROOT_DIR']     # need to set GS_ROOT_DIR environment variable to location of GS code tree
CFG_PATH        = "cfg/"

# Site Timeout
PMC_HEARTBEAT_TIMEOUT = 100 # timeout, in seconds
PMC_HEARTBEAT_PD      = 10 # expected period, in seconds
PMC_HEARTBEAT_RESET   = 24 * 60 * 60 # heartbeat reset frequency, in seconds
PMC_WATCHDOG_PD       = 10 # expected heartbeat, in seconds
PMC_WATCHDOG_RESET    = 24 * 60 * 60 # watchdog reset frequency, in seconds
IGNORE_HEARTBEAT_ERRORS = 1

# GS Internal Operating Modes
IDLE = 0
USER_CONTROL = 1
APPLICATION_CONTROL = 2
EXEC_STARTING = 3


###############################
## Set configuration files here
if DEPLOYED == True:
    #SITE_CFG_FILE   = "SiteConfiguration-PlantLevel-original.json"
    #SITE_CFG_FILE   = "SiteConfiguration-DeviceLevel.json"
    SYSTEM_CFG_FILE = "SundialSystemConfiguration.json"
    SITE_CFG_FILE   = "SiteConfiguration-PlantLevel.json"
    DAY_AHEAD_SYSTEM_CFG_FILE = "DayAheadSundialSystemConfiguration.json"
else:
    SITE_CFG_FILE   = "SiteConfiguration-Emulator.json"
    #SITE_CFG_FILE   = "SiteConfiguration-Emulator-2Sites.json"
    SYSTEM_CFG_FILE = "EmulatedSundialSystemConfiguration.json"
    DAY_AHEAD_SYSTEM_CFG_FILE = "DayAheadSundialSystemConfiguration.json"


if USE_SIM == 0:
    SIM_HRS_PER_HR = 1 # used to set time acceleration.  1 = normal time.  60 = 60x acceleration

    # Configuration File Locations
    #SYSTEM_CFG_FILE = "SundialSystemConfiguration.json"
    #DAY_AHEAD_SYSTEM_CFG_FILE = "DayAheadSundialSystemConfiguration.json"

    pass

else:
    SIM_HRS_PER_HR = 1 # used to set time acceleration.  1 = normal time.  60 = 60x acceleration
    # Configuration File Locations
    #SYSTEM_CFG_FILE = "EmulatedSundialSystemConfiguration.json"
    #DAY_AHEAD_SYSTEM_CFG_FILE = "DayAheadSundialSystemConfiguration.json"


###################################
### Sets some internal schedules
MODBUS_SCRAPE_INTERVAL  = 1 # period in seconds for modbus device to post on the IEB bus
NORTH_MODBUS_SCRAPE_INTERVAL  = 10 # period in seconds for modbus device to post on the IEB bus

AVERAGING_WINDOW = int(15*60 / SIM_HRS_PER_HR) # period in seconds over which to average readings
AVG_UPDATE_PD    = 30 # period, in seconds, over which to update average calculation
#MODBUS_PTS_PER_WINDOW = int(MODBUS_AVERAGING_WINDOW/MODBUS_SCRAPE_INTERVAL)
MODBUS_WRITE_ATTEMPTS  = 5  # number of modbus reads before a write error is thrown

SSA_SCHEDULE_DURATION = 24 # Duration, in hours, over which SSA generates schedules
SSA_SCHEDULE_RESOLUTION   = 60 # Time resolution, in minutes, of SSA schedule
SSA_PTS_PER_SCHEDULE = SSA_SCHEDULE_DURATION * 60/SSA_SCHEDULE_RESOLUTION
DURATION_1MIN_FORECAST = 5 # hrs

# For configuring forecast agent
CPR_TIMEOUT = 600            #sets the timeout for hourly forecast data requests - DEPRECATED???
CPR_1M_TIMEOUT = 600         #sets the timeout for minute forecast data requests - DEPRECATED???

##############################################
#### Configuration for simulation scenarios:
# For configuring w/ simulated data
if SIM_SCENARIO == 1:
    PV_FORECAST_FILE = "SAM_PVPwr_nyc.csv"  # "irr_1min.csv"
    PV_TS_FILE       = None
    PV_FORECAST_FILE_TIME_RESOLUTION_MIN = 60  # 1
    SIM_START_DAY = 202  # day 106 #2  # day 202, Hr = 5 # 200, Hr = 7
    SIM_START_HR  = 5
    USE_MATRIX = False
elif SIM_SCENARIO == 2:
    USE_MATRIX = True
    PV_FORECAST_FILE = 'solar_forecast_matrix.csv'
    PV_TS_FILE       = 'solar_forecast_ts_matrix.csv'
    GHI_FORECAST_FILE = 'ghi_forecast_matrix.csv'
    GHI_TS_FILE       = 'ghi_forecast_ts_matrix_v2.csv'
    PV_FORECAST_FILE_TIME_RESOLUTION_MIN = 60  # 1
    #SIM_START_TIME = datetime(year=2018, month=10, day=5, hour=11, minute=0, second=0)
    SIM_START_TIME = datetime(year=2018, month=10, day=11, hour=0, minute=0, second=0)
    SIM_START_DAY = (SIM_START_TIME - START_OF_YR).days+1
    SIM_START_HR  = SIM_START_TIME.hour
elif SIM_SCENARIO == 3:
    USE_MATRIX = True
    PV_FORECAST_FILE = 'solar_forecast_matrix.csv'
    PV_TS_FILE       = 'solar_forecast_ts_matrix.csv'
    GHI_FORECAST_FILE = 'ghi_forecast_matrix.csv'
    GHI_TS_FILE       = 'ghi_forecast_ts_matrix_v2.csv'
    PV_FORECAST_FILE_TIME_RESOLUTION_MIN = 60  # 1
    #SIM_START_TIME = datetime(year=2018, month=10, day=5, hour=11, minute=0, second=0)
    SIM_START_TIME = datetime(year=2018, month=8, day=16, hour=0, minute=0, second=0)
    SIM_START_DAY = (SIM_START_TIME - START_OF_YR).days+1
    SIM_START_HR  = SIM_START_TIME.hour
elif SIM_SCENARIO == 4:
    USE_MATRIX = True
    PV_FORECAST_FILE = 'solar_forecast_matrix.csv'
    PV_TS_FILE       = 'solar_forecast_ts_matrix.csv'
    GHI_FORECAST_FILE = 'ghi_forecast_matrix.csv'
    GHI_TS_FILE       = 'ghi_forecast_ts_matrix_v2.csv'
    PV_FORECAST_FILE_TIME_RESOLUTION_MIN = 60  # 1
    #SIM_START_TIME = datetime(year=2018, month=10, day=5, hour=11, minute=0, second=0)
    SIM_START_TIME = datetime(year=2018, month=8, day=18, hour=0, minute=0, second=0)
    SIM_START_DAY = (SIM_START_TIME - START_OF_YR).days+1
    SIM_START_HR  = SIM_START_TIME.hour
elif SIM_SCENARIO == 5:
    USE_MATRIX = True
    PV_FORECAST_FILE = 'solar_forecast_matrix.csv'
    PV_TS_FILE       = 'solar_forecast_ts_matrix.csv'
    GHI_FORECAST_FILE = 'ghi_forecast_matrix.csv'
    GHI_TS_FILE       = 'ghi_forecast_ts_matrix_v2.csv'
    PV_FORECAST_FILE_TIME_RESOLUTION_MIN = 60  # 1
    #SIM_START_TIME = datetime(year=2018, month=10, day=5, hour=11, minute=0, second=0)
    SIM_START_TIME = datetime(year=2018, month=10, day=18, hour=0, minute=0, second=0)
    SIM_START_DAY = (SIM_START_TIME - START_OF_YR).days+1
    SIM_START_HR  = SIM_START_TIME.hour
else:
    PV_FORECAST_FILE = "irr_1min.csv"
    PV_FORECAST_FILE_TIME_RESOLUTION_MIN = 1
    SIM_START_DAY = 200  # day 106 #2  # day 202, Hr = 5 # 200, Hr = 7
    SIM_START_HR  = 7
    USE_MATRIX = False

######################################
## for simulated demand data:
DEMAND_FORECAST_FILE = "NYC_demand.csv" #"NYC_forecast_interpolated.csv"
DEMAND_FILE          = DEMAND_FORECAST_FILE #"NYC_demand_interpolated.csv"
DEMAND_FORECAST_FILE_TIME_RESOLUTION_MIN = 60
DEMAND_FILE_TIME_RESOLUTION_MIN = DEMAND_FORECAST_FILE_TIME_RESOLUTION_MIN #1

SIM_START_TIME = START_OF_YR + timedelta(hours=SIM_START_HR, days=SIM_START_DAY-1)

####################################################################33
# Set schedules for querying external devices:
if USE_SIM == 1:   # schedules for simulated testing

    if SIM_HRS_PER_HR == 1:
        CPR_QUERY_INTERVAL = 20*60  # period in seconds for forecasts to arrive
        CPR_1MIN_QUERY_INTERVAL = 300
        DEMAND_FORECAST_QUERY_INTERVAL = 20*60  # seconds
        DEMAND_FORECAST_RESOLUTION = SSA_SCHEDULE_RESOLUTION  # 60 minutes # MATT
        LOADSHIFT_QUERY_INTERVAL = 10*60  # seconds
        DEMAND_REPORT_SCHEDULE = 15*60  # SECONDS
        DEMAND_REPORT_RESOLUTION = 60  # minutes Time resolution of load request report - ONLY SUPPORTS 60 MIN
        DEMAND_REPORT_DURATION = 24 * 60  # minutes for load request
        N_LOADSHIFT_PROFILES = 5
        STATUS_REPORT_SCHEDULE = 60*60  # in seconds # Time interval at which the GS should poll the FLAME to check for status
        LOADSHIFT_FORECAST_UPDATE_INTERVAL = 2 * 60  # # seconds

        HI_RES_DEMAND_REPORT_DURATION = 60  # minutes
        HI_RES_DEMAND_REPORT_RESOLUTION = 1  # minute
        HI_RES_DEMAND_REPORT_SCHEDULE = 5*60 #DEMAND_REPORT_SCHEDULE  # seconds

    CPR_QUERY_INTERVAL = 60 # period in seconds for forecasts to arrive
    CPR_1MIN_QUERY_INTERVAL = 30
    DEMAND_FORECAST_QUERY_INTERVAL = 60 # seconds
    DEMAND_FORECAST_RESOLUTION = SSA_SCHEDULE_RESOLUTION # 60 minutes # MATT
    LOADSHIFT_QUERY_INTERVAL = 10 # seconds
    DEMAND_REPORT_SCHEDULE = 60 # SECONDS
    DEMAND_REPORT_RESOLUTION = 60 # minutes Time resolution of load request report - ONLY SUPPORTS 60 MIN
    DEMAND_REPORT_DURATION   = 24*60 # minutes for load request
    N_LOADSHIFT_PROFILES   = 5
    STATUS_REPORT_SCHEDULE = 60 # in seconds # Time interval at which the GS should poll the FLAME to check for status
    LOADSHIFT_FORECAST_UPDATE_INTERVAL = 30*60 # # seconds

    HI_RES_DEMAND_REPORT_DURATION   = 60 # minutes
    HI_RES_DEMAND_REPORT_RESOLUTION = 1 # minute
    HI_RES_DEMAND_REPORT_SCHEDULE   = DEMAND_REPORT_SCHEDULE # seconds

else:   # schedules associated with live testing
    CPR_QUERY_INTERVAL = 20*60 # period in seconds for forecasts to arrive
    CPR_1MIN_QUERY_INTERVAL = 300
    DEMAND_FORECAST_QUERY_INTERVAL = 20*60 # seconds
    DEMAND_FORECAST_RESOLUTION = SSA_SCHEDULE_RESOLUTION # 60 minutes # MATT - "PT1H"
    LOADSHIFT_QUERY_INTERVAL = 10*60 # seconds
    DEMAND_REPORT_SCHEDULE = 15*60 # SECONDS
    DEMAND_REPORT_RESOLUTION = 60 # minutes Time resolution of load request report - ONLY SUPPORTS 60 MIN
    DEMAND_REPORT_DURATION =  24*60 # Duration of load request reports in minutes
    N_LOADSHIFT_PROFILES   = 2
    STATUS_REPORT_SCHEDULE = 60*60 # in seconds # Time interval at which the GS should poll the FLAME to check for status

    HI_RES_DEMAND_REPORT_DURATION   = 60 # minutes
    HI_RES_DEMAND_REPORT_RESOLUTION = 1 # minute
    HI_RES_DEMAND_REPORT_SCHEDULE   = 5*60 # seconds

    LOADSHIFT_FORECAST_UPDATE_INTERVAL = 30*60 # # seconds


