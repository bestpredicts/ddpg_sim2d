import datetime
import logging
import pickle
import random
import threading
from collections import deque

import numpy as np
import torch

logger = logging.getLogger(__name__)


class MemoryDeque():
    '''
    Code based on:
    https://github.com/openai/baselines/blob/master/baselines/deepq/replay_buffer.py
    Expects tuples of (state, next_state, action, reward, done)
    '''

    def __init__(self, max_size=50000):
        self.storage = []
        self.max_size = max_size
        self.ptr = 0

    def store(self, data):
        if len(self.storage) == self.max_size:
            self.storage[int(self.ptr)] = data
            self.ptr = (self.ptr + 1) % self.max_size
        else:
            self.storage.append(data)

    def sample(self, batch_size):
        ind = np.random.randint(0, len(self.storage), size=batch_size)
        x, y, u, r, d = [], [], [], [], []

        for i in ind:
            X, U, R, Y, D = self.storage[i]
            x.append(np.array(X, copy=False))
            y.append(np.array(Y, copy=False))
            u.append(np.array(U, copy=False))
            r.append(np.array(R, copy=False))
            d.append(np.array(D, copy=False))

        return np.array(x), np.array(y), np.array(u), np.array(r), np.array(d)

    def __len__(self):
        return len(self.storage)


class OUNoise(object):
    def __init__(self, action_space, mu=0.0,
                 theta=0.15, max_sigma=0.3,
                 min_sigma=0.3, decay_period=100000):
        self.mu = mu
        self.theta = theta
        self.sigma = max_sigma
        self.max_sigma = max_sigma
        self.min_sigma = min_sigma
        self.decay_period = decay_period
        self.action_dim = action_space.n
        self.low = 0
        self.high = action_space.n
        self.reset()

    def reset(self):
        self.state = np.ones(self.action_dim) * self.mu

    def evolve_state(self):
        x = self.state
        dx = self.theta * (self.mu - x) + self.sigma * \
            np.random.randn(self.action_dim)
        self.state = x + dx
        return self.state

    def get_action(self, action, t=0):
        ou_state = self.evolve_state()
        self.sigma = self.max_sigma - \
            (self.max_sigma - self.min_sigma) * min(1.0, t / self.decay_period)
        return np.clip(action + ou_state, self.low, self.high)


class AsyncWrite(threading.Thread):

    def __init__(self, obj, path, msg):

        # calling superclass init
        threading.Thread.__init__(self)
        self.obj = obj
        self.path = path
        self.msg = msg

    def run(self):
        with open(self.path, 'wb') as fiile:
            pickle.dump(self.obj, fiile)
        fiile.close()
        self.obj = None
        print(self.msg)


class AsyncModelWrite(threading.Thread):

    def __init__(self, obj, paths, msg):
        # calling superclass init
        threading.Thread.__init__(self)
        self.obj = obj
        self.paths = paths
        self.msg = msg

    def run(self):
        torch.save(self.obj.actor.state_dict(), self.paths[0])
        torch.save(self.obj.critic.state_dict(), self.paths[1])
        torch.save(self.obj.actor_optimizer.state_dict(), self.paths[2])
        torch.save(self.obj.critic_optimizer.state_dict(), self.paths[3])
        print(self.msg)


def gen_mem_end(gen_mem, episode, model, frame_idx):
    gen_mem = False
    frame_idx = 0
    model.learn_start = 0
    logging.info('Start Learning at Episode %s', episode)


def episode_end(total_reward, episode, model):
    # Get the total reward of the episode
    logging.info('Episode %s reward %d', episode, total_reward)
    model.finish_nstep()
    model.reset_hx()


def save_modelmem(episode, test, model, model_path,
                  optim_path, mem_path, frame_idx, replay_size):
    if episode % 100 == 0 and episode > 0 and not test:
        model.save_w(path_model=model_path,
                     path_optim=optim_path)
    if ((frame_idx / 16) % replay_size) == 0 and episode % 1000 == 0:
        model.save_replay(mem_path=mem_path)
        logging.info("Memory Saved")


def save_rewards(rewards):
    day = datetime.datetime.now().today().day()
    hour = datetime.datetime.now().hour()
    minute = datetime.datetime.now().minute()
    final_str = str(day) + "-" + str(hour) + "-" + str(minute)
    with open('saved_agents/rewards_{}.pickle'.format(final_str),
              'w+') as fiile:
        pickle.dump(rewards, fiile)
        fiile.close()
