#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import numpy as np
from brainstorm.describable import Describable


class RandomState(np.random.RandomState):
    """
    An extension of the numpy RandomState that saves it's own seed
    and offers convenience methods to generate seeds and other RandomStates.
    """

    seed_range = (0, 1000000000)

    def __init__(self, seed=None):
        if seed is None:
            seed = np.random.randint(*RandomState.seed_range)
        super(RandomState, self).__init__(seed)
        self._seed = seed

    def seed(self, seed=None):
        """
        Set the seed of this RandomState.
        This method is kept for compatibility with the numpy RandomState. But
        for better readability you are encouraged to use the set_seed() method
        instead.

        :param seed: the seed to reseed this random state with.
        :type seed: int
        """
        super(RandomState, self).seed(seed)
        self._seed = seed

    def get_seed(self):
        """
        Return the seed of this RandomState.
        """
        return self._seed

    def set_seed(self, seed):
        """
        Set the seed of this RandomState.
        """
        self.seed(seed)

    def reset(self):
        """
        Reset the internal state of this RandomState.
        """
        self.seed(self._seed)

    def generate_seed(self):
        """
        Generate a random seed.
        """
        return self.randint(*RandomState.seed_range)

    def create_random_state(self, seed=None):
        """
        Create and return new RandomState object. If seed is given this is
        equivalent to RandomState(seed). Otherwise this will first generate a
        seed and initialize the new RandomState with that.
        """
        if seed is None:
            seed = self.generate_seed()
        return RandomState(seed)


class Seedable(Describable):
    """
    Baseclass for all objects that use randomness.
    It offers a self.rnd which is a RandomState.

    Dev-note: It inherits from Describable in order to implement
    __init_from_description__ and to make rnd undescribed.

    """
    __undescribed__ = {'rnd'}

    def __init__(self, seed=None):
        self.rnd = RandomState(seed)

    def __init_from_description__(self, description):
        Seedable.__init__(self)


global_rnd = RandomState()