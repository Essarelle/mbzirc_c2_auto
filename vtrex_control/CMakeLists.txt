cmake_minimum_required(VERSION 2.8.3)
project(vtrex_control)

find_package(catkin REQUIRED COMPONENTS roslaunch)

catkin_package()

roslaunch_add_file_check(launch/vtrex_control.launch)
roslaunch_add_file_check(launch/teleop.launch)
roslaunch_add_file_check(launch/vtrex_hw.launch)

install(DIRECTORY config launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
