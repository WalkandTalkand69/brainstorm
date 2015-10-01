#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import numpy as np
import pytest
from brainstorm.data_iterators import (
    Online, Undivided, Minibatches, AddGaussianNoise, Pad, Flip, RandomCrop)
from brainstorm.handlers._cpuop import _crop_images
from brainstorm.utils import IteratorValidationError
from brainstorm.handlers import default_handler


# ######################### Nested Iterators ##################################

inner = Undivided(default=np.random.randn(2, 3, 1, 2, 2))

# TODO: Test AddGaussianNoise


def test_flip_dict_mismatch_raises():
    with pytest.raises(IteratorValidationError):
        _ = Flip(inner, prob_dict={'images': 1})
    with pytest.raises(IteratorValidationError):
        _ = Flip(inner, prob_dict={'default': 10})


def test_flip():
    a = np.random.randn(2, 3, 4, 5, 5)
    b = np.random.randn(2, 3, 1, 4, 4)
    c = np.random.randn(2, 3, 1)
    iterator = Undivided(default=a, secondary=b, targets=c)
    pad = Flip(iterator, prob_dict={'default': 1.0})(default_handler)
    x = next(pad)
    assert set(x.keys()) == set(iterator.data.keys())
    assert x['default'].shape == (2, 3, 4, 5, 5)
    assert x['secondary'].shape == (2, 3, 1, 4, 4)
    assert x['targets'].shape == (2, 3, 1)
    assert np.allclose(x['default'][:, :, :, :, ::-1], a)
    assert np.allclose(x['secondary'], b)
    assert np.allclose(x['targets'], c)


def test_pad_dict_mismatch_raises():
    with pytest.raises(IteratorValidationError):
        _ = Pad(inner, size_dict={'images': 1})
    with pytest.raises(IteratorValidationError):
        _ = Pad(inner, size_dict={'default': 1}, value_dict={'images': 0})


def test_pad():
    a = np.random.randn(2, 3, 4, 5, 5)
    b = np.random.randn(2, 3, 1, 4, 4)
    c = np.random.randn(2, 3, 1)
    iterator = Undivided(default=a, secondary=b, targets=c)
    pad = Pad(iterator, size_dict={'default': 1})(default_handler)
    x = next(pad)
    assert set(x.keys()) == set(iterator.data.keys())
    assert x['default'].shape == (2, 3, 4, 7, 7)
    assert x['secondary'].shape == (2, 3, 1, 4, 4)
    assert x['targets'].shape == (2, 3, 1)
    assert np.allclose(x['default'][:, :, :, 1:-1, 1:-1], a)
    assert np.allclose(x['secondary'], b)
    assert np.allclose(x['targets'], c)


def test_random_crop_dict_mismatch_raises():
    with pytest.raises(IteratorValidationError):
        _ = RandomCrop(inner, shape_dict={'images': (1, 1)})
    with pytest.raises(IteratorValidationError):
        _ = RandomCrop(inner, shape_dict={'default': 10})
    with pytest.raises(IteratorValidationError):
            _ = RandomCrop(inner, shape_dict={'default': (1, 1, 1)})
    with pytest.raises(IteratorValidationError):
            _ = RandomCrop(inner, shape_dict={'default': (10, 10)})


def test_random_crop():
    a = np.random.randn(1, 3, 4, 5, 5)
    b = np.random.randn(1, 3, 1, 4, 4)
    c = np.random.randn(1, 3, 1)
    iterator = Undivided(default=a, secondary=b, targets=c)
    pad = RandomCrop(iterator, shape_dict={'default': (3, 3),
                                           'secondary': (2, 2)
                                           })(default_handler)
    x = next(pad)
    assert set(x.keys()) == set(iterator.data.keys())
    assert x['default'].shape == (1, 3, 4, 3, 3)
    assert x['secondary'].shape == (1, 3, 1, 2, 2)
    assert x['targets'].shape == (1, 3, 1)
    assert np.allclose(x['targets'], c)


def test_crop_images_operation():
    a = np.random.randn(3, 2, 4, 5, 5)
    out = np.zeros(a.shape[:3] + (3, 3))
    _crop_images(a, 3, 3, np.array([0, 1]), np.array([0, 2]), out)
    assert np.allclose(out[:, 0, ...], a[:, 0, :, 0:3, 0:3])
    assert np.allclose(out[:, 1, ...], a[:, 1, :, 1:4, 2:5])


# ######################## Common Validation Tests ###########################

def test_non5d_data_raises():
    with pytest.raises(IteratorValidationError):
        _ = Flip(Undivided(default=np.random.randn(2, 3, 1, 2)),
                 prob_dict={'default': 1})
    with pytest.raises(IteratorValidationError):
        _ = Pad(Undivided(default=np.random.randn(2, 3, 1, 2)),
                size_dict={'default': 1})
    with pytest.raises(IteratorValidationError):
        _ = RandomCrop(Undivided(default=np.random.randn(2, 3, 1, 2)),
                       shape_dict={'default': (1, 1)})


