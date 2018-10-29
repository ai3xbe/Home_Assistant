import appdaemon.plugins.hass.hassapi as hass
import datetime
from datetime import timedelta
from datetime import datetime, timezone

######################
#
# presence.py
#
# By Alex Beckett
# Date: May 2018
#
# Presence detection using a PIR sensor (or input boolean). 
# Note: Presence devices SHOULD NOT STAY ON. They should only trigger on a movement then quickly reset.
#Sets a timer for dim and off. 
# Changes lights depending upon a mode switch (input selector) and then calls an appropriate script appending _dim for dimming.
# script called is made up of the script_prefix, the mode and then _dim if in a dimmed state
# eg. script.alex_office_mode_0_dim
# To turn off we call _off.
# eg. script.alex_office_off
#
# SETUP:
# automation_office:
#  module: presence
#  class: PresenceDetection
#  debug: 'true'
#  script_prefix: 'alex_office'
#  sensor: 'binary_sensor.alexoffice_presence'
#  mode_switch: 'input_select.alexoffice_presence_mode'
#  dim_time: 600 #in seconds - time to start dimming to show possible non-presence
#  off_time: 900 #in seconds - time to switch off the script
#
#####################

class PresenceDetection(hass.Hass):

  def initialize(self):
          
  #Setup initial variables
     self.sensor = self.args["sensor"]
     self.mode_switch = self.args["mode_switch"]
     self.script_prefix = self.args["script_prefix"]
     self.dim_time = self.args["dim_time"]
     self.off_time = self.args["off_time"]
     self.debug = self.args["debug"]
     self.debug_str = self.sensor

     #setup devices to listen on and tracker to make sure it's not us changing!
     self.devices = []
     self.last_update_time = datetime.now(timezone.utc)
     if "devices" in self.args:
       self.devices = self.args["devices"]
       self.dbglog("Devices Present")
     for device in self.devices:
       self.device_listener = self.listen_state(self.device_change, device)
      
     

     #set the current state
     self.current_state = "off"
     self.log("   " + self.script_prefix + ": Enabling Motion Detection")
     
     #listen for motion on given sensor
     
     self.motion_listener = self.listen_state(self.motion, self.sensor, new = "on")
     self.motion_listener2 = self.listen_state(self.motion_off, self.sensor, new = "off")
     self.motion_on = self.run_in(self.enable_motion_listener, 2)
     self.mode_listener = self.listen_state(self.mode_change, self.mode_switch)
     
     #setup timers. This is to avoid a null later on
     self.dim_timer = self.run_in(self.dim, 10)
     self.off_timer = self.run_in(self.off, 10)
     self.cancel_timer(self.dim_timer)  
     self.cancel_timer(self.off_timer)


     
  #used to enable and disable motion control
  def disable_motion_listener(self, kwargs):
    if (self.motion_listener is None):
      self.dbglog("Already Disabled motion listener")
    else:
      self.dbglog("Disabling Motion Listener")
      self.motion_listener = self.cancel_listen_state(self.motion_listener)
      self.motion_listener2 = self.cancel_listen_state(self.motion_listener2)

  def enable_motion_listener(self, kwargs):
    self.dbglog("Enabling Motion Listener")
    #cancel previous motion listener and start a new one. 
    self.motion_listener = self.cancel_listen_state(self.motion_listener)
    self.motion_listener2 = self.cancel_listen_state(self.motion_listener2)
    self.motion_listener = self.listen_state(self.motion, self.sensor, new = "on")
    self.motion_listener2 = self.listen_state(self.motion_off, self.sensor, new = "off")



  #called when the mode is changed. Updates lights accordingly.
  def mode_change(self, entity, attribute, old, new, kwargs):
   
    #exit if it didn't actually change
    if (old == new):
      self.dbglog("Mode change detected for " + str(entity) + " No change made though")
      return
    #calculate what the old mode would be with the old attribute passed here
    old_mode = old.replace(" ", "_")
    old_mode = ("script." + self.script_prefix+ "_" + old_mode.lower())
    self.dbglog("Mode change. Old mode = " + old_mode + " Current State = " + self.current_state)
    
    #turn back on the motion listener
    self.enable_motion_listener("")

    #check to see if out current state was on/dim/off
    if (self.current_state == old_mode):
      self.dbglog("Old mode was in state ON.")
      self.change_lights(new)
      
    if (self.current_state == (old_mode + "_dim")):
      self.dbglog("Old mode was in state DIM.")
      self.change_lights(new + "_dim")
    
    if (self.current_state == ("script." + self.script_prefix+ "_off")):
      self.dbglog("Old mode was in state OFF.")
      #reset current state to force another off.
      self.current_state= ""
      self.change_lights("off")
      




  #Function to detect device changes which were caused manually by the user. Compare time of device change to when we last made a change
  #If you turn a device off it will cancel dimming the room
  def device_change(self, entity, attribute, old, new, kwargs):
    self.current_time = datetime.now(timezone.utc)
    self.timeout_time = self.last_update_time + timedelta(seconds=10)

    #bail out if not actual change
    if (new == old):
      self.dbglog("No actual change, exiting   " + str(entity))
      return

    if (self.current_time <= self.timeout_time):
      self.dbglog("App Triggered -  " + str(entity) + " State = " + str(new)+ " old state = " + str(old))
    else:
      self.dbglog("Manually Triggered -  " + str(entity) + " State = " + str(new) + " old state = " + str(old))
      if (new == "off"):
        self.dbglog("Deviced turned off - cancelling Dim")
        self.cancel_timer(self.dim_timer)
        self.disable_motion_listener("")
        self.motion_on = self.cancel_timer(self.motion_on)  
        self.motion_on = self.run_in(self.enable_motion_listener, 10)
        #self.current_state = "Custom"
      if (new == 'on'):
        self.dbglog("Deviced turned on - cancelling auto for 1hr")
        self.disable_motion_listener("")
        #Cancel current timers
        self.cancel_timer(self.dim_timer)  
        self.cancel_timer(self.off_timer)
        self.motion_on = self.cancel_timer(self.motion_on) 

        self.motion_on = self.run_in(self.enable_motion_listener, 3600)
        self.off_timer = self.run_in(self.off, 4000)
        #self.current_state = "Custom"
  
  
  



     
  #Triggered by motion. First we disable any current timers then perform the action
  def motion(self, entity, attribute, old, new, kwargs):
    self.dbglog("   " + self.script_prefix +":  Motion on " + self.sensor)
    
    #Cancel current timers
    self.cancel_timer(self.dim_timer)  
    self.cancel_timer(self.off_timer)
    
    #get mode info and set lights accordingly
    self.mode = (self.get_state(self.mode_switch, attribute="state"))
    self.change_lights(self.mode)
    
  
  #set the dim and off timers when there is no longer presence
  def motion_off(self, entity, attribute, old, new, kwargs):
    #Set new timers
    self.dbglog("Motion off - setting timers Dim time = " + str(self.dim_time) + " off time = " + str(self.off_time))
    #Cancel current timers
    self.cancel_timer(self.dim_timer)  
    self.cancel_timer(self.off_timer)

    self.dim_timer = self.run_in(self.dim, self.dim_time)
    self.off_timer = self.run_in(self.off, self.off_time)
  
          
        
  def dim(self, kwargs):
    self.dbglog("   " + self.script_prefix +": Dimming")
    self.mode = (self.get_state(self.mode_switch, attribute="state"))
    self.change_lights(self.mode + "_dim")
    
    
  def off(self, kwargs):
    self.dbglog("   " + self.script_prefix +": Turning off")
    self.change_lights("off")
    
    
  #change lights if they're not already set
  def change_lights(self, mode):
    self.dbglog("Possibly Changing Lights...")
    #replace the " " characters in mode names with _ hence "Mode 1" becomes Mode_1
    mode = mode.replace(" ", "_")
    self.turn_on_string = ("script." + self.script_prefix+ "_" + mode.lower())

    if (self.current_state != self.turn_on_string):    
      self.last_update_time =  datetime.now(timezone.utc)
      self.dbglog("  Turning on with: " + str(self.turn_on_string))
      self.turn_on(self.turn_on_string)
      self.current_state = self.turn_on_string

    
  def dbglog(self, message):
    if (self.debug == 'true'):
      self.log("DEBUG: " + self.debug_str + ":   " + str(message))
