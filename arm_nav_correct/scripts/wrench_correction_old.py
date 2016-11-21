#!/usr/bin/env python

"""
    arm_nav_correcton.py - Version 0.1 2016-11-03

    Luan Cong Doan _ CMS Lab
    luandoan@vt.edu

    Use inverse kinemtatics to move the end effector from prediction point to the center point of wrench

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.5

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details at:

    http://www.gnu.org/licenses/gpl.html
"""

import rospy
import sys
import moveit_commander
from geometry_msgs.msg import PoseArray, PoseStamped
from copy import deepcopy

class WrenchCorrection:
    def __init__(self):
        #Give the node a name
        rospy.init_node("wrench_correction", anonymous=False)
        
        rospy.loginfo("Starting node Wrench navigation correction")
        
        rospy.on_shutdown(self.cleanup)

        # Initialize the move_group API
        moveit_commander.roscpp_initialize(sys.argv)

        # Initialize the move group for the ur5_arm
        self.arm = moveit_commander.MoveGroupCommander("ur5_arm")

        # Get the name of the end-effector link
        end_effector_link = self.arm.get_end_effector_link()

        # Initialize Necessary Variables
        self.reference_frame = rospy.get_param("~reference_frame", "/base_link")
        self.location = rospy.get_param("~location", 1)
        self.error_y = rospy.get_param("~error_y", 0)
        self.error_z = rospy.get_param("~error_z", 0)

        # Set the ur5_arm reference frame accordingly
        self.arm.set_pose_reference_frame(self.reference_frame)

        # Allow replanning to increase the odds of a solution
        self.arm.allow_replanning(True)

        # Allow some leeway in position (meters) and orientation (radians)
        self.arm.set_goal_position_tolerance(0.0001)
        self.arm.set_goal_orientation_tolerance(0.0001)
        
        # Get the current pose
        start_pose = self.arm.get_current_pose(end_effector_link).pose
        
        # Adjust start_pose based on camera feedback
        wrench_pose = deepcopy(start_pose)
        wrench_pose.position.y += self.error_y
        wrench_pose.position.z += self.error_z

        #Move the end effecor to the x, y, z positon
        #Set the target pose to the wrench location in the base_link frame
        target_pose = PoseStamped()
        target_pose.header.frame_id = self.reference_frame
        target_pose.header.stamp = rospy.Time.now()
        target_pose.pose.position.x = wrench_pose.position.x
        target_pose.pose.position.y = wrench_pose.position.y
        target_pose.pose.position.z = wrench_pose.position.z
        #target_pose.pose.orientation.x = wrench_pose.orientation.x
        #target_pose.pose.orientation.y = wrench_pose.orientation.y
        #target_pose.pose.orientation.z = wrench_pose.orientation.z
        #target_pose.pose.orientation.w = wrench_pose.orientation.w

        # Set the start state to the current state
        self.arm.set_start_state_to_current_state()

        # Set the goal pose of the gripper to the stored pose
        self.arm.set_pose_target(target_pose, gripper_link)

        # Plan the trajectory to the goal
        traj = self.arm.plan()
        
        if traj is not None:
            # Execute the planned trajectory
            self.arm.execute(traj)
            
             # Pause for a second
            rospy.sleep(1)
                
            rospy.loginfo("Successfully updated position of wrench " + str(self.location))
                
        else:
            rospy.loginfo("Unable to update position of wrench " + str(self.location))

    def cleanup(self):
        rospy.loginfo("Stopping the robot")
    
        # Stop any current arm movement
        self.arm.stop()
        
        #Shut down MoveIt! cleanly
        rospy.loginfo("Shutting down Moveit!")
        moveit_commander.roscpp_shutdown()
        moveit_commander.os._exit(0)


if __name__ == "__main__":
  try:
    WrenchCorrection()
  except KeyboardInterrupt:
      print "Shutting down WrenchCorrection node."
