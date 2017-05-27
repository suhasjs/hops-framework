"""
Interface to control Ant hexapod robot, in one of two modes:
 * Full Force/Torque Control Mode
 * Inverse Kinematics Mode (Hybrid), using Position Control (PID)
"""

import time
import numpy as np
import vrep
import math

class Ant:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_id = None
        self.handles = None

    def init_client(self):
        # Stop any previous simulation
        vrep.simxStopSimulation(-1, vrep.simx_opmode_oneshot_wait)
        # Start a client
        self.client_id = vrep.simxStart(self.server_ip, self.server_port, True, True, 5000, 5)
        assert self.client_id != -1, 'Failed connecting to remote API server'

        # Enable synchronous mode
        e = vrep.simxSynchronous(self.client_id, True)
        assert e != -1, 'Failed enabling remote API synchronous mode'

        # Start simulation
        e = vrep.simxStartSimulation(self.client_id, vrep.simx_opmode_blocking)
        assert e != -1, 'Failed to start simulation'

        # Print ping time
        sec, msec = vrep.simxGetPingTime(self.client_id)
        print "Started simulation on %s:%d" % (self.server_ip, self.server_port)
        print "Ping time: %f" % (sec + msec / 1000.0)

        # Obtain handle for body (for orientation, positions etc)
        _, self.body_handle = vrep.simxGetObjectHandle(self.client_id, 'Ant_body', vrep.simx_opmode_blocking)

        # Obtain joint handles
        _, Ant_joint1Leg1 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint1Leg1', vrep.simx_opmode_blocking)
        _, Ant_joint2Leg1 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint2Leg1', vrep.simx_opmode_blocking)
        _, Ant_joint3Leg1 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint3Leg1', vrep.simx_opmode_blocking)
        _, Ant_joint1Leg2 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint1Leg2', vrep.simx_opmode_blocking)
        _, Ant_joint2Leg2 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint2Leg2', vrep.simx_opmode_blocking)
        _, Ant_joint3Leg2 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint3Leg2', vrep.simx_opmode_blocking)
        _, Ant_joint1Leg3 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint1Leg3', vrep.simx_opmode_blocking)
        _, Ant_joint2Leg3 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint2Leg3', vrep.simx_opmode_blocking)
        _, Ant_joint3Leg3 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint3Leg3', vrep.simx_opmode_blocking)
        _, Ant_joint1Leg4 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint1Leg4', vrep.simx_opmode_blocking)
        _, Ant_joint2Leg4 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint2Leg4', vrep.simx_opmode_blocking)
        _, Ant_joint3Leg4 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint3Leg4', vrep.simx_opmode_blocking)
        _, Ant_joint1Leg5 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint1Leg5', vrep.simx_opmode_blocking)
        _, Ant_joint2Leg5 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint2Leg5', vrep.simx_opmode_blocking)
        _, Ant_joint3Leg5 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint3Leg5', vrep.simx_opmode_blocking)
        _, Ant_joint1Leg6 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint1Leg6', vrep.simx_opmode_blocking)
        _, Ant_joint2Leg6 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint2Leg6', vrep.simx_opmode_blocking)
        _, Ant_joint3Leg6 = vrep.simxGetObjectHandle(self.client_id, 'Ant_joint3Leg6', vrep.simx_opmode_blocking)

        # Obtain body joint handles
        _, Ant_neckJoint1 = vrep.simxGetObjectHandle(self.client_id, 'Ant_neckJoint1', vrep.simx_opmode_blocking)
        _, Ant_neckJoint2 = vrep.simxGetObjectHandle(self.client_id, 'Ant_neckJoint2', vrep.simx_opmode_blocking)
        _, Ant_neckJoint3 = vrep.simxGetObjectHandle(self.client_id, 'Ant_neckJoint3', vrep.simx_opmode_blocking)
        _, Ant_leftJawJoint = vrep.simxGetObjectHandle(self.client_id, 'Ant_leftJawJoint', vrep.simx_opmode_blocking)
        _, Ant_rightJawJoint = vrep.simxGetObjectHandle(self.client_id, 'Ant_rightJawJoint', vrep.simx_opmode_blocking)

        # Order : [Ant_joint{1-3}Leg{1-6}, Ant_neckJoint{1-3}, Ant_leftJawJoint, Ant_rightJawJoint]
        self.handles = [Ant_joint1Leg1, Ant_joint2Leg1, Ant_joint3Leg1, Ant_joint1Leg2, Ant_joint2Leg2, Ant_joint3Leg2,
                        Ant_joint1Leg3, Ant_joint2Leg3, Ant_joint3Leg3, Ant_joint1Leg4, Ant_joint2Leg4, Ant_joint3Leg4,
                        Ant_joint1Leg5, Ant_joint2Leg5, Ant_joint3Leg5, Ant_joint1Leg6, Ant_joint2Leg6, Ant_joint3Leg6,
                        Ant_neckJoint1, Ant_neckJoint2, Ant_neckJoint3, Ant_leftJawJoint, Ant_rightJawJoint]

        self.joint_count = len(self.handles)

        # log these for consistency
        self.start_pos = self.get_position()
        self.start_orientation = self.get_orientation()

        '''
        # Configure them to have almost infinite target velocity
        # Use only if in pure Force/Torque mode without position control (PID)
        _ = vrep.simxPauseCommunication(self.client_id, True);
        for joint_handle in self.handles:
            _ = vrep.simxSetJointTargetVelocity(self.client_id, joint_handle, 9999.0, vrep.simx_opmode_blocking)
        _ = vrep.simxPauseCommunication(self.client_id, False);
        '''

    # force_vec = [Ant_joint{1-3}Leg{1-6}, Ant_neckJoint{1-3}, Ant_leftJawJoint, Ant_rightJawJoint]
    def set_forces(self, force_vec):
        _ = vrep.simxPauseCommunication(self.client_id, True);
        for handle_idx in range(0, self.joint_count):
            _ = vrep.simxSetJointForce(self.client_id, self.handles[handle_idx], force_vec[handle_idx], vrep.simx_opmode_blocking)
        _ = vrep.simxPauseCommunication(self.client_id, False);

    # set force_vec and trigger simulation step
    def set_forces_and_trigger(self, force_vec):
        self.set_forces(force_vec)
        _ = vrep.simxSynchronousTrigger(self.client_id);

    # Get joint positions
    def get_joint_pos(self):
        jpos = np.zeros(1,self.joint_count);
        for handle_idx in range(0, self.joint_count):
            _, jpos[handle_idx] = vrep.simxGetJointPosition(self.client_id, self.handles[handle_idx], vrep.simx_opmode_blocking)
        return jpos

    # returns euler orientation (alpha, beta, gamma) for the body
    def get_orientation(self):
        _, euler_angles = vrep.simxGetObjectOrientation(self.client_id, self.body_handle, vrep.simx_opmode_blocking)
        return np.asarray(euler_angles[0], euler_angles[1], euler_angles[2]).reshape((1, -1))

    # returns Cartesian coordinates (x,y,z) for the body
    def get_position(self):
        _, position = vrep.simxGetObjectPosition(self.client_id, self.body_handle, vrep.simx_opmode_blocking)
        return np.asarray(position[0], position[1], position[2]).reshape((1, -1))

    # set (x,y) position and rotation about z-axis
    def set_position_and_rotation(self, position, rotation):
        emptyBuff = bytearray()
        args = [position[0], position[1], self.start_pos[2], self.start_orientation[0], self.start_orientation[1], rotation]
        res,retInts,retFloats,retStrings,retBuffer=vrep.simxCallScriptFunction(client_id,'Ant',vrep.sim_scripttype_childscript,'resetScene',[], args,[],emptyBuff,vrep.simx_opmode_blocking)
        if res !=vrep.simx_return_ok:
            print('Failed') # TODO : log

    # Set custom dt for simulation
    def set_custom_dt(self, custom_dt):
        _ = vrep.simxSetFloatingParameter(self.client_id, vrep.sim_floatparam_simulation_time_step, custom_dt, vrep.simx_opmode_blocking)

    def start_simulation(self):
        # Start simulation
        e = vrep.simxStartSimulation(self.client_id, vrep.simx_opmode_blocking)
        assert e != -1, 'Failed to start simulation' # TODO : log

        # Print ping time
        sec, msec = vrep.simxGetPingTime(self.client_id)
        print "Started simulation on %s:%d" % (self.server_ip, self.server_port)
        print "Ping time: %f" % (sec + msec / 1000.0)

    def stop_simulation(self):
        vrep.simxStopSimulation(self.client_id, vrep.simx_opmode_blocking)
        # Just to make sure this gets executed
        vrep.simxGetPingTime(self.client_id)
