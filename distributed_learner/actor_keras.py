'''
Adapted from github.com/yanpanlau
'''

import numpy as np
import math
from keras.initializations import normal, identity
from keras.models import model_from_json
from keras.models import Sequential, Model
from keras.engine.training import collect_trainable_weights
from keras.layers import Dense, Flatten, Input, merge, Lambda
from keras.optimizers import Adam
import tensorflow as tf
import keras.backend as K

class ActorNetwork(object):
    def __init__(self, args):
        self.sess = args['sess']
        self.batch_size = args['batch_size']
        self.target_update_rate = args['target_update_rate']
        self.learning_rate = args['learning_rate']
        self.network_config = args['actor_network_config'] # hlayer_x_size, hlayer_x_type keys

        K.set_session(self.sess)

        #Now create the model
        state_size, action_size = args['state_size'], args['action_size']

        self.model , self.weights, self.state = self.create_actor_network(state_size, action_size)
        self.target_model, self.target_weights, self.target_state = self.create_actor_network(state_size, action_size)
        self.action_gradient = tf.placeholder(tf.float32,[None, action_size])
        self.params_grad = tf.gradients(self.model.output, self.weights, -self.action_gradient)
        grads = zip(self.params_grad, self.weights)
        self.optimize = tf.train.AdamOptimizer(learning_rate).apply_gradients(grads)
        self.sess.run(tf.initialize_all_variables())

    def train(self, states, action_grads):
        self.sess.run(self.optimize, feed_dict={
            self.state: states,
            self.action_gradient: action_grads
        })

    def target_train(self):
        actor_weights = self.model.get_weights()
        actor_target_weights = self.target_model.get_weights()
        for i in xrange(len(actor_weights)):
            actor_target_weights[i] = self.target_update_rate * actor_weights[i] + (1 - self.target_update_rate)* actor_target_weights[i]
        self.target_model.set_weights(actor_target_weights)

    def create_actor_network(self, state_size,action_dim):
        print("Building Actor Network")
        S = Input(shape=[state_size])
        # HIDDEN1_UNITS=100, relu
        h0 = Dense(self.network_config['hlayer_1_size'], activation=self.network_config['hlayer_1_type'])(S)
        # HIDDEN2_UNITS=200, relu
        h1 = Dense(self.network_config['hlayer_2_size'], activation=self.network_config['hlayer_2_type'])(h0)
        A = Dense(action_dim, activation = 'tanh', init= lambda shape, name: normal(shape, scale=1e-3, name=name))(h1)
        model = Model(input=S,output=A)
        return model, model.trainable_weights, S