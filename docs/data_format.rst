.. _data_format:

###########
Data Format
###########

***********
Data Shapes
***********
All data passed to a network in Brainstorm by a data iterator must match
the template ``(T, B, ...)`` where ``T`` is the maximum sequence length and
``B`` is the number of sequences (or batch size, in other words).

To simplify handling both sequential and non-sequential data,
such shapes should be used even if the data is not sequential. In such cases
the shape is simply ``(1, B, ...)``. As an example, the MNIST training images
for classification with an MLP should be shaped ``(1, 60000, 784)`` and the
corresponding targets should be shaped ``(1, 60000, 1)``.

The data for images/videos should be stored in the ``TNHWC`` format. For
example, the training images for CIFAR-10 should be shaped
``(1, 50000, 32, 32, 3)`` and the targets should be shaped ``(1, 50000, 1)``.

***********
File Format
***********
There is no requirement on how to store the data in ``brainstorm``, but we
highly recommend the HDF5 format using the h5py library.

It's amazingly simple to create these files:

.. code-block:: python

    import h5py
    import numpy as np

    with h5py.File('demo.hdf5', 'w') as f:
        f['training/input_data'] = np.random.randn(7, 100, 15)
        f['training/targets'] = np.random.randn(7, 100, 2)
        f['training/static_data'] = np.random.randn(1, 100, 4)

And given that file you could use your iterator like this:

.. code-block:: python

    import h5py
    import brainstorm as bs

    ds = h5py.File('demo.hdf5', 'r')

    train_iter = bs.Online(**ds['training'])

H5py offers many more features, which can be utilized to improve data
storage and access such as chunking and compression.
