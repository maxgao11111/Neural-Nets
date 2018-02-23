import numpy as np

from layers import Kernel

from layers import ConvLayer
from layers import DeconvLayer
from layers import DenseLayer
from layers import SoftmaxLayer

from functions import QuadraticCost
from functions import NegativeLogLikelihood
from functions import LeakyRELU
from functions import Softmax

from random import shuffle
from copy import deepcopy

from convolutional import ConvolutionalNet

# Makes a 3D np array into a 1D np array
def flatten_image(image):
    if len(image.shape) > 1:
        l = np.array([])
        for x in image:
            l = np.concatenate((l, x.ravel()))

        image = l.ravel()
    return image

# Makes 1D np array into 3D np array
def convert_to_image(arr, image_shape):
    if len(arr.shape) == 2:
        return np.array([arr])
    elif len(arr.shape) < 2:
        image = np.zeros(image_shape)
        counter = 0

        for z in range(image_shape[0]):
            for y in range(image_shape[1]):
                for x in range(image_shape[2]):
                    image[z][y][x] = arr[counter]
                    counter+=1
        return image
    return arr

class Generator (ConvolutionalNet):
    # Args:
    #   input_shape (tuple) - the shape of the input (for images: (image depth, image height, image length))
    def __init__(self, input_shape, layers=None):
        self.input_shape = input_shape
        self.layer_types = []
        self.num_layers = 0
        self.layers = []
        if layers is not None:
            self.layers = layers

    # This function calculates the gradients for one training example
    # Args:
    #   network_input - (np arr) the input being used
    #   discriminator_network (object)
    def backprop(self, network_input, expected_output, discriminator_network):
        curr_z = network_input
        fzs_list = [network_input]
        dzs_list = [network_input]

        is_conv = False
        if self.layer_types[0] is "conv" or self.layer_types[0] is "deconv":
            is_conv = True

        for i, lt, lyr in zip(range(1, self.num_layers + 1), self.layer_types, self.layers):
            # Squash to 1D np array
            if lt is not "conv" and lt is not "deconv" and is_conv:
                is_conv = False
                curr_z = flatten_image(curr_z)

            curr_z = lyr.getactivations(curr_z)
            dzs_list.append(lyr.activation_function.func_deriv(deepcopy(curr_z)))

            curr_z = lyr.activation_function.func(curr_z)
            fzs_list.append(deepcopy(curr_z))

        delta = discriminator_network.getdeltas(deepcopy(curr_z), expected_output)

        is_conv = True
        if self.layer_types[-1] is not "conv" \
                and self.layer_types[-1] is not "deconv":
            is_conv = False

        delta_w = []
        delta_b = []

        # Append all the errors for each layer
        for lt, lyr, fzs, dzs in reversed(zip(self.layer_types, self.layers, fzs_list[:-1], dzs_list[:-1])):
            if lt is "conv" or lt is "deconv":
                if not is_conv:
                    delta = convert_to_image(delta, lyr.get_output_shape())
                    is_conv = True
            elif lt is "dense" or lt is "soft":
                fzs = flatten_image(fzs)
                dzs = flatten_image(dzs)
            dw, db, dlt = lyr.backprop(fzs, dzs, delta)
            delta_w.insert(0, dw)
            delta_b.insert(0, db)

            delta = dlt

        return np.array(delta_w), np.array(delta_b)

    # Updates the network given a specific minibatch (done by averaging gradients over the minibatch)
    # Args:
    #   mini_batch - a list of np arrays (inputs)
    #   step_size - the amount the network should change its parameter`s by relative to the gradients
    def update_network(self, mini_batch, step_size, discriminator_network):
        gradient_w, gradient_b = self.backprop(mini_batch[0][0], mini_batch[0][1], discriminator_network)

        for inp, outp in mini_batch[1:]:
            dgw, dgb = self.backprop(inp, outp, discriminator_network)
            gradient_w += dgw
            gradient_b += dgb

        # Average the gradients
        gradient_w *= step_size/(len(mini_batch)+0.00)
        gradient_b *= step_size/(len(mini_batch)+0.00)

        # Update weights and biases in opposite direction of gradients
        for gw, gb, lyr in zip(gradient_w, gradient_b, self.layers):
            lyr.update(-gw, -gb)

    # Evaluates the average cost across the training set
    def evaluate_cost(self, training_set, discriminator_network):
        total = 0.0
        for inp, outp in training_set:
            net_outp = self.feedforward(inp)
            total += discriminator_network.cost_function.cost(discriminator_network.feedforward(net_outp), outp)

        return total/len(training_set)

    # Performs SGD on the network
    # Args:
    #   epochs - (int), number of times to loop over the entire batch
    #   step_size - (float), amount network should change its parameters per update
    #   mini_batch_size - (int), number of training examples per mini batch
    #   training_inputs - (list), the list of training inputs
    #   expected_outputs - (list), the list of expected outputs for each input
    def stochastic_gradient_descent(self, epochs, step_size, mini_batch_size, training_set, discriminator_network):
        # Train
        for ep in range(epochs):
            shuffle(training_set)
            for x in range(0, len(training_set), mini_batch_size):
                self.update_network(training_set[x:x+mini_batch_size], step_size, discriminator_network)
            # Update with progress
            print("Generator Epoch: %d   Average cost: %f" % (ep+1, self.evaluate_cost(training_set, discriminator_network)))