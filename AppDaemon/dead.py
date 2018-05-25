import appdaemon.plugins.hass.hassapi as hass
import datetime
from datetime import timedelta
from datetime import datetime, timezone

######################
#
# dead.py
#
# By Alex Beckett
# Date: 26 May 2018
#
# Battery level and death detection
#
#
#####################

class DeadDetector(hass.Hass):

  def initialize(self):
    
     #setup initial variables
     self.device = self.args["zwave_sensor_name"]
     self.friendly_name = (self.get_state(self.device, attribute="friendly_name"))
     self.timeout = self.args["timeout_mins"]
     self.frequency = self.args["check_frequency"] #frequency in seconds
     self.debug = self.args["debug"]
     self.debug_str = self.device
     self.notifier = "pushover"
     self.notification_sent = False
          
     self.log("   " + self.device + ": Enabling Battery Low & Death Detection")
     self.dbglog(self.get_state(self.device, attribute="all"))
     
     #run the checker every x seconds
     self.scheduler = self.run_every(self.check, (datetime.now() + timedelta(minutes=30)), self.frequency)


  #check battery level and whether device is alive
  def check(self, kwargs):
     self.battery_level = (self.get_state(self.device, attribute="battery_level"))
     self.last_update = self.convert_utc(self.get_state(self.device, attribute="last_updated"))
  
  
     #check last update time
     self.current_time = datetime.now(timezone.utc)
     #timeout = last updated time + the timeout defined at the start. Timeout in mins
     self.timeout_time = self.last_update + timedelta(minutes=self.timeout)
     self.dbglog("last update " +  str(self.last_update))
     self.dbglog("current time " + str(self.current_time))
     self.dbglog("timeout time " + str(self.timeout_time))
     
     #notify if change in status
     if (self.current_time < self.timeout_time):
      self.dbglog("Device ONLINE")
      if (self.notification_sent == True):
        self.notification_sent = False
        self.notify(("Device Online. Last seen: " + str(self.last_update) + " Battery Level: " + str(self.battery_level)  + " Time now: " + str(self.current_time)) , title = ("Online: " + self.friendly_name), name = self.notifier)

     else:
      self.dbglog("Device OFFLINE")
      if (self.notification_sent == False):
        self.notify(("Device timeout out. Last seen: " + str(self.last_update) + " Battery Level: " + str(self.battery_level) + " Time now: " + str(self.current_time)) , title = ("Timeout: " + self.friendly_name), name = self.notifier)
        self.notification_sent = True


     self.dbglog("Battery Level = " + str(self.battery_level))


  
  def dbglog(self, message):
    if (self.debug == 'true'):
      self.log("DEBUG: " + self.debug_str + ":   " + str(message))