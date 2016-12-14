""" grasp_wrench_states.py - Version 1.0 2016-11-10

    State machine classes for grasping a certain wrench from a peg board.

    Classes
        MoveToReady -
        MoveToWrenchReady
        IDWrench
        MoveToWrench
        MoveToGrasp
        GraspWrench

    Alan Lattimer (alattimer at jensenhughes dot com)

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
import smach
import subprocess
from geometry_msgs.msg import Pose, PoseWithCovarianceStamped, Point, Quaternion, Twist
from mbzirc_c2_auto.msg import kf_msg
from twist_command import *

class MoveToReady(smach.State):
    """Moves the arm to the ready state from the stowed state

    Outcomes
    --------
        atReady : at the ready position
        moveStuck : move failed but still retrying
        moveFailed : move failed too many times

    """

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['atReady',
                                       'moveStuck',
                                       'moveFailed'],
                             input_keys=['move_counter_in',
                                         'max_retries'],
                             output_keys=['move_counter_out'])

    def execute(self, userdata):

        if userdata.move_counter_in == 0:
            curr_pos = rospy.get_param('ee_position')
            curr_pos[0] = curr_pos[0] + 0.2
            curr_pos[2] = curr_pos[2] + 0.2
            rospy.set_param('ee_position', [float(curr_pos[0]),
                                            float(curr_pos[1]),
                                            float(curr_pos[2])])

	move_state = twist_command(curr_pos[0], curr_pos[1], curr_pos[2])

        #prc = subprocess.Popen("rosrun mbzirc_grasping move_arm_param.py", shell=True)
        #prc.wait()

        #move_state = rospy.get_param('move_arm_status')

        # Preset the out move counter to 0, override if necessary
        userdata.move_counter_out = 0

        if move_state == 'success':
            return 'atReady'

        else:
            if userdata.move_counter_in < userdata.max_retries:
                userdata.move_counter_out = userdata.move_counter_in + 1
                return 'moveStuck'

            else:
                return 'moveFailed'




class MoveToWrenchReady(smach.State):
    """Moves the arm into position for identifying the wrench

    Outcomes
    --------
        atWrenchReady : at location to determine correct wrench
        moveToOperate
        moveStuck : move failed but still retrying
        moveFailed : move failed too many times

    """

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['atWrenchReady',
                                       'moveToOperate',
                                       'moveStuck',
                                       'moveFailed'],
                             input_keys=['move_counter_in',
                                         'max_retries',
                                         'got_wrench'],
                             output_keys=['move_counter_out'])

    def execute(self, userdata):

        wrench_ready_pos = rospy.get_param('wrench')

        # Set the ready position 40 cm away from the wrenches
        wrench_ready_pos[0] = wrench_ready_pos[0] - 0.6
        wrench_ready_pos[1] = wrench_ready_pos[1] + 0.1
        wrench_ready_pos[2] = 0.3 #wrench_ready_pos[2] - 0.05

        rospy.set_param('ee_position', [float(wrench_ready_pos[0]),
                                        float(wrench_ready_pos[1]),
                                        float(wrench_ready_pos[2])])

	move_state = twist_command(wrench_ready_pos[0], wrench_ready_pos[1], wrench_ready_pos[2])

        #prc = subprocess.Popen("rosrun mbzirc_grasping move_arm_param.py", shell=True)
        #prc.wait()

        #move_state = rospy.get_param('move_arm_status')

        # Preset the out move counter to 0, override if necessary
        userdata.move_counter_out = 0


        if move_state == 'success':
            if userdata.got_wrench is True:
                return 'moveToOperate'
            else:
                ve = 0.1
                dist_to_move = 0.0
                sleep_time = 0.1
                time_to_move = abs(dist_to_move/ve)
                twist = Twist()
                twist.linear.x = ve
                twist.linear.y = 0
                twist.linear.z = 0
                twist.angular.x = 0
                twist.angular.y = 0
                twist.angular.z = 0
                twi_pub = rospy.Publisher("/joy_teleop/cmd_vel", Twist, queue_size=10)
                ct_move = 0
                while ct_move*sleep_time < time_to_move:
                    twi_pub.publish(twist)
                    ct_move = ct_move+1
                    rospy.sleep(sleep_time)
                return 'atWrenchReady'


        else:
            if userdata.move_counter_in < userdata.max_retries:
                userdata.move_counter_out = userdata.move_counter_in + 1
                return 'moveStuck'

            else:
                return 'moveFailed'



class IDWrench(smach.State):
    """ID the correct wrench

    Outcomes
    --------
        wrenchNotFound : unable to locate the correct wrench
        wrenchFound : located the correct wrench

    """

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['wrenchFound',
                                       'armTest',
                                       'wrenchNotFound'])

    def execute(self, userdata):
        prc = subprocess.Popen("rosrun mbzirc_c2_auto idwrench2.py", shell=True)
        prc.wait()

        ret_state = rospy.get_param('smach_state')
        return ret_state




class MoveToWrench(smach.State):
    """Move in front of correct wrench to servo in to wrench

    Outcomes
    --------
        atWrench : in front of wrench
        moveStuck : move failed but still retrying
        moveFailed : move failed too many times

    """

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['atWrench',
                                       'moveStuck',
                                       'moveFailed'],
                             input_keys=['move_counter_in',
                                         'max_retries'],
                             output_keys=['move_counter_out'])

    def callback(self, data):
        self.valve_pos_kf = data

    def execute(self, userdata):
        rospy.Subscriber('/move_arm/valve_pos_kf', Twist, self.callback)
        rospy.sleep(0.1)
        wrench_id = rospy.get_param('wrench_ID_m')
        rospy.sleep(0.1)
        ee_position = rospy.get_param('ee_position')
        print "wrench_id", wrench_id
        print "ee_position", ee_position
        # Set the ready position 40 cm away from the wrenches
        wrench_id[0] = ee_position[0]+wrench_id[0]-0.6
        wrench_id[1] = ee_position[1]+wrench_id[1]
        wrench_id[2] = ee_position[2]+wrench_id[2]-0.1

        rospy.set_param('ee_position', [float(wrench_id[0]),
                                        float(wrench_id[1]),
                                        float(wrench_id[2])])

	move_state = twist_command(wrench_id[0], wrench_id[1], wrench_id[2])

        #prc = subprocess.Popen("rosrun mbzirc_grasping move_arm_param.py", shell=True)
        #prc.wait()
        ve = 0.1
        dist_to_move = 0.2
        sleep_time = 0.1
        time_to_move = abs(dist_to_move/ve)
        twist = Twist()
        twist.linear.x = ve
        twist.linear.y = 0
        twist.linear.z = 0
        twist.angular.x = 0
        twist.angular.y = 0
        twist.angular.z = 0
        twi_pub = rospy.Publisher("/joy_teleop/cmd_vel", Twist, queue_size=10)
        ct_move = 0
        while ct_move*sleep_time < time_to_move:
            twi_pub.publish(twist)
            ct_move = ct_move+1
            rospy.sleep(sleep_time)
        move_state = rospy.get_param('move_arm_status')
        wrench_id[0] = wrench_id[0]-dist_to_move
        rospy.set_param('wrench_ID_m',wrench_id)
        gripper_pub = rospy.Publisher('gripper/cmd_vel', Twist, queue_size = 1)
        twist = Twist()
        speed = .5; turn = 1
        x = 0; y = 0; z = 0;
        th = 1 # To open gripper (1) use th = 1
        twist.linear.x = x*speed;
        twist.linear.y = y*speed;
        twist.linear.z = z*speed;
        twist.angular.x = 0;
        twist.angular.y = 0;
        twist.angular.z = th*turn

        ct = 0
        rest_time = 0.1
        tot_time = 3

        while ct*rest_time < tot_time:
            gripper_pub.publish(twist)
            rospy.sleep(0.1)
            ct = ct+1
        # Preset the out move counter to 0, override if necessary
        userdata.move_counter_out = 0

        if move_state == 'success':
            rospy.sleep(0.1)
            wrench_id = rospy.get_param('wrench_ID_m')
            wrench_id[0]
            print "Wrench ID: ", wrench_id
            thresh = 10
            xA = 20
            ee_position = rospy.get_param('ee_position')
            ct3 = 0
            ee_position[0] = ee_position[0]+0.06

            kf = kf_msg()
            kf_pub = rospy.Publisher("/move_arm/kf_init", kf_msg, queue_size=1, latch=True)
            ee_pub = rospy.Publisher("/move_arm/valve_pos", Twist, queue_size=1)
            kf.initial_pos = [0,0,0,0,0,0]
            kf.initial_covar = [0.001,0.001]
            kf.covar_motion = [0.001,0.001]
            kf.covar_observer = [0.001,0.001]

            kf_pub.publish(kf)
            rospy.sleep(0.1) # Wait for 0.1s to ensure init topic is published
            rospy.sleep(1) # Wait for 1.0s to ensure init routine is completed
            ee_twist = Twist()

            while ee_position[0] < xA+0.461-0.155:
                rospy.sleep(0.1)

                prc = subprocess.Popen("rosrun mbzirc_c2_auto centerwrench.py", shell=True)
                prc.wait()
                rospy.sleep(0.1)
                dist = rospy.get_param("wrench_ID_dist")
                rospy.sleep(0.1)
                wrench_id = rospy.get_param('wrench_ID_m')
                rospy.sleep(0.1)
                ee_position = rospy.get_param('ee_position')
                rospy.sleep(0.1)
                wrench_id_px = rospy.get_param('wrench_ID')
                rospy.sleep(0.1)
                print "wrench_id", wrench_id
                print "Wrench_id_px: ", wrench_id_px
                dx = wrench_id[0]*0.05
                xA = rospy.get_param('xA')
                # Set the ready position 40 cm away from the wrenches
                ee_position[0] = (xA + 0.461-0.17)+0.005*ct3 # 0.134 distance from camera to left_tip   
                print "ee_position before Kalman filter", ee_position
                print "************************************************"
                ee_twist.linear.x = ee_position[0]
                ee_twist.linear.y = wrench_id[1]
                ee_twist.linear.z = wrench_id[2]
                ee_pub.publish(ee_twist)
                rospy.sleep(0.1)
                tw = self.valve_pos_kf
                print "Estimated pose from Kalman filter: ", tw

                #ee_position[0] = ee_position[0]+0.005 #
                ee_position[1] = ee_position[1]+tw.linear.y
                ee_position[2] = ee_position[2]+tw.linear.z
                rospy.set_param('ee_position', [float(ee_position[0]),
                                                float(ee_position[1]),
                                                float(ee_position[2])])
                rospy.sleep(0.1)
                rospy.set_param('wrench_ID_m',[wrench_id[0]-dx,wrench_id[1],wrench_id[2]])
                rospy.sleep(0.1)
                print "***********************************************"
                print "ee_position after Kalman filter", ee_position
                ee_twist.linear.y = ee_position[1]
                ee_twist.linear.z = ee_position[2]

		move_state = twist_command(ee_twist.linear.x, ee_twist.linear.y, ee_twist.linear.z)

                #prc = subprocess.Popen("rosrun mbzirc_grasping move_arm_param.py", shell=True)
                #prc.wait()
                ct3 = ct3+1
            print "We are close enough! Distance = ", dist
            return 'atWrench'

        else:
            if userdata.move_counter_in < userdata.max_retries:
                userdata.move_counter_out = userdata.move_counter_in + 1
                return 'moveStuck'

            else:
                return 'moveFailed'

class MoveToGrasp(smach.State):
    """Video servo to the grasp position

    Outcomes
    --------
        readyToGrasp - in position for the gripper to grab wrench

    """

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['readyToGrasp'])

    def execute(self, userdata):
        prc = subprocess.Popen("rosrun mbzirc_c2_auto move2grasp.py", shell=True)
        prc.wait()
        return rospy.get_param('smach_state')



class GraspWrench(smach.State):
    """Close the gripper

    Outcomes
    --------
        wrenchGrasped - Grabbed the wrench
        gripFailure - failed to grab the wrench

    """

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['wrenchGrasped',
                                       'gripFailure',
                                       'wrenchTestDone'],
                             input_keys=['sim_type_in'],
                             output_keys=['got_wrench'])

    def execute(self, userdata):
        prc = subprocess.Popen("rosrun mbzirc_c2_auto grasp.py", shell=True)
        rospy.sleep(2)
        #prc.wait()
        ee_position = rospy.get_param('ee_position')
        ee_position[0] = ee_position[0]-0.1
        rospy.set_param('ee_position', [float(ee_position[0]),
                                        float(ee_position[1]),
                                        float(ee_position[2])])
        rospy.sleep(0.1)

	move_state = twist_command(ee_position[0], ee_position[1], ee_position[2])

        #prc = subprocess.Popen("rosrun mbzirc_grasping move_arm_param.py", shell=True)
        #prc.wait()

        #ve = -0.1
        #dist_to_move = 0.2
        #sleep_time = 0.1
        #time_to_move = abs(dist_to_move/ve)
        #twist = Twist()
        #twist.linear.x = ve
        #twist.linear.y = 0
        #twist.linear.z = 0
        #twist.angular.x = 0
        #twist.angular.y = 0
        #twist.angular.z = 0
        #twi_pub = rospy.Publisher("/joy_teleop/cmd_vel", Twist, queue_size=10)
        #ct_move = 0
        #while ct_move*sleep_time < time_to_move:
        #    twi_pub.publish(twist)
        #    ct_move = ct_move+1
        #    rospy.sleep(sleep_time)
        #prc.wait()
        rospy.sleep(0.1)
        rospy.set_param('smach_state','wrenchGrasped')
        rospy.sleep(0.1)
        status = rospy.get_param('smach_state')

        if status == 'wrenchGrasped':
            userdata.got_wrench = True

        if userdata.sim_type_in == 'normal':
            return status
        else:
            return 'wrenchTestDone'


