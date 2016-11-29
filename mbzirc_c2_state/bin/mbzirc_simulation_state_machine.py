#!/usr/bin/env python

""" mbzirc_simulation_state_machine.py - Version 1.0 2016-10-12

    This program node defines the state machine for Challenge 2

    Author: Alan Lattimer (alattimer at jensenhughes dot com)

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
import smach_ros
from navigate_states import *
from orient_states import *
from grasp_wrench_states import *
from operate_valve_states import *
from test_states import *
from control_msgs.msg import *
from trajectory_msgs.msg import *

# *************************************************************************
# State classes are defined in files associated with the sub-state machine
#
# navigation_states.py
#   FindBoard
#
# orient_states.py
#   Orient
#
# grasp_wrench_states.py
#   MoveToReady
#   MoveToReadyWreanch
#   IDWrench
#   MoveToWrench
#   MoveToGrasp
#   GraspWrench
#
# operate_valve_states.py
#   MoveToValveReady
#   IDValve
#   MoveToValve
#   MoveToOperate
#   RotateValve
#
# test_states.py
#   TestArm
# *************************************************************************

class InitSimulation(smach.State):
    """Initializes the simulation for testing or normal runs

    Outcomes
    --------
        normalRun : start normal simulation
        armTest : perform a test on the arm

    """

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['normal',
                                       'armTest',
                                       'wrenchTest',
                                       'valveTest'],
                             input_keys=['sim_type_in'])

    def execute(self, userdata):

        if userdata.sim_type_in is not 'normal':
            rospy.set_param('wrench',[1.3494152516567712, 0.20670606484791776, 0.36069096929131383])
            rospy.set_param('valve',[1.3494152516567712, 0.4806854679264738, 0.21677653795777196])
            rospy.set_param('ee_position',[0.486, 0.109, 0.620])
            rospy.set_param('stow_position',[0.486, 0.109, 0.620])
            rospy.set_param('current_joint_state', [0, 0, 0, 0, 0, 0])

        rospy.loginfo("Running in %s mode.", userdata.sim_type_in)

        # Sleep to allow the user to pause
        rospy.sleep(5)
        return userdata.sim_type_in


def main():
    """Defines the state machines for Smach
    """

    rospy.init_node('mbzirc_simulation_state_machine', anonymous=True)

    # Create a SMACH state machine
    sm = smach.StateMachine(outcomes=['success', 'failure'])

    # Open the container
    with sm:

        # Create the sub SMACH state machine for navigation
        sm_nav = smach.StateMachine(outcomes=['readyToOrient'])

        # Create the sub SMACH state machine for orienting
        sm_orient = smach.StateMachine(outcomes=['readyToGrabWrench'])

        # Create the sub SMACH state machine for grabbing wrench
        sm_wrench = smach.StateMachine(outcomes=['readyToOperate',
                                                 'testingArm',
                                                 'testWrench',
                                                 'failedToMove',
                                                 'droppedWrench',
                                                 'wrenchIDFailed'])

        # Create the sub SMACH state machine operating the valve
        sm_valve = smach.StateMachine(outcomes=['valveOperated',
                                                'failedToMove',
                                                'failedToStowArm',
                                                'valveIDFailed',
                                                'lostWrench',
                                                'valveStuck'])

        # Define the type of simulation:
        #   'normal'     : Execute the normal plan
        #   'armTest'    : Test the arm for range of motion and stability
        #   'wrenchTest' : Test the wrench manipulation
        #   'valveTest'  : Test the valve operation
        sm.userdata.sim_type = 'wrenchTest'

        # Define userdata for the state machines
        sm_wrench.userdata.move_counter = 0
        sm_wrench.userdata.max_move_retries = 1
        sm_wrench.userdata.have_wrench = False

        sm_valve.userdata.move_counter = 0
        sm_valve.userdata.max_move_retries = 1
        sm_valve.userdata.valve_centered = False
        sm_valve.userdata.valve_turned = False

        # Define the Main State Machine (sm)
        smach.StateMachine.add('INITIALIZATION', InitSimulation(),
                               transitions={'normal' : 'NAVIGATE',
                                            'armTest' : 'TEST_ARM',
                                            'wrenchTest' : 'TEST_WRENCH',
                                            'valveTest' : 'TEST_VALVE'},
                               remapping={'sim_type_in' : 'sim_type'})


        smach.StateMachine.add('NAVIGATE', sm_nav,
                               transitions={'readyToOrient' : 'ORIENT'})

        smach.StateMachine.add('ORIENT', sm_orient,
                               transitions={'readyToGrabWrench' : 'GRAB_WRENCH'})

        smach.StateMachine.add('GRAB_WRENCH', sm_wrench,
                               transitions={'readyToOperate' : 'OPERATE_VALVE',
                                            'testingArm' : 'success',
                                            'testWrench' : 'success',
                                            'failedToMove' : 'failure',
                                            'droppedWrench' : 'failure',
                                            'wrenchIDFailed' : 'failure'},
                               remapping={'sim_type_wrench' : 'sim_type'})

        smach.StateMachine.add('OPERATE_VALVE', sm_valve,
                               transitions={'valveOperated' : 'success',
                                            'failedToMove' : 'failure',
                                            'failedToStowArm' : 'failure',
                                            'valveIDFailed' : 'failure',
                                            'lostWrench' : 'failure',
                                            'valveStuck' : 'failure'})

        smach.StateMachine.add('TEST_ARM', TestArm(),
                               transitions={'armTestComplete' : 'success',
                                            'armTestFailed' : 'failure'})

        smach.StateMachine.add('TEST_WRENCH', TestWrenchGrab(),
                               transitions={'wrenchTestComplete' : 'GRAB_WRENCH',
                                            'wrenchTestFailed' : 'failure'})

        smach.StateMachine.add('TEST_VALVE', TestValveOp(),
                               transitions={'valveOpTestComplete' : 'OPERATE_VALVE',
                                            'valveOpTestFailed' : 'failure'})





        # Define the NAVIGATE State Machine (sm_nav)
        with sm_nav:
            smach.StateMachine.add('FINDBOARD', FindBoard(),
                                   transitions={'atBoard' : 'readyToOrient'})

        # Define the ORIENT State Machine (sm_orient)
        with sm_orient:
            smach.StateMachine.add('ORIENT_HUSKY', Orient(),
                                   transitions={'oriented' : 'readyToGrabWrench'})

        # Define the GRAB_WRENCH State Machine (sm_wrench)
        with sm_wrench:
            smach.StateMachine.add('MOVE_TO_READY', MoveToReady(),
                                   transitions={'atReady' : 'MOVE_WRENCH_READY',
                                                'moveStuck' : 'MOVE_TO_READY',
                                                'moveFailed' : 'failedToMove'},
                                   remapping={'move_counter_in' : 'move_counter',
                                              'max_retries' : 'max_move_retries',
                                              'move_counter_out' : 'move_counter'})

            smach.StateMachine.add('MOVE_WRENCH_READY', MoveToWrenchReady(),
                                   transitions={'atWrenchReady' : 'ID_WRENCH',
                                                'moveToOperate' : 'readyToOperate',
                                                'moveStuck' : 'MOVE_WRENCH_READY',
                                                'moveFailed' : 'failedToMove'},
                                   remapping={'got_wrench' : 'have_wrench',
                                              'move_counter_in' : 'move_counter',
                                              'max_retries' : 'max_move_retries',
                                              'move_counter_out' : 'move_counter'})

            smach.StateMachine.add('ID_WRENCH', IDWrench(),
                                   transitions={'wrenchFound' : 'MOVE_TO_WRENCH',
                                                'armTest' : 'testingArm',
                                                'wrenchNotFound' : 'wrenchIDFailed'})

            smach.StateMachine.add('MOVE_TO_WRENCH', MoveToWrench(),
                                   transitions={'atWrench' : 'MOVE_TO_GRASP',
                                                'moveStuck' : 'MOVE_TO_WRENCH',
                                                'moveFailed' : 'failedToMove'},
                                   remapping={'move_counter_in' : 'move_counter',
                                              'max_retries' : 'max_move_retries',
                                              'move_counter_out' : 'move_counter'})

            smach.StateMachine.add('MOVE_TO_GRASP', MoveToGrasp(),
                                   transitions={'readyToGrasp' : 'GRASP_WRENCH'})

            smach.StateMachine.add('GRASP_WRENCH', GraspWrench(),
                                   transitions={'wrenchGrasped' : 'readyToOperate',
                                                'gripFailure' : 'droppedWrench',
                                                'wrenchTestDone' : 'testWrench'},
                                   remapping={'got_wrench' : 'have_wrench',
                                              'sim_type_in' : 'sim_type_wrench'})

        # Define the OPERATE_VALVE State Machine (sm_valve)
        with sm_valve:
            smach.StateMachine.add('STOW_ARM', StowArm(),
                                   transitions={'armStowed' : 'DRIVE_TO_VALVE',
                                                'stowArmFailed' : 'failedToStowArm'})

            smach.StateMachine.add('DRIVE_TO_VALVE', DriveToValve(),
                                   transitions={'atValveDrive' : 'MOVE_VALVE_READY',
                                                'moveFailed' : 'failedToMove'})

            smach.StateMachine.add('MOVE_VALVE_READY', MoveToValveReady(),
                                   transitions={'atValveReady' : 'ID_VALVE',
                                                'moveStuck' : 'MOVE_VALVE_READY',
                                                'moveFailed' : 'failedToMove'},
                                   remapping={'move_counter_in' : 'move_counter',
                                              'max_retries' : 'max_move_retries',
                                              'move_counter_out' : 'move_counter'})

            smach.StateMachine.add('ID_VALVE', IDValve(),
                                   transitions={'valveLocated' : 'MOVE_TO_VALVE',
                                                'valveNotFound' : 'valveIDFailed'},
                                   remapping={'valve_centered_out' : 'valve_centered'})

            smach.StateMachine.add('MOVE_TO_VALVE', MoveToValve(),
                                   transitions={'servoArm' : 'SERVO_TO_VALVE',
                                                'moveForward' : 'MOVE_TO_OPERATE'},
                                   remapping={'valve_centered_in' : 'valve_centered'})

            smach.StateMachine.add('SERVO_TO_VALVE', ServoToValve(),
                                   transitions={'moveSuccess' : 'ID_VALVE',
                                                'moveFailed' : 'failedToMove'})


            smach.StateMachine.add('MOVE_TO_OPERATE', MoveToOperate(),
                                   transitions={'wrenchFell' : 'lostWrench',
                                                'wrenchOnValve' : 'ROTATE_VALVE'})

            smach.StateMachine.add('ROTATE_VALVE', RotateValve(),
                                   transitions={'wrenchFell' : 'lostWrench',
                                                'cantTurnValve' : 'valveStuck',
                                                'turnedValve' : 'valveOperated'})

    # Create the introspection server
    sis = smach_ros.IntrospectionServer('mbzirc_server', sm, '/CHALLENGE_TWO')
    sis.start()
    # Execute SMACH plan
    outcome = sm.execute()

    rospy.spin()
    sis.stop()


if __name__ == '__main__':
    main()
