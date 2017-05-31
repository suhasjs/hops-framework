import logging
import numpy as np
import time

from hexapod import Ant


def _normalize(theta):
    if theta > 0:
        return theta
    else:
        return theta + 2 * np.pi


class AntTurnEnv(object):
    def __init__(self, args):
        self.delta_theta = None
        # subprocess.Popen(
        #    [args['vrep_exec_path'], '-h', '-gREMOTEAPISERVERSERVICE_' + str(args['server_port']) + '_FALSE_TRUE',
        #     args['vrep_scene_file']])
        self.ant = Ant(args['server_ip'], args['server_port'])
        self.ant.init_client()
        self.per_step_reward = args['per_step_reward']
        self.final_reward = args['final_reward']
        self.tolerance = args['tolerance']
        self.server_ip, self.server_port = args['server_ip'], args['server_port']
        self.spawn_radius = args['spawn_radius']
        self.begin_pos = None
        self.goal = None

    def set_goal(self, delta_theta):
        self.delta_theta = delta_theta

    def start(self):
        logging.getLogger("learner").info("ENV::START:goal:%f" % self.delta_theta)
        state = np.hstack((self.ant.get_joint_pos(), self.ant.get_position(), self.ant.get_orientation()))
        begin_angle = self.ant.start_orientation[0, -1].item()
        self.begin_pos = self.ant.start_pos[0, 1:3]
        self.goal = begin_angle + self.delta_theta
        if self.goal > np.pi:
            self.goal -= 2 * np.pi
        elif self.goal < -np.pi:
            self.goal += 2 * np.pi
        return state, np.asarray(self.delta_theta).reshape((1, -1))

    def _is_terminal(self, current):
        diff = np.absolute(current - self.goal)
        if diff > np.pi:
            diff -= 2 * np.pi
        if diff < self.tolerance:
            return True
        else:
            return False

    def step(self, action):
        logging.getLogger("learner").info("stepping")
        self.ant.set_forces_and_trigger(action)
        new_state = np.hstack((self.ant.get_joint_pos(), self.ant.get_position(), self.ant.get_orientation()))
        net_displacement = new_state[0, -6:-4] - self.begin_pos
        new_goal = self.goal - new_state[0, -1].item()
        if new_goal > np.pi:
            new_goal -= 2 * np.pi
        new_goal = np.asarray(new_goal).reshape((1, -1))
        if self._is_terminal(new_state[0, -1].item()):
            disp_reward = -np.linalg.norm(net_displacement)
            return new_state, new_goal, (disp_reward + self.final_reward), True
        else:
            return new_state, new_goal, self.per_step_reward, False

    def reset(self):
        logging.getLogger("learner").info("ENV::RESET")
        self.ant.stop_simulation()
        time.sleep(0.5)
        self.ant.start_simulation()
        spawn_rad = np.random.uniform(-self.spawn_radius, +self.spawn_radius)
        angle = np.random.uniform(-np.pi, np.pi)
        self.ant.set_position_and_rotation(spawn_rad * np.asarray((np.cos(angle), np.sin(angle))),
                                           np.random.uniform(-np.pi, +np.pi))
        # NOTE : use this only if the stop_simulation() and set_position_and_rotation() doesn't cut it
        # self.ant.init_client()
