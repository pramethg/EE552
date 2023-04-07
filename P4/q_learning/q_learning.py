import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import math
import random

import gym
from maze.util import *

import numpy as np
import matplotlib.pyplot as plt

def plot_moving_average_with_std(data, window_size, alpha=0.3, data_name='Reward', file_save=None):
    """
    Plots the moving average of the data with a standard deviation shaded area.
    
    Args:  
        data: 1D numpy array of data points
        window_size: integer size of the moving average window
        alpha: transparency of the shaded area
        data_name: name of the data to be used in the plot legend
        file_save: path to save the plot to. If None, the plot is not saved.
    """
    moving_average = np.convolve(data, np.ones(window_size), mode='valid') / window_size
    moving_std = np.array([np.std(data[i:i+window_size]) for i in range(len(data) - window_size + 1)])

    # Define the upper and lower bounds for the shaded area
    upper_bound = moving_average + moving_std
    lower_bound = moving_average - moving_std

    x_values = np.arange(window_size - 1, len(data))
    plt.plot(x_values, moving_average, label='Moving Average', color='blue')
    plt.fill_between(x_values, lower_bound, upper_bound, color='blue', alpha=alpha, label='Moving Std Deviation')
    plt.title(f'{data_name} Moving Average')
    plt.xlabel('Episode')
    plt.ylabel(data_name)
    if file_save is not None:
        plt.savefig(file_save)
    else:
        plt.show()
    plt.close()


def simulate(env):
    # Instantiating the learning related parameters
    learning_rate = get_learning_rate(0)
    explore_rate = get_explore_rate(0)
    discount_factor = 0.99

    num_streaks = 0

    # Render tha maze
    env.render()

    ep_rewards = []
    ep_steps = []

    for episode in range(NUM_EPISODES):

        # Reset the environment
        obv = env.reset()

        # the initial state
        state_0 = state_to_bucket(obv)
        total_reward = 0

        for t in range(MAX_T):
            # Select an action
            action = select_action(state_0, explore_rate)

            # execute the action
            obv, reward, done, _ = env.step(action)

            # Observe the result
            state = state_to_bucket(obv)
            total_reward += reward

            # Update the Q based on the result
            best_q = np.amax(q_table[state])
            q_table[state_0 + (action,)] += learning_rate * (reward + discount_factor * (best_q) - q_table[state_0 + (action,)])

            # Setting up for the next iteration
            state_0 = state

            # Print data
            if DEBUG_MODE == 2:
                print("\nEpisode = %d" % episode)
                print("t = %d" % t)
                print("Action: %d" % action)
                print("State: %s" % str(state))
                print("Reward: %f" % reward)
                print("Best Q: %f" % best_q)
                print("Explore rate: %f" % explore_rate)
                print("Learning rate: %f" % learning_rate)
                print("Streaks: %d" % num_streaks)
                print("")

            elif DEBUG_MODE == 1:
                if done or t >= MAX_T - 1:
                    print("\nEpisode = %d" % episode)
                    print("t = %d" % t)
                    print("Explore rate: %f" % explore_rate)
                    print("Learning rate: %f" % learning_rate)
                    print("Streaks: %d" % num_streaks)
                    print("Total reward: %f" % total_reward)
                    print("")

            # Render tha maze
            if RENDER_MAZE:
                env.render()

            #if env.is_game_over():
            #   sys.exit()

            if done:
                print("Episode %d finished after %f time steps with total reward = %f (streak %d)."
                      % (episode, t, total_reward, num_streaks))

                if t <= SOLVED_T:
                    num_streaks += 1
                else:
                    num_streaks = 0
                break

            elif t >= MAX_T - 1:
                print("Episode %d timed out at %d with total reward = %f."
                      % (episode, t, total_reward))

        # It's considered done when it's solved over 120 times consecutively
        if num_streaks > STREAK_TO_END:
            break

        # Update parameters
        explore_rate = get_explore_rate(episode)
        learning_rate = get_learning_rate(episode)
        ep_rewards.append(total_reward)
        ep_steps.append(t)

    print('Game over!')

    # Plot the reward and steps
    ep_rewards = np.array(ep_rewards)
    file_name = f'q_learning_{ENV_NAME}_rewards.png'
    plot_moving_average_with_std(ep_rewards, window_size=AVG_N, data_name='Reward', file_save=file_name)

    ep_steps = np.array(ep_steps)
    file_name = f'q_learning_{ENV_NAME}_steps.png'
    plot_moving_average_with_std(ep_steps, window_size=AVG_N, data_name='Steps', file_save=file_name)
    env.close()



