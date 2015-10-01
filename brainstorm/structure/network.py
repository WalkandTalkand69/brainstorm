#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
import numpy as np
import h5py
import json
import re

from brainstorm.structure.architecture import (
    instantiate_layers_from_architecture)
from brainstorm.structure.buffer_views import BufferView
from brainstorm.structure.buffers import BufferManager
from brainstorm.structure.layout import create_layout
from brainstorm.structure.view_references import (resolve_references,
                                                  prune_view_references,
                                                  order_and_copy_modifiers)
from brainstorm.initializers import evaluate_initializer, ArrayInitializer
from brainstorm.randomness import Seedable
from brainstorm.structure.architecture import generate_architecture
from brainstorm.handlers import default_handler
from brainstorm.utils import NetworkValidationError
from brainstorm.layers.loss_layer import LossLayerImpl
from brainstorm.describable import get_description, create_from_description
from brainstorm.value_modifiers import GradientModifier

__all__ = ['Network']


# ################################ Network ####################################

class Network(Seedable):
    __undescribed__ = {'layers', 'loss_layers', 'buffer', '_buffer_manager'}

    # -------------------------- Constructors ---------------------------------
    @classmethod
    def from_layer(cls, some_layer):
        """
        Create Network instance from a construction layer.

        :param some_layer: Some layer used to wire up an architecture with `>>`
        :type some_layer: brainstorm.construction.ConstructionWrapper

        :returns: A fully functional Network instance.
        :rtype: brainstorm.structure.Network
        """
        arch = generate_architecture(some_layer)
        return cls.from_architecture(arch)

    @classmethod
    def from_architecture(cls, architecture):
        """
        Create Network instance from given architecture.

        :param architecture: JSON serializable Architecture description.
        :type architecture: dict

        :returns: A fully functional Network instance.
        :rtype: brainstorm.structure.Network
        """
        layers = instantiate_layers_from_architecture(architecture)
        hubs, layout = create_layout(layers)
        buffer_manager = BufferManager(layout, hubs)
        return cls(layers, buffer_manager, architecture)

    @classmethod
    def __new_from_description__(cls, description):
        net = Network.from_architecture(description['architecture'])
        net.set_memory_handler(create_from_description(description['handler']))
        net.initialize(create_from_description(description['initializers']))
        net.set_gradient_modifiers(
            create_from_description(description['gradient_modifiers']))
        net.set_weight_modifiers(
            create_from_description(description['weight_modifiers']))
        return net

    @classmethod
    def from_hdf5(cls, filename):
        with h5py.File(filename, 'r') as f:
            description = json.loads(f['description'].value.decode())
            net = create_from_description(description)
            net.handler.set_from_numpy(net.buffer.parameters,
                                       f['parameters'].value)
        return net

    def __init__(self, layers, buffer_manager, architecture, seed=None,
                 handler=default_handler):
        super(Network, self).__init__(seed)
        self.layers = layers
        self.loss_layers = _get_loss_layers(layers)
        self._buffer_manager = buffer_manager
        self.buffer = self._buffer_manager.views
        self.architecture = architecture
        self.handler = None
        self.set_memory_handler(handler)
        self.initializers = {}
        self.weight_modifiers = {}
        self.gradient_modifiers = {}
        self.default_output = None

    def get_output(self, out_name=''):
        out_name = out_name if out_name else self.default_output
        if not out_name:
            raise KeyError(
                'No output specified. Either pass an out_name to this function'
                ' or set network.default_output to fix this.')
        if not re.match(r'\w+\.\w+', out_name):
            raise ValueError('Invalid out_name "{}". Should be of the form '
                             '"LAYERNAME.OUT_NAME"'.format(out_name))
        layername, _, output_name = out_name.partition('.')
        if layername not in self.layers:
            raise KeyError('Invalid layer name "{}". Available names are: {}'
                           .format(layername, list(self.layers.keys())))
        layer_buffer = self.buffer[layername]
        if output_name not in layer_buffer.outputs:
            raise KeyError('Invalid view name "{}". Available names are: {}'
                           .format(output_name,
                                   list(layer_buffer.outputs.keys())))

        return self.handler.get_numpy_copy(layer_buffer.outputs[output_name])

    def get_input(self, input_name):
        return self.handler.get_numpy_copy(
            self.buffer.Input.outputs[input_name])


    # -------------------------- Setup Methods --------------------------------

    def initialize(self, default_or_init_dict=None, seed=None, **kwargs):
        """Initialize the weights of the network.

        Initialization can be specified in two equivalent ways:

            1. just a default initializer:

                >>> net.initialize(bs.Gaussian())

                Note that this is equivalent to:

                >>> net.initialize(default=bs.Gaussian())

            2. by passing a dictionary:

                >>> net.initialize({'RegularLayer': bs.Uniform(),
                ...                 'LstmLayer': bs.Gaussian()})

            3. by using keyword arguments:

                >>> net.initialize(RegularLayer=bs.Uniform(),
                ...                LstmLayer=bs.Uniform())

        All following explanations will be with regards to the dictionary style
        of initialization, because it is the most general one.

        .. note:: It is not recommended to combine 2. and 3. but if they are,
            then keyword arguments take precedence.

        Each initialization consists of a layer-pattern and that maps to an
        initializer or a weight-pattern dictionary.

        Layer patterns can take the following forms:

            1. ``{'layer_name': INIT_OR_SUBDICT}``
               Matches all the weights of the layer named layer_name
            2. ``{'layer_*': INIT_OR_SUBDICT}``
               Matches all layers with a name that starts with ``layer_``
               The wild-card ``*`` can appear at arbitrary positions and even
               multiple times in one path.

        There are two special layer patterns:

            3. ``{'default': INIT}``
               Matches all weights that are not matched by any other
               path-pattern
            4. ``{'fallback': INIT}``
               Set a fallback initializer for every weight. It will only be
               evaluated for the weights for which the regular initializer
               failed with an InitializationError.

               `This is useful for initializers that require a certain shape
               of weights and will not work otherwise. The fallback will then
               be used for all cases when that initializer failed.`

        The weight-pattern sub-dictionary follows the same form as the layer-
        pattern:

            1) ``{'layer_pattern': {'a': INIT_A, 'b': INIT_B}}``
            2) ``{'layer_pattern': {'a*': INIT}``
            3) ``{'layer_pattern': {'default': INIT}``
            4) ``{'layer_pattern': {'fallback': INIT}``


        An initializer can either be a scalar, something that converts to a
        numpy array of the correct shape or an :class:`Initializer` object.
        So for example:

        >>> net.initialize(default=0,
        ...                RnnLayer={'b': [1, 2, 3, 4, 5]},
        ...                ForwardLayer=bs.Gaussian())

        .. Note:: Each view must match exactly one initialization and up to one
            fallback to be unambiguous. Otherwise the initialization will fail.

        You can specify a seed to make the initialization reproducible:

        >>> net.initialize({'default': bs.Gaussian()}, seed=1234)
        """
        init_refs = _update_references_with_dict(default_or_init_dict, kwargs)
        self.initializers = get_description(init_refs)
        all_parameters = {k: v.parameters
                          for k, v in self.buffer.items()
                          if isinstance(v, BufferView) and 'parameters' in v}
        _replace_lists_with_array_initializers(init_refs)
        initializers, fallback = resolve_references(all_parameters, init_refs)
        init_rnd = self.rnd.create_random_state(seed)
        for layer_name, views in sorted(all_parameters.items()):
            if views is None:
                continue
            for view_name, view in sorted(views.items()):
                init = initializers[layer_name][view_name]
                fb = fallback[layer_name][view_name]
                if len(init) > 1:
                    raise NetworkValidationError(
                        "Multiple initializers for {}.{}: {}".format(
                            layer_name, view_name, init))

                if len(init) == 0:
                    raise NetworkValidationError("No initializer for {}.{}".
                                                 format(layer_name, view_name))
                if len(fb) > 1:
                    raise NetworkValidationError(
                        "Multiple fallbacks for {}.{}: {}".format(
                            layer_name, view_name, fb))

                fb = fb.pop() if len(fb) else None
                self.handler.set_from_numpy(
                    view,
                    evaluate_initializer(init.pop(), view.shape, fb,
                                         seed=init_rnd.generate_seed()))

    def set_weight_modifiers(self, default_or_mod_dict=None, **kwargs):
        """
        Install :class:`ValueModifiers` in the network to change the weights.

        They can be run manually using :meth:`.apply_weight_modifiers`,
        but they will also be called by the trainer after each weight update.

        :class:`ValueModifiers` can be set for specific weights in the same way
        :class:`Initializer` can, but there is no ``fallback``.
        (see :meth:`.initialize` for details)


        A modifier can be a :class:`ValueModifiers` object or a list of them.
        So for example:

        >>> net.set_weight_modifiers(
        ...    default=bs.ClipValues(-1, 1)
        ...    FullyConnectedLayer={'W': [bs.RescaleIncomingWeights(),
        ...                               bs.MaskValues(my_mask)]}
        ...    )

        .. Note:: The order in which ValueModifiers appear in the list matters,
            because it is the same order in which they will be executed.
        """
        weight_mod_refs = _update_references_with_dict(default_or_mod_dict,
                                                       kwargs)
        all_parameters = {k: v.parameters
                          for k, v in self.buffer.items()
                          if k not in ['parameters', 'gradients'] and
                          'parameters' in v}
        weight_mods, fallback = resolve_references(all_parameters,
                                                   weight_mod_refs)

        assert not prune_view_references(fallback), \
            'fallback is not supported for weight modifiers'
        weight_mods = prune_view_references(weight_mods)
        self.weight_modifiers = order_and_copy_modifiers(weight_mods)
        # TODO: Check that all are ValueModifiers

    def set_gradient_modifiers(self, default_or_mod_dict=None, **kwargs):
        """
        Install :class:`ValueModifiers` in the network to change the gradient.

        They can be run manually using :meth:`.apply_gradient_modifiers`, but
        they will also be called by the network after each backward pass.

        Gradient modifiers can be set for specific weights in the same way as
        :class:`Initializer` can, but there is no ``fallback``.
        (see :meth:`.initialize` for details)

        A modifier can be a :class:`ValueModifiers` object or a list of them.
        So for example:

        >>> net.set_gradient_modifiers(
        ...    default=bs.ClipValues(-1, 1)
        ...    FullyConnectedLayer={'W': [bs.ClipValues(),
        ...                               bs.MaskValues(my_mask)]}
        ...    )

        .. Note:: The order in which ValueModifiers appear in the list matters,
            because it is the same order in which they will be executed.
        """
        gradient_mod_refs = _update_references_with_dict(default_or_mod_dict,
                                                         kwargs)
        all_parameters = {k: v.gradients
                          for k, v in self.buffer.items()
                          if k not in ['parameters', 'gradients'] and
                          'gradients' in v}
        gradient_mods, fallback = resolve_references(all_parameters,
                                                     gradient_mod_refs)

        assert not prune_view_references(fallback), \
            'fallback is not supported for gradient modifiers'
        gradient_mods = prune_view_references(gradient_mods)
        self.gradient_modifiers = order_and_copy_modifiers(gradient_mods)
        # TODO: Check that all are ValueModifiers or GradientModifiers

    def set_memory_handler(self, new_handler):
        self.handler = new_handler
        self._buffer_manager.set_memory_handler(new_handler)
        self.buffer = self._buffer_manager.views
        for layer in self.layers.values():
            layer.set_handler(new_handler)

    # -------------------------- Running Methods ------------------------------

    def provide_external_data(self, data):
        time_size, batch_size = data[next(iter(data))].shape[: 2]
        self.buffer = self._buffer_manager.resize(time_size, batch_size)
        for name, buf in self.buffer.Input.outputs.items():
            if isinstance(data[name], self.handler.array_type):
                self.handler.copy_to(buf, data[name])
            else:
                # assert isinstance(data[name], np.ndarray)
                self.handler.set_from_numpy(buf, data[name])

    def forward_pass(self, training_pass=False, context=None):
        if context is None:
            self._buffer_manager.clear_context()
        else:
            self._buffer_manager.apply_context(context)
        for layer_name, layer in list(self.layers.items())[1:]:
            layer.forward_pass(self.buffer[layer_name], training_pass)

    def backward_pass(self):
        self._buffer_manager.clear_backward_buffers()
        for layer_name, layer in reversed(list(self.layers.items())[1:]):
            layer.backward_pass(self.buffer[layer_name])
        self.apply_gradient_modifiers()

    def get_loss_values(self):
        loss = 0.
        losses = OrderedDict()
        for loss_layer_name in self.loss_layers:
            l = float(self.handler.get_numpy_copy(
                self.buffer[loss_layer_name].outputs.loss))
            losses[loss_layer_name] = l
            loss += l
        if len(losses) > 1:
            losses['total_loss'] = loss
        return losses

    def get_context(self):
        return self._buffer_manager.get_context()

    def apply_weight_modifiers(self):
        for layer_name, views in self.weight_modifiers.items():
            for view_name, weight_mods in views.items():
                for wm in weight_mods:
                    wm.rnd.set_seed(self.rnd.generate_seed())
                    wm(self.handler,
                       self.buffer[layer_name].parameters[view_name])

    def apply_gradient_modifiers(self):
        for layer_name, views in self.gradient_modifiers.items():
            for view_name, gradient_mods in views.items():
                for gm in gradient_mods:
                    gm.rnd.set_seed(self.rnd.generate_seed())
                    if isinstance(gm, GradientModifier):
                        gm(self.handler,
                           self.buffer[layer_name].parameters[view_name],
                           self.buffer[layer_name].gradients[view_name])
                    else:
                        gm(self.handler,
                           self.buffer[layer_name].gradients[view_name])

    # -------------------------- Serialization --------------------------------

    def save_as_hdf5(self, filename):
        with h5py.File(filename, 'w') as f:
            description = get_description(self)
            f['description'] = json.dumps(description).encode()
            f.create_dataset(
                'parameters', compression='gzip',
                data=self.handler.get_numpy_copy(self.buffer.parameters))


# ########################### Helper Methods ##################################

def _get_loss_layers(layers):
    return [name for name, l in layers.items() if isinstance(l, LossLayerImpl)]


def _update_references_with_dict(refs, ref_dict):
    if refs is None:
        references = dict()
    elif isinstance(refs, dict):
        references = refs
    else:
        references = {'default': refs}

    if set(references.keys()) & set(ref_dict.keys()):
        raise TypeError('Conflicting values for %s!' %
                        sorted(set(references.keys()) & set(ref_dict.keys())))

    references.update(ref_dict)

    return references


def _replace_lists_with_array_initializers(ref_dict):
    for key, value in ref_dict.items():
        if isinstance(value, dict):
            _replace_lists_with_array_initializers(value)
        elif isinstance(value, (list, np.ndarray)):
            ref_dict[key] = ArrayInitializer(value)
