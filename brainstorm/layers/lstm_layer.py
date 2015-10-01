#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
from brainstorm.structure.construction import ConstructionWrapper
from brainstorm.utils import LayerValidationError
from brainstorm.layers.base_layer import BaseLayerImpl
from brainstorm.structure.buffer_structure import (StructureTemplate,
                                                   BufferStructure)


def Lstm(size, activation_function='tanh', name=None):
    """Create an LSTM layer."""
    return ConstructionWrapper.create('Lstm', size=size, name=name,
                                      activation_function=activation_function)


class LstmLayerImpl(BaseLayerImpl):

    expected_inputs = {'default': StructureTemplate('T', 'B', 'F')}
    expected_kwargs = {'size', 'activation_function'}

    def setup(self, kwargs, in_shapes):
        self.act_func = lambda x, y: None
        self.act_func_deriv = lambda x, y, dy, dx: None
        in_size = in_shapes['default'].feature_size
        self.size = kwargs.get('size', in_size)
        if not isinstance(self.size, int):
            raise LayerValidationError('size must be int but was {}'.
                                       format(self.size))

        outputs = OrderedDict()
        outputs['default'] = BufferStructure('T', 'B', self.size,
                                             context_size=1)

        parameters = OrderedDict()
        parameters['Wz'] = BufferStructure(self.size, in_size)
        parameters['Wi'] = BufferStructure(self.size, in_size)
        parameters['Wf'] = BufferStructure(self.size, in_size)
        parameters['Wo'] = BufferStructure(self.size, in_size)
        parameters['Rz'] = BufferStructure(self.size, self.size)
        parameters['Ri'] = BufferStructure(self.size, self.size)
        parameters['Rf'] = BufferStructure(self.size, self.size)
        parameters['Ro'] = BufferStructure(self.size, self.size)
        parameters['bz'] = BufferStructure(self.size)
        parameters['bi'] = BufferStructure(self.size)
        parameters['bf'] = BufferStructure(self.size)
        parameters['bo'] = BufferStructure(self.size)

        internals = OrderedDict()
        internals['Za'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Zb'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Ia'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Ib'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Fa'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Fb'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Oa'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Ob'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Ca'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['Cb'] = BufferStructure('T', 'B', self.size, context_size=1)
        internals['dZa'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dZb'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dIa'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dIb'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dFa'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dFb'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dOa'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dOb'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dCa'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        internals['dCb'] = BufferStructure('T', 'B', self.size, context_size=1,
                                           is_backward_only=True)
        return outputs, parameters, internals

    def set_handler(self, new_handler):
        super(LstmLayerImpl, self).set_handler(new_handler)

        # Assign act_func and act_dunc_derivs
        activation_functions = {
            'sigmoid': (self.handler.sigmoid, self.handler.sigmoid_deriv),
            'tanh': (self.handler.tanh, self.handler.tanh_deriv),
            'linear': (lambda x, y: self.handler.copy_to(y, x),
                       lambda x, y, dy, dx: self.handler.copy_to(dx, dy)),
            'rel': (self.handler.rel, self.handler.rel_deriv)
        }

        self.act_func, self.act_func_deriv = activation_functions[
            self.kwargs.get('activation_function', 'tanh')]

    def forward_pass(self, buffers, training_pass=True):
        # prepare
        _h = self.handler
        (Wz, Wi, Wf, Wo,
         Rz, Ri, Rf, Ro,
         bz, bi, bf, bo) = buffers.parameters
        (Za, Zb, Ia, Ib, Fa, Fb, Oa, Ob, Ca, Cb,
         dZa, dZb, dIa, dIb, dFa, dFb, dOa, dOb, dCa, dCb) = buffers.internals
        x = buffers.inputs.default
        y = buffers.outputs.default

        time_size, batch_size, in_size = x.shape

        for t in range(time_size):
            # Block input
            _h.dot_mm(x[t], Wz, Za[t], transb=True)
            _h.dot_add_mm(y[t - 1], Rz, Za[t])
            _h.add_mv(Za[t], bz.reshape((1, self.size)), Za[t])
            self.act_func(Za[t], Zb[t])

            # Input Gate
            _h.dot_mm(x[t], Wi, Ia[t], transb=True)
            _h.dot_add_mm(y[t - 1], Ri, Ia[t])
            _h.add_mv(Ia[t], bi.reshape((1, self.size)), Ia[t])
            _h.sigmoid(Ia[t], Ib[t])

            # Forget Gate
            _h.dot_mm(x[t], Wf, Fa[t], transb=True)
            _h.dot_add_mm(y[t - 1], Rf, Fa[t])
            _h.add_mv(Fa[t], bf.reshape((1, self.size)), Fa[t])
            _h.sigmoid(Fa[t], Fb[t])

            # Cell
            _h.mult_tt(Ib[t], Zb[t], Ca[t])
            _h.mult_add_tt(Fb[t], Ca[t - 1], Ca[t])

            # Output Gate
            _h.dot_mm(x[t], Wo, Oa[t], transb=True)
            _h.dot_add_mm(y[t - 1], Ro, Oa[t])
            _h.add_mv(Oa[t], bo.reshape((1, self.size)), Oa[t])
            _h.sigmoid(Oa[t], Ob[t])

            # Block output
            self.act_func(Ca[t], Cb[t])
            _h.mult_tt(Ob[t], Cb[t], y[t])

    def backward_pass(self, buffers):
        # prepare
        _h = self.handler
        (Wz, Wi, Wf, Wo,
         Rz, Ri, Rf, Ro,
         bz, bi, bf, bo) = buffers.parameters
        (dWz, dWi, dWf, dWo,
         dRz, dRi, dRf, dRo,
         dbz, dbi, dbf, dbo) = buffers.gradients

        (Za, Zb, Ia, Ib, Fa, Fb, Oa, Ob, Ca, Cb,
         dZa, dZb, dIa, dIb, dFa, dFb, dOa, dOb, dCa, dCb) = buffers.internals

        x = buffers.inputs.default
        dx = buffers.input_deltas.default
        y = buffers.outputs.default
        deltas = buffers.output_deltas.default

        dy = _h.allocate(y.shape)

        time_size, batch_size, in_size = x.shape
        for t in range(time_size - 1, -1, - 1):
            # cumulate recurrent deltas
            _h.copy_to(dy[t], deltas[t])
            _h.dot_add_mm(dIa[t + 1], Ri, dy[t], transb=True)
            _h.dot_add_mm(dFa[t + 1], Rf, dy[t], transb=True)
            _h.dot_add_mm(dOa[t + 1], Ro, dy[t], transb=True)
            _h.dot_add_mm(dZa[t + 1], Rz, dy[t], transb=True)

            # Output Gate
            _h.mult_tt(dy[t], Cb[t], dOb[t])
            _h.sigmoid_deriv(Oa[t], Ob[t], dOb[t], dOa[t])

            # Cell
            _h.mult_tt(dy[t], Ob[t], dCb[t])
            self.act_func_deriv(Ca[t], Cb[t], dCb[t], dCa[t])
            _h.mult_add_tt(dCa[t + 1], Fb[t + 1], dCa[t])

            # Forget Gate
            _h.mult_tt(dCa[t], Ca[t - 1], dFb[t])
            _h.sigmoid_deriv(Fa[t], Fb[t], dFb[t], dFa[t])

            # Input Gate
            _h.mult_tt(dCa[t], Zb[t], dIb[t])
            _h.sigmoid_deriv(Ia[t], Ib[t], dIb[t], dIa[t])

            # Block Input
            _h.mult_tt(dCa[t], Ib[t], dZb[t])
            self.act_func_deriv(Za[t], Zb[t], dZb[t], dZa[t])

            # Input Deltas
            _h.dot_add_mm(dIa[t], Wi, dx[t])
            _h.dot_add_mm(dFa[t], Wf, dx[t])
            _h.dot_add_mm(dOa[t], Wo, dx[t])
            _h.dot_add_mm(dZa[t], Wz, dx[t])

            # Gradients for the input weights
            _h.dot_add_mm(dIa[t], x[t], dWi, transa=True)
            _h.dot_add_mm(dFa[t], x[t], dWf, transa=True)
            _h.dot_add_mm(dOa[t], x[t], dWo, transa=True)
            _h.dot_add_mm(dZa[t], x[t], dWz, transa=True)

            # Gradient for the recurrent weights
            _h.dot_add_mm(y[t], dIa[t + 1], dRi, transa=True)
            _h.dot_add_mm(y[t], dFa[t + 1], dRf, transa=True)
            _h.dot_add_mm(y[t], dOa[t + 1], dRo, transa=True)
            _h.dot_add_mm(y[t], dZa[t + 1], dRz, transa=True)

            # biases
            bias_tmp = _h.allocate(dbz.shape)
            _h.sum_t(dIa[t], axis=0, out=bias_tmp)
            _h.add_tt(bias_tmp, dbi, dbi)
            _h.sum_t(dFa[t], axis=0, out=bias_tmp)
            _h.add_tt(bias_tmp, dbf, dbf)
            _h.sum_t(dOa[t], axis=0, out=bias_tmp)
            _h.add_tt(bias_tmp, dbo, dbo)
            _h.sum_t(dZa[t], axis=0, out=bias_tmp)
            _h.add_tt(bias_tmp, dbz, dbz)
