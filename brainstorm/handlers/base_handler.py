#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from brainstorm.describable import Describable
import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Handler(Describable):
    """Abstract Base Class for all handlers.

    This base is used mainly to ensure a common interface and provide
    documentation for derived handlers. When implementing new methods
    one should adhere to the naming scheme. Most mathematical operations should
    have a suffix or suffixes indicating the shapes of inputs it expects:

    `s` for scalar,
    `v` for vector (a 2D array with at least dimension equal to 1),
    `m` for matrix  (a 2D array),
    `t` for tensor (which means arbitrary shape, synonym for `array`).

    Note that these shapes are not checked by each handler itself. However,
    the DebugHandler can be used to perform these checks to ensure that
    operations are not abused.

    Attributes:
      dtype: Data type that this handler works with.
      context: Context which may be used by this handler for operation.
      EMPTY: An empty array matching this handler's type.
      rnd: A random state maintained by this handler.
      array_type: The type of array object that this handler works with.
    """

    # ------------------------- Allocate new memory ------------------------- #

    @abc.abstractmethod
    def allocate(self, shape):
        """Allocate new memory with given shape but arbitrary content.

        Args:
            shape (tuple[int]): Shape of the array.

        Returns:
            object: New array with given shape.
        """

    @abc.abstractmethod
    def ones(self, shape):
        """Allocate new memory with given shape and filled with ones.

        Args:
            shape (tuple[int]): Shape of the array.

        Returns:
            object: New array with given shape filled with ones.
        """

    @abc.abstractmethod
    def zeros(self, shape):
        """Allocate new memory with given shape and filled with zeros.

        Args:
            shape (tuple[int]): Shape of the array.

        Returns:
            object: New array with given shape filled with zeros.
        """

    # ---------------------------- Copy and Fill ---------------------------- #

    @abc.abstractmethod
    def copy_to(self, dest, src):
        """Copy the contents of one array to another.

        Both source and destination arrays must be of this handler's supported
        type and have the same shape.

        Args:
            dest (array_type): Destination array.
            src (array_type): Source array.
        Returns:
            None
        """

    @abc.abstractmethod
    def create_from_numpy(self, arr):
        """Create a new array with the same entries as a Numpy array.

        Args:
            arr (numpy.ndarray): Numpy array whose elements should be used
                                 to fill the new array.
        Returns:
            array_type: New array with same shape and entries as the given
                        Numpy array.
        """

    @abc.abstractmethod
    def fill(self, mem, val):
        """Fill an array with a given value.

        Args:
            mem (array_type): Array to be filled.
            val (dtype): Value to fill.
        Returns:
            None
        """

    @abc.abstractmethod
    def get_numpy_copy(self, mem):
        """Return a copy of the given data as a numpy array.

        Args:
            mem (array_type): Source array to be copied.

        Returns:
            numpy.ndarray: Numpy array with same content as mem.
        """

    @abc.abstractmethod
    def set_from_numpy(self, mem, arr):
        """Set the content of an array from a given numpy array.

        Args:
            mem (array_type): Destination array that should be set.
            arr (numpy.ndarray): Source numpy array.
        Returns:
            None
        """

    # ---------------------------- Debug helpers ---------------------------- #

    @abc.abstractmethod
    def is_fully_finite(self, a):
        """Check if all entries of the array are finite (no nans or infs).

        Args:
            a (array_type): Input array to check.
        Returns:
            bool: True if there are no infs or nans, False otherwise.
        """

    # ----------------------- Mathematical operations ----------------------- #

    @abc.abstractmethod
    def add_mv(self, m, v, out):
        """Add a matrix to a vector with broadcasting.

        Add an (M, N) matrix to a (1, N) or (M, 1) vector using
        broadcasting such that the output is (M, N).

        Args:
            m (array_type): The first array to be added. Must be 2D.
            v (array_type): The second array to be added. Must be 2D with at
                            least one dimension of size 1 and the other
                            dimension matching the corresponding size of
                            :attr:`m`.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`m`.
        Returns:
            None
        """

    @abc.abstractmethod
    def add_st(self, s, t, out):
        """Add a scalar to each element of a tensor.

        Args:
            s (dtype): The scalar value to be added.
            t (array_type): The array to be added.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`t`.
        Returns:
            None
        """

    @abc.abstractmethod
    def add_tt(self, a, b, out):
        """Add two tensors element-wise,

        Args:
            a (array_type): First array.
            b (array_type): Second array.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`a` and :attr:`b`.
        Returns:
            None
        """

    @abc.abstractmethod
    def avgpool2d_backward_batch(self, inputs, window, outputs, padding,
                                 stride, in_deltas, out_deltas):
        """Computes the gradients for 2D average-pooling on a batch of images.

        Args:
            inputs (array_type):
            window (tuple[int]):
            outputs (array_type):
            padding (int):
            stride (tuple[int]):
            in_deltas (array_type):
            out_deltas (array_type):
        Returns:
            None
        """

    @abc.abstractmethod
    def avgpool2d_forward_batch(self, inputs, window, outputs, padding,
                                stride):
        """Performs 2D average-pooling on a batch of images.

        Args:
            inputs (array_type):
            window (tuple[int]):
            outputs (array_type):
            padding (int):
            stride (tuple[int]):
            argmax (array_type):
        Returns:
            None
        """

    @abc.abstractmethod
    def binarize_v(self, v, out):
        """Convert a column vector into a matrix of one-hot row vectors.

        Usually used to convert class IDs into one-hot vectors. Therefore,
        `out[i, j] = 1`, if j equals v[i, 0]
        `out[i, j] = 0`, otherwise.

        Note that `out` must have enough columns such that all indices in
        :attr:`v` are valid.

        Args:
            v (array_type): Column vector (2D array with a single column).
            out (array_type): Matrix (2D array) into which the output is
                              placed. The number of rows must be the same as
                              :attr:`v` and number of columns must be greater
                              than the maximum value in :attr:`v`.
        Returns:
            None
        """

    @abc.abstractmethod
    def broadcast_features_t(self, a, out):
        """Broadcast the right-most dimension of an array by copying elements.

        This function provides a numpy-broadcast-like operation for the
        right-most dimension of an array. E.g. an array with shape (2, 3, 4, 1)
        may be broadcasted to shape (2, 3, 4, 5), by copying all the elements
        5 times.

        Note:
            This function supports more general cases, such as broadcasting
            an array of shape (2, 3, 1) to shape (2, 3, 1, 3, 2). However,
            currently it is assumed that this function will be used with
            both :attr:`a` and :attr:`out` having the same number of dimensions.

        Args:
            a (array_type): Array whose elements should be broadcasted. Must
                            be at least 3D and the rightmost dimension must
                            be of size 1.
            out (array_type): Array into which the output is placed. Must be at
                              at least 3D and have same the number of
                              dimensions as :attr:`a`. Only the right-most
                              dimension can be different from :attr:`a`.
        Returns:
            None
        """

    @abc.abstractmethod
    def clip_t(self, a, a_min, a_max, out):
        """Clip (limit) the values in an array.

        Given an interval, values outside the interval are clipped to the
        interval edges. For example, if an interval of [0, 1] is specified,
        values smaller than 0 become 0, and values larger than 1 become 1.

        Args:
            a (array_type): Array containing the elements to clip.
            a_min (dtype): Minimum value.
            a_max (dtype): Maximum value.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`a`.
        Returns:
            None
        """

    @abc.abstractmethod
    def conv2d_backward_batch(self, inputs, weights, padding, stride,
                              in_deltas, out_deltas, weight_deltas,
                              bias_deltas):
        """Computes the gradients for a 2D convolution on a batch of images.

        Args:
            inputs (array_type):
            weights (array_type):
            padding (int):
            stride (tuple[int]):
            in_deltas (array_type):
            out_deltas (array_type):
            weight_deltas (array_type):
            bias_deltas (array_type):
        Returns:
            None
        """

    @abc.abstractmethod
    def conv2d_forward_batch(self, inputs, weights, bias, outputs,
                             padding, stride):
        """Performs a 2D convolution on a batch of images.

        Args:
            inputs (array_type):
            weights (array_type):
            bias (array_type):
            outputs (array_type):
            padding (int):
            stride (tuple[int]):
        Returns:
            None
        """

    @abc.abstractmethod
    def dot_add_mm(self, a, b, out, transa=False, transb=False):
        """Multiply two matrices and add to a matrix.

        Only 2D arrays (matrices) are supported.

        Args:
            a (array_type): First matrix.
            b (array_type): Second matrix. Must have compatible shape to be
                            right-multiplied with :attr:`a`.
            out (array_type): Array into which the output is added. Must
                              have correct shape for the product of the two
                              matrices.
        Returns:
            None
        """

    @abc.abstractmethod
    def dot_mm(self, a, b, out, transa=False, transb=False):
        """Multiply two matrices.

        Only 2D arrays (matrices) are supported.

        Args:
            a (array_type): First matrix.
            b (array_type): Second matrix. Must have compatible shape to be
                            right-multiplied with :attr:`a`.
            out (array_type): Array into which the output is placed. Must
                              have correct shape for the product of the two
                              matrices.
        Returns:
            None
        """

    @abc.abstractmethod
    def divide_mv(self, m, v, out):
        """Divide a matrix by a vector.

        Divide a (M, N) matrix element-wise by a (1, N) vector using
        broadcasting such that the output is (M, N).

        Args:
            a (array_type): First array (dividend). Must be 2D.
            b (array_type): Second array (divisor). Must be 2D with at
                            least one dimension of size 1 and second
                            dimension matching the corresponding size of
                            :attr:`m`.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`m`.
        Returns:
            None
        """

    @abc.abstractmethod
    def divide_tt(self, a, b, out):
        """Divide two tensors element-wise.

        Args:
            a (array_type): First array (dividend).
            b (array_type): Second array (divisor). Must have the same shape
                            as :attr:`a`.
            out (array_type): Array into which the output is placed. Must have
                              the same shape as :attr:`a` and :attr:`b`.
        Returns:
            None
        """

    @abc.abstractmethod
    def fill_gaussian(self, mean, std, out):
        """Fill an array with values drawn from a Gaussian distribution.

        Args:
            mean (float): Mean of the Gaussian Distribution.
            std (float): Standard deviation of the Gaussian distribution.
            out (array_type): Target array to fill with values.

        Returns:
            None
        """

    @abc.abstractmethod
    def generate_probability_mask(self, mask, probability):
        """Fill an array with zeros and ones.

        Fill an array with zeros and ones such that the probability of an
        entry being one is equal to :attr:`probability`.

        Args:
            mask (array_type): Array to will be filled.
            probability (float): Probability of an entry of :attr:`mask` being
            equal to one.
        Returns:
            None
        """

    @abc.abstractmethod
    def index_m_by_v(self, m, v, out):
        """Get elements from a matrix using indices from a vector.

        :attr:`v` and :attr:`out` must be column vectors of the same size.
        Elements from the matrix :attr:`m` are copied using the indices given
        by a column vector. From row `i` of the matrix, the entry from column
        `v[i, 0]` is copied to out, such that `out[i, 0] = m[i, v[i, 0]]`.

        Note that `m` must have enough columns such that all indices in
        :attr:`v` are valid.

        Args:
            m (array_type): Matrix (2D array) whose elements should be copied.
            v (array_type): Column vector (2D array with a single column) whose
                            values are used as indices into :attr:`m`. The
                            number of rows must be the same as :attr:`m`.
            out (array_type): Array into which the output is placed. It's shape
                              must be the same as :attr:`v`.
        Returns:
            None
        """

    @abc.abstractmethod
    def log_t(self, a, out):
        """Compute the element-wise natural logarithm.

        The natural logarithm log is the inverse of the exponential function,
        so that `log(exp(x)) = x`.

        Args:
            a (array_type): Array whose logarithm is to be computed.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`a`.
        Returns:
            None
        """

    @abc.abstractmethod
    def maxpool2d_backward_batch(self, inputs, window, outputs, padding,
                                 stride, argmax, in_deltas, out_deltas):
        """Computes the gradients for 2D max-pooling on a batch of images.

        Args:
            inputs (array_type):
            window (tuple[int]):
            outputs (array_type):
            padding (int):
            stride (tuple[int]):
            argmax (array_type):
            in_deltas (array_type):
            out_deltas (array_type):
        Returns:
            None
        """

    @abc.abstractmethod
    def maxpool2d_forward_batch(self, inputs, window, outputs, padding,
                                stride, argmax):
        """Performs a 2D max-pooling on a batch of images.

        Args:
            inputs (array_type):
            window (tuple[int]):
            outputs (array_type):
            padding (int):
            stride (tuple[int]):
            argmax (array_type):
        Returns:
            None
        """

    @abc.abstractmethod
    def mult_add_st(self, a, b, out):
        """Multiply a scalar with each element of a tensor and add to a tensor.

        Args:
            s (dtype): The scalar value to be multiplied.
            t (array_type): The array to be multiplied.
            out (array_type): Array into which the product is added. Must have
                              the same shape as :attr:`t`.
        Returns:
            None
        """
        out[:] += a * b

    @abc.abstractmethod
    def mult_add_tt(self, a, b, out):
        """Multiply two tensors element-wise and add to a tensor.

        Args:
            a (array_type): First array.
            b (array_type): Second array. Must have the same shape as
                            :attr:`a`.
            out (array_type): Array into which the output is added.  Must have
                              the same shape as :attr:`a` and :attr:`b`.
        Returns:
            None
        """

    @abc.abstractmethod
    def mult_mv(self, m, v, out):
        """Multiply a matrix with a vector.

        Multiply an (M, N) matrix with a (1, N) or (M, 1) vector using
        broadcasting such that the output is (M, N).

        Args:
            m (array_type): The first array. Must be 2D.
            v (array_type): The second array, to be multiplied with :attr:`a`.
                            Must be 2D with at least one dimension of size 1
                            and the other dimension matching the corresponding
                            size of :attr:`m`.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`m`.
        Returns:
            None
        """

    @abc.abstractmethod
    def mult_st(self, a, b, out):
        """Multiply a scalar with each element of a tensor.

        Args:
            s (dtype): The scalar value to be multiplied.
            t (array_type): The array to be multiplied.
            out (array_type): Array into which the output is placed. Must have
                              the same shape as :attr:`t`.
        Returns:
            None
        """

    @abc.abstractmethod
    def mult_tt(self, a, b, out):
        """Multiply two tensors of the same shape element-wise.

        Args:
            a (array_type): First array.
            b (array_type): Second array. Must have the same shape as
                            :attr:`a`.
            out (array_type): Array into which the output is placed. Must have
                              the same shape as :attr:`a` and :attr:`b`.
        Returns:
            None
        """

    @abc.abstractmethod
    def sign_t(self, a, out):
        """Compute an element-wise indication of the sign of a number.

        Output has the value 1.0 if an element is positive, 0 if it is zero,
        and -1.0 if it is negative.

        Args:
            a (array_type): Array whose sign is to be computed.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`a`.
        Returns:
            None
        """

    @abc.abstractmethod
    def sqrt_t(self, a, out):
        """Compute the positive square-root of an array, element-wise.

        Args:
            a (array_type): Array whose square root is to be computed.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`a`.
        Returns:
            None
        """

    @abc.abstractmethod
    def subtract_mv(self, m, v, out):
        """Subtract a vector from a matrix with broadcasting.

        Args:
            m (array_type): The first array. Must be 2D.
            v (array_type): The second array, to be subtracted from :attr:`a`.
                            Must be 2D with at least one dimension of size 1
                            and second dimension matching the corresponding
                            size of :attr:`m`.
            out (array_type): Array into which the output is placed. Must
                              have the same shape as :attr:`m`.
        Returns:
            None
        """

    @abc.abstractmethod
    def subtract_tt(self, a, b, out):
        """Subtract a tensor from another element-wise.

        Args:
            a (array_type): First array.
            b (array_type): Second array, to be subtracted from :attr:`a`.
                            Must have the same shape as :attr:`a`.
            out (array_type): Array into which the output
                              (:attr:`a` - :attr:`b`) is placed. Must
                              have the same shape as :attr:`a` and :attr:`b`.
        Returns:
            None
        """

    @abc.abstractmethod
    def sum_t(self, a, axis, out):
        """Sum the elements of an array along a given axis.

        If axis is None, the sum is computed over all elements of the array.
        Otherwise, it is computed along the specified axis.

        Note:
            Only 1D and 2D arrays are currently supported.
        Args:
            a (array_type): Array to be summed.
            axis (int): Axis over which the summation should be done.
            out (array_type): Array into which the output is placed.
        Returns:
            None
        """

    # ------------------------ Activation functions ------------------------- #

    @abc.abstractmethod
    def rel(self, x, y):
        """Compute the rel (rectified linear) function.

        `y = rel(x) = max(0, x)`

        Args:
            x (array_type): Input array.
            y (array_type): Output array.
        Returns:
            None
        """

    @abc.abstractmethod
    def rel_deriv(self, x, y, dy, dx):
        """Backpropagate derivatives through the rectified linear function.

        Args:
            x (array_type): Inputs to the rel function.
                            This argument is not used and is present only to
                            conform with other activation functions.
            y (array_type): Outputs of the rel function.
            dy (array_type): Derivatives with respect to the outputs.
            dx (array_type): Array in which the derivatives with respect to
                             the inputs are placed.
        Returns:
            None
        """

    @abc.abstractmethod
    def sigmoid(self, x, y):
        """Compute the sigmoid function.

        `y = sigmoid(x) = 1 / (1 + exp(-x))`
        Args:
            x (array_type): Input array.
            y (array_type): Output array.
        Returns:
            None
        """

    @abc.abstractmethod
    def sigmoid_deriv(self, x, y, dy, dx):
        """Backpropagate derivatives through the sigmoid function.

        Args:
            x (array_type): Inputs to the sigmoid function.
                            This argument is not used and is present only to
                            conform with other activation functions.
            y (array_type): Outputs of the sigmoid function.
            dy (array_type): Derivatives with respect to the outputs.
            dx (array_type): Array in which the derivatives with respect to
                             the inputs are placed.
        Returns:
            None
        """

    @abc.abstractmethod
    def softmax_m(self, m, out):
        """Compute the softmax function over last dimension of a matrix.

        Args:
            m (array_type): Input array.
            out (array_type): Output array.
        Returns:
            None
        """

    @abc.abstractmethod
    def tanh(self, x, y):
        """Compute the tanh (hyperbolic tangent) function.

        `y = tanh(x) = (e^z - e^-z) / (e^z + e^-z)`

        Args:
            x (array_type): Input array.
            y (array_type): Output array.
        Returns:
            None
        """

    @abc.abstractmethod
    def tanh_deriv(self, x, y, dy, dx):
        """Backpropagate derivatives through the tanh function.

        Args:
            x (array_type): Inputs to the tanh function.
                            This argument is not used and is present only to
                            conform with other activation functions.
            y (array_type): Outputs of the tanh function.
            dy (array_type): Derivatives with respect to the outputs.
            dx (array_type): Array in which the derivatives with respect to
                             the inputs are placed.
        Returns:
            None
        """