def select_action(state, explore_rate):
    # Select a random action
    if random.random() < explore_rate:
        action = env.action_space.sample()
    # Select the action with the highest q
    else:
        action = int(np.argmax(q_table[state]))
    return action


def get_explore_rate(t):
    return max(MIN_EXPLORE_RATE, min(0.8, 1.0 - math.log10((t+1)/DECAY_FACTOR)))


def get_learning_rate(t):
    return max(MIN_LEARNING_RATE, min(0.8, 1.0 - math.log10((t+1)/DECAY_FACTOR)))


def state_to_bucket(state):
    bucket_indice = []
    for i in range(len(state)):
        if state[i] <= STATE_BOUNDS[i][0]:
            bucket_index = 0
        elif state[i] >= STATE_BOUNDS[i][1]:
            bucket_index = NUM_BUCKETS[i] - 1
        else:
            # Mapping the state bounds to the bucket array
            bound_width = STATE_BOUNDS[i][1] - STATE_BOUNDS[i][0]
            offset = (NUM_BUCKETS[i]-1)*STATE_BOUNDS[i][0]/bound_width
            scaling = (NUM_BUCKETS[i]-1)/bound_width
            bucket_index = int(round(scaling*state[i] - offset))
        bucket_indice.append(bucket_index)
    return tuple(bucket_indice)


if __name__ == "__main__":

    # Get the configuration parameters
    cfg = CFG('config.cfg')

    # Initialize the "maze" environment
    env = gym.make(cfg.ENV_NAME)

    '''
    Defining the environment related constants
    '''
    # Number of discrete states (bucket) per state dimension
    MAZE_SIZE = tuple((env.observation_space.high + np.ones(env.observation_space.shape)).astype(int))
    NUM_BUCKETS = MAZE_SIZE  # one bucket per grid

    # Number of discrete actions
    NUM_ACTIONS = env.action_space.n  # ["N", "S", "E", "W"]
    # Bounds for each discrete state
    STATE_BOUNDS = list(zip(env.observation_space.low, env.observation_space.high))

    '''
    Learning related constants
    '''
    MIN_EXPLORE_RATE = cfg.MIN_EXPLORE_RATE
    MIN_LEARNING_RATE = cfg.MIN_LEARNING_RATE
    DECAY_FACTOR = np.prod(MAZE_SIZE, dtype=float) / 10.0

    '''
    Defining the simulation related constants
    '''
    NUM_EPISODES = cfg.NUM_EPISODES
    MAX_T = np.prod(MAZE_SIZE, dtype=int) * 100
    STREAK_TO_END = cfg.STREAK_TO_END
    SOLVED_T = np.prod(MAZE_SIZE, dtype=int)
    DEBUG_MODE = cfg.DEBUG_MODE
    RENDER_MAZE = cfg.RENDER_MAZE
    ENABLE_RECORDING = cfg.ENABLE_RECORDING

    '''
    Define plotting related constants
    '''
    ENV_NAME = cfg.ENV_NAME
    AVG_N = cfg.AVG_N

    '''
    Creating a Q-Table for each state-action pair
    '''
    q_table = np.zeros(NUM_BUCKETS + (NUM_ACTIONS,), dtype=float)

    '''
    Begin simulation
    '''

    if ENABLE_RECORDING:
        if not os.path.exists(cfg.RECORDING_FOLDER):
            os.makedirs(cfg.RECORDING_FOLDER)
        #env = RecordEveryNEpisodes(env, cfg.RECORDING_FOLDER, video_length=200, n=cfg.RECORDING_RATE)
        wrapped_env = gym.wrappers.RecordVideo(env, cfg.RECORDING_FOLDER, episode_trigger = lambda x: x % cfg.RECORDING_RATE == 0)
        wrapped_env.reset()
        simulate(wrapped_env)
    else:
        simulate(env)
