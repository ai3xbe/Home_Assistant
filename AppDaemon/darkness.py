import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime

class darkdetector(hass.Hass):

  def initialize(self):
    self.dark_switch_name = self.args["dark_switch_name"]
    self.dark_threshold_device = self.args["dark_threshold"]
    self.sensor = self.args["sensor"]
  
    self.debug = self.args["debug"]
    self.debug_str = self.dark_switch_name
    
    self.dark_threshold = self.get_state(self.dark_threshold_device)
    
    self.log("Starting Darkness Detector. Current Threshold = " + str(self.dark_threshold))
  
    self.threshold_listenr = self.listen_state(self.threshold_change, self.dark_threshold_device)
    self.dark_listener = self.listen_state(self.light_changed, self.sensor)

  
  
  def threshold_change(self, entity, attribute, old, new, kwargs):
    self.dark_threshold = new
    self.dbglog("Darkness Threshold Changed. Now = " + str(self.dark_threshold))
    sensor_value =  float(self.get_state(self.sensor))
    self.dbglog("sensor = " + str(sensor_value))
    if (float(new) < sensor_value):
      self.dbglog("Dark")
      self.turn_off(self.dark_switch_name)
      self.turn_on("script.house_mode_0")
    else:
      self.dbglog("Not Dark")
      self.turn_on(self.dark_switch_name)
      self.turn_on("script.house_mode_1")
  
  def light_changed(self, entity, attribute, old, new, kwargs):
    self.dbglog("light level changed now = " + str(new))
    self.dbglog("sensor = " + str(self.get_state(self.sensor)))
    currentState = self.entities.input_select.house_presence_mode.state
    intervalTime = datetime.now().timestamp() - (self.convert_utc(self.entities.input_select.house_presence_mode.last_changed).timestamp())
    #if greater than 10mins since last updated....
    if (intervalTime > (60* 10)):
      if (float(self.get_state(self.sensor)) < float(self.dark_threshold)):
        self.turn_on(self.dark_switch_name)
        #only update the lights if they're not already on. This is to prevent going from a dimmed state to full on.
        if (currentState == "Mode 0"):
          self.turn_on("script.house_mode_1")
      else:
        self.turn_off(self.dark_switch_name)
        self.turn_on("script.house_mode_0")
  
  
  def dbglog(self, message):
    if (self.debug == 'true'):
      self.log("DEBUG: " + self.debug_str + ":   " + str(message))