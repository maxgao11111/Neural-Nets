import numpy as np

from layers import Kernel

from layers import ConvLayer
from layers import DeconvLayer
from layers import DenseLayer
from layers import SoftmaxLayer

from functions import QuadraticCost
from functions import NegativeLogLikelihood

from neural_network import NeuralNetwork

from random import shuffle
from copy import deepcopy

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

class ConvolutionalNet(NeuralNetwork):
    # Args:
    #   input_shape (tuple) - the shape of the input (for images: (image depth, image height, image length))
    def __init__(self, input_shape, layers=None, cost_function=QuadraticCost):
        super(ConvolutionalNet,self).__init__("convolutional", cost_function, layers)
        self.input_shape = input_shape
        self.layer_types=[]

    # Adds a new layer to the network
    # Args:
    #   layer_type (string) - the type of layer to be added (conv, deconv, dense, soft)
    #   output_size (tuple/int) optional - the shape of the output for that layer
    #                   conv (None)
    #                   deconv (2 tuple): (output height, output length)
    #                   dense and softmax (int): num of neurons on the layer
    #   kernel_size (2-tuple) optional - for conv and deconv layers, (num kernels, kernel height, kernel length)
    def add(self, layer_type, output_size=None, kernel_size=None):
        # If there are no layers, make the first one
        input_shape = self.input_shape
        is_first_layer = True

        # Use last layer as input shape for new layer if there exists a previous layer
        if not len(self.layers) == 0:
            input_shape = self.layers[-1].get_output_shape()
            is_first_layer = False

        if layer_type is "conv" or layer_type is "deconv":
            # Order kernel shape (num kernels, kernel depth, kernel height, kernel length)
            kernel_shape = (kernel_size[0], input_shape[0], kernel_size[1], kernel_size[2])

            if layer_type is "conv":
                self.layers.append(ConvLayer(input_shape=input_shape,
                                             kernel_shape=kernel_shape))
            elif layer_type is "deconv":
                # Order output shape (image depth, image height, image length)
                output_shape = (kernel_size[0], output_size[0], output_size[1])
                self.layers.append(DeconvLayer(input_shape=input_shape,
                                               output_shape=output_shape,
                                               kernel_shape=kernel_shape))
        elif layer_type is "dense" or layer_type is "soft":
            # Assume last layer was softmax or dense
            num_prev_neurons = input_shape
            # If it is a deconv or conv, calculate number of previous neurons
            if not is_first_layer:
                if self.layer_types[-1] is "conv" or self.layer_types[-1] is "deconv":
                    num_prev_neurons = input_shape[0]*input_shape[1]*input_shape[2]

            if layer_type is "dense":
                self.layers.append(DenseLayer(input_shape=num_prev_neurons,
                                              output_shape=output_size))
            elif layer_type is "soft":
                self.layers.append(SoftmaxLayer(input_shape=num_prev_neurons,
                                                output_shape=output_size))

        self.num_layers += 1
        self.layer_types.append(layer_type)

        # Change cost function based on last layer to optimize training
        if isinstance(self.layers[-1], SoftmaxLayer):
            self.cost_function=NegativeLogLikelihood
        else:
            self.cost_function=QuadraticCost

    # Returns the next activation without squashing it
    # Args:
    #   z_activations - (np arr) the current activations
    #   layer - the next layer to be used
    def next_activation(self, z_activations, layer):
        return layer.getactivations(z_activations)

    # Feeds an input through the network, returning the output
    # Args: network_input - (np arr) the input
    def feedforward(self, network_input):
        is_conv = False
        if self.layer_types[0] == "conv" or self.layer_types[0] == "deconv":
            is_conv = True
            if len(network_input.shape) == 2:
                network_input = np.array([network_input])


        for lt, lyr in zip(self.layer_types, self.layers):
            # Squash to 1D np array
            if lt is not "conv" and lt is not "deconv" and is_conv:
                is_conv = False
                network_input = flatten_image(network_input)

            network_input = lyr.feedforward(network_input)

        return network_input

    # This function calculates the gradients for one training example
    # Args:
    #   network_input - (np arr) the input being used
    #   expected_output - (np arr) the expected output
    def backprop(self, network_input, expected_output):
        curr_z = network_input
        fzs_list = [network_input]
        dzs_list = [network_input]

        is_conv = False
        if self.layer_types[0] is "conv" or self.layer_types[0] is "deconv":
            is_conv = True

        for i, lt, lyr in zip(range(1, self.num_layers+1), self.layer_types, self.layers):
            # Squash to 1D np array
            if lt is not "conv" and lt is not "deconv" and is_conv:
                is_conv = False
                curr_z = flatten_image(curr_z)

            curr_z = lyr.getactivations(curr_z)
            dzs_list.append(lyr.activation_function.func_deriv(deepcopy(curr_z)))

            curr_z = lyr.activation_function.func(curr_z)
            fzs_list.append(deepcopy(curr_z))

        # Errors for the last layer
        delta = self.cost_function.delta(fzs_list[-1],
                                         dzs_list[-1],
                                         expected_output)

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

    def reset_velocity(self):
        self.velocity = None

    # Updates the network given a specific minibatch (done by averaging gradients over the minibatch)
    # Args:
    #   mini_batch - a list of tuples, (input, expected output)
    #   step_size - the amount the network should change its parameters by relative to the gradients
    def update_network(self, step_size, mini_batch, is_momentum_based, friction):
        gradient_w, gradient_b = self.backprop(mini_batch[0][0], mini_batch[0][1])

        for inp, outp in mini_batch[1:]:
            dgw, dgb = self.backprop(inp, outp)
            gradient_w += dgw
            gradient_b += dgb

        # Average the gradients
        gradient_w *= step_size/(len(mini_batch)+0.00)
        gradient_b *= step_size/(len(mini_batch)+0.00)

        if self.velocity is None:
            self.velocity = np.array([gradient_w, gradient_b])
        else:
            self.velocity *= friction
            self.velocity += np.array([gradient_w, gradient_b])

        # Update weights and biases in opposite direction of gradients
        if is_momentum_based:
            for gw, gb, lyr in zip(gradient_w, gradient_b, self.layers):
                lyr.update(-gw, -gb)
        else:
            for gw, gb, lyr in zip(self.velocity[0], self.velocity[1], self.layers):
                lyr.update(-gw, -gb)

    # Performs SGD on the network
    # Args:
    #   epochs - (int), number of times to loop over the entire batch
    #   step_size - (float), amount network should change its parameters per update
    #   mini_batch_size - (int), number of training examples per mini batch
    #   training_inputs - (list), the list of training inputs
    #   expected_outputs - (list), the list of expected outputs for each input
    def stochastic_gradient_descent(self, epochs, step_size, mini_batch_size, training_inputs, expected_outputs,
                                    is_momentum_based=False, friction=0.9):
        training_set = []
        for inp, outp in zip(training_inputs, expected_outputs):
            training_set.append((inp, outp))

        # Train
        for ep in range(epochs):
            shuffle(training_set)
            for x in range(0, len(training_set), mini_batch_size):
                self.update_network(step_size=step_size,
                                    mini_batch=training_set[x:x+mini_batch_size],
                                    is_momentum_based=is_momentum_based,
                                    friction=friction)
            # # Update with progress
            # print("Epoch: %d   Average cost: %f" % (ep+1, self.evaluate_cost(training_set)))
            # print "kernel0"
            # print self.layers[0].kernels[0].weights[0]
            # print "softweights0"
            # print self.layers[5].weights[0]

        self.reset_velocity()

