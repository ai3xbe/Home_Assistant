import appdaemon.plugins.hass.hassapi as hass

######################
#
# presence.py
#
# By Alex Beckett
# Date: May 2018
#
# Presence detection using a PIR sensor (or input boolean). Sets a timer for dim and off. 
# Changes lights depending upon a mode switch (input selector) and then calls an appropriate scene appending _dim for dimming.
# Scene called is made up of the scene_prefix, the mode and then _dim if in a dimmed state
# eg. scene.alex_office_mode_0_dim
# To turn off we call _off.
# eg. scene.alex_office_off
#
# SETUP:
# automation_office:
#  module: presence
#  class: PresenceDetection
#  debug: 'true'
#  scene_prefix: 'alex_office'
#  sensor: 'binary_sensor.alexoffice_presence'
#  mode_switch: 'input_select.alexoffice_presence_mode'
#  dim_time: 600 #in seconds - time to start dimming to show possible non-presence
#  off_time: 900 #in seconds - time to switch off the scene
#
#####################

class PresenceDetection(hass.Hass):

  def initialize(self):
     
          
     #Setup initial variables
     self.sensor = self.args["sensor"]
     self.mode_switch = self.args["mode_switch"]
     self.scene_prefix = self.args["scene_prefix"]
     self.dim_time = self.args["dim_time"]
     self.off_time = self.args["off_time"]
     self.debug = self.args["debug"]
     self.debug_str = self.sensor
     
     #set the current state
     self.current_state = "off"
     
     self.log("   " + self.scene_prefix + ": Enabling Motion Detection")
     
     #listen for motion on given sensor
     self.motion_listener = self.listen_state(self.motion, self.sensor, new = "on")
     self.mode_listener = self.listen_state(self.mode_change, self.mode_switch)
     
     #setup timers. This is to avoid a null later on
     self.dim_timer = self.run_in(self.dim, 10)
     self.off_timer = self.run_in(self.off, 10)
     self.cancel_timer(self.dim_timer)  
     self.cancel_timer(self.off_timer)
     


#called when the mode is changed. Updates lights accordingly.
  def mode_change(self, entity, attribute, old, new, kwargs):
    #calculate what the old mode would be with the old attribute passed here
    old_mode = old.replace(" ", "_")
    old_mode = ("scene." + self.scene_prefix+ "_" + old_mode.lower())
    self.dbglog("Mode change. Old mode = " + old_mode + " Current State = " + self.current_state)
    
    #check to see if out current state was on/dim/off
    if (self.current_state == old_mode):
      self.dbglog("Old mode was in state ON.")
      self.change_lights(new)
      
    if (self.current_state == (old_mode + "_dim")):
      self.dbglog("Old mode was in state DIM.")
      self.change_lights(new + "_dim")
    
    if (self.current_state == ("scene." + self.scene_prefix+ "_off")):
      self.dbglog("Old mode was in state OFF.")
      #reset current state to force another off.
      self.current_state= ""
      self.change_lights("off")
      

  
     
  #Triggered by motion. First we disable any current timers then perform the action
  def motion(self, entity, attribute, old, new, kwargs):
    self.dbglog("   " + self.scene_prefix +":  Motion on " + self.sensor)
    
    #Cancel current timers
    self.cancel_timer(self.dim_timer)  
    self.cancel_timer(self.off_timer)
    

    self.mode = (self.get_state(self.mode_switch, attribute="state"))
    self.change_lights(self.mode)
    
    #Set new timers
    self.dim_timer = self.run_in(self.dim, self.dim_time)
    self.off_timer = self.run_in(self.off, self.off_time)
  
          
        
  def dim(self, kwargs):
    self.dbglog("   " + self.scene_prefix +": Dimming")
    self.mode = (self.get_state(self.mode_switch, attribute="state"))
    self.change_lights(self.mode + "_dim")
    
    
  def off(self, kwargs):
    self.dbglog("   " + self.scene_prefix +": Turning off")
    self.change_lights("off")
    
    
  #change lights if they're not already set
  def change_lights(self, mode):
    #replace the " " characters in mode names with _ hence "Mode 1" becomes Mode_1
    mode = mode.replace(" ", "_")

    self.turn_on_string = ("scene." + self.scene_prefix+ "_" + mode.lower())

    if (self.current_state != self.turn_on_string):    
      self.dbglog("Turning on with: " + str(self.turn_on_string))
      self.turn_on(self.turn_on_string)
      self.current_state = self.turn_on_string
      

    
  def dbglog(self, message):
    if (self.debug == 'true'):
      self.log("DEBUG: " + self.debug_str + ":   " + str(message))