@pytest.mark.parametrize('iterator', [Undivided, Online, Minibatches])
def test_data_iterator_with_wrong_input_type_raises(iterator):
    targets = np.ones((2, 3, 1))
    with pytest.raises(IteratorValidationError):
        iterator(my_data=None, my_targets=targets)

    with pytest.raises(IteratorValidationError):
        iterator(something='input', targets=targets)

    with pytest.raises(IteratorValidationError):
        iterator(default=[[[1]]], some_targets=targets)


@pytest.mark.parametrize('iterator', [Undivided, Online, Minibatches])
def test_data_iterator_with_wrong_targets_type_raises(iterator):
    input_data = np.zeros((2, 3, 5))
    with pytest.raises(IteratorValidationError):
        iterator(my_data=input_data, my_targets=[1])

    with pytest.raises(IteratorValidationError):
        iterator(my_data=input_data, my_targets='2')

    with pytest.raises(IteratorValidationError):
        iterator(my_data=input_data, my_target='3')


@pytest.mark.parametrize('iterator', [Undivided, Online, Minibatches])
def test_data_iterator_with_wrong_input_dim_raises(iterator):
    targets = np.ones((2, 3, 1))
    with pytest.raises(IteratorValidationError):
        iterator(my_data=np.zeros((2, 3)), my_targets=targets)


@pytest.mark.parametrize('iterator', [Undivided, Online, Minibatches])
def test_data_iterator_with_input_target_shape_mismatch_raises(iterator):
    targets = np.ones((2, 3, 1))
    with pytest.raises(IteratorValidationError):
        iterator(my_data=np.zeros((2, 5, 7)), my_targets=targets)


@pytest.mark.parametrize('iterator', [Undivided, Online, Minibatches])
def test_data_iterator_with_shape_mismatch_among_targets_raises(iterator):
    targets1 = np.ones((2, 3, 1))
    targets2 = np.ones((2, 5, 1))
    with pytest.raises(IteratorValidationError):
        iterator(my_data=np.zeros((2, 3, 7)),
                 targets1=targets1,
                 targets2=targets2)
    with pytest.raises(IteratorValidationError):
        iterator(my_data=np.zeros((2, 5, 7)),
                 targets1=targets1,
                 targets2=targets2)


# ########################### Undivided #######################################

def test_undivided_default():
    input_data = np.zeros((2, 3, 5))
    targets = np.ones((2, 3, 1))
    iter = Undivided(my_data=input_data, my_targets=targets)(default_handler)
    x = next(iter)
    assert np.all(x['my_data'] == input_data)
    assert np.all(x['my_targets'] == targets)
    with pytest.raises(StopIteration):
        next(iter)


def test_undivided_named_targets():
    input_data = np.zeros((2, 3, 5))
    targets1 = np.ones((2, 3, 1))
    targets2 = np.ones((2, 3, 1))
    iter = Undivided(my_data=input_data,
                     targets1=targets1,
                     targets2=targets2)(default_handler)
    x = next(iter)
    assert np.all(x['my_data'] == input_data)
    assert np.all(x['targets1'] == targets1)
    assert np.all(x['targets2'] == targets2)

    with pytest.raises(StopIteration):
        next(iter)


# ########################### Online ##########################################

def test_online_default():
    input_data = np.zeros((4, 5, 3))
    targets = np.ones((4, 5, 1))
    it = Online(my_data=input_data,
                my_targets=targets,
                shuffle=False)(default_handler)
    x = next(it)
    assert set(x.keys()) == {'my_data', 'my_targets'}
    assert x['my_data'].shape == (4, 1, 3)
    assert x['my_targets'].shape == (4, 1, 1)
    x = next(it)
    assert set(x.keys()) == {'my_data', 'my_targets'}
    assert x['my_data'].shape == (4, 1, 3)
    assert x['my_targets'].shape == (4, 1, 1)
    x = next(it)
    assert set(x.keys()) == {'my_data', 'my_targets'}
    assert x['my_data'].shape == (4, 1, 3)
    assert x['my_targets'].shape == (4, 1, 1)
    x = next(it)
    assert set(x.keys()) == {'my_data', 'my_targets'}
    assert x['my_data'].shape == (4, 1, 3)
    assert x['my_targets'].shape == (4, 1, 1)
    x = next(it)
    assert set(x.keys()) == {'my_data', 'my_targets'}
    assert x['my_data'].shape == (4, 1, 3)
    assert x['my_targets'].shape == (4, 1, 1)
    with pytest.raises(StopIteration):
        next(it)
