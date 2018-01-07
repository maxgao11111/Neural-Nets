import numpy as np
import functions as fn

# Convolution Pooling layer
class ConvPoolLayer:
    # Args:
    #   image_shape: a 3-tuple (num_images, image_height, image_length)
    #   filter_shape: a 4-tuple (num_filters, filter_depth, filter_height, filter_length)
    #   pool_shape: a 2-tuple (pool_height, pool_length)
    def __init__(self, image_shape, filter_shape, pool_shape, pooling_method="max", logistic_func="sig", filters=None):
        self.image_shape = image_shape
        self.filter_shape = filter_shape
        self.output_shape = (filter_shape[0], image_shape[1]-filter_shape[1]+1, image_shape[2]-filter_shape[2]+1)
        self.pooling_method = pooling_method
        self.pool_shape = pool_shape

        if logistic_func == "sig":
            self.logistic_func = fn.Sigmoid
        elif logistic_func == "relu":
            self.logistic_func = fn.ReLU
        elif logistic_func == "leakyrelu":
            self.logistic_func = fn.LeakyReLU
        elif logistic_func == "tanh":
            self.logistic_func = fn.TanH

        # Create list of filter objects
        if filters is not None:
            self.filters = filters
        else:
            self.filters = []
            for i in range(filter_shape[0]):
                self.filters.append(Filter(self.filter_shape[1:]))

    # Forwards past a list of images and returns the new list of images
    def feed_forward (self, image_list):
        new_image_list = []
        for i in range(self.filter_shape[0]):
            fil = self.filters[i]
            feature_image = fil.use_filter(self.image_shape, image_list)

            # Max pooling
            if self.pooling_method == "max":
                feature_image = MaxPool.pool(feature_image, self.pool_shape)

            new_image_list.append(feature_image)
        return self.logistic_func(new_image_list)

    def get_num_filters(self):
        return self.filter_shape[0]

    def get_filter(self, index):
        return self.filters[index]

    def get_all_filters(self):
        return self.filters

    def get_output_shape(self):
        return self.output_shape

    def set_filter(self, index, filtr):
        self.filters[index] = filtr

    def set_all_filters(self, filters):
        self.filters = filters

# Individual filter objects
class Filter:
    # Args:
    #   filter_size: a 3-tuple (filter_depth, filter_height, filter_length)
    def __init__(self, filter_size, weights=None, bias=None):
        self.filter_size = filter_size
        self.feature_map_length = filter_size[2]
        self.feature_map_height = filter_size[1]
        self.num_feature_maps = filter_size[0]
        if weights is not None:
            self.weights = weights
        else:
            self.weights = [np.random.randn(self.feature_map_height, self.feature_map_length) for f in range(self.num_feature_maps)]

        if bias is not None:
            self.bias = bias
        else:
            self.bias = np.random.random()

    # Takes in a list of images and applies the filter specific to the object to the filter, returning the new 2D image
    # Args:
    #   image_shape: a 3-tuple (num_images, image_height, image_length)
    #   image_list: a list of 2D images
    def use_filter (self, image_shape, image_list):
        num_images = image_shape[0]
        new_image_size = (image_shape[1] - self.feature_map_height + 1, image_shape[2] - self.feature_map_length + 1)
        new_image = np.zeros(new_image_size)
        for i in range(num_images):
            new_image += self.use_feature_map(self.weights[i], new_image_size, image_list[i])
        for y in range(new_image_size[0]):
            for x in range(new_image_size[1]):
                new_image[y][x] = new_image[y][x]+ self.bias
        return new_image


    # This method takes in a feature map and slides it across an image
    # Returns:
    #   a 2D array which is the new output image
    def use_feature_map (self, feature_map, new_image_size, image):
        new_image = np.zeros(new_image_size)
        for x in range(new_image_size[1]):
            for y in range(new_image_size[0]):
                img_piece = image[y:y+self.feature_map_height,x:x+self.feature_map_length]
                new_image[y][x] = np.dot(feature_map.ravel(), img_piece.ravel())
        return new_image

    def get_filter_size(self):
        return self.filter_size

    def get_weights(self):
        return self.weights

    def get_bias(self):
        return self.bias

    def set_weights(self, weights):
        self.weights = weights

    def set_bias(self, bias):
        self.bias = bias

class MaxPool:
    # This method performs max pooling on an image and returns the new, max-pooled image
    # Args:
    #   image (np array) - a 2d image
    #   pool_shape (tuple) - a 2-tuple (pool_length, pool_height)
    @staticmethod
    def pool (image, pool_shape):
        image_length = len(image)
        image_height = len(image[0])

        pool_length = pool_shape[1]
        pool_height = pool_shape[0]

        new_image = np.zeros((image_height/pool_height, image_length/pool_length))
        for ny, iy in enumerate(range(0, image_height, pool_height)):
            for nx, ix in enumerate(range(0, image_length, pool_length)):
                new_image[ny][nx] = np.argmax(image[iy:iy+pool_height][ix:ix+pool_length])
        return new_image