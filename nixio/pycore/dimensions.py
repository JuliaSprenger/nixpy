# Copyright (c) 2016, German Neuroinformatics Node (G-Node)
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

from numbers import Number
import numpy as np
from .util import util
from .data_set import DataType
from ..dimension_type import DimensionType


class Dimension(object):

    def __init__(self, h5group):
        from nixio.pycore.h5group import H5Group
        if not isinstance(h5group, H5Group):
            print(h5group)
            raise Exception
        self._h5group = h5group

    @classmethod
    def _create_new(cls, parent, index):
        h5group = parent.open_group(str(index))
        newdim = cls(h5group)
        newdim.index = index
        return newdim

    @property
    def dimension_type(self):
        return self._h5group.get_attr("dimension_type")

    @dimension_type.setter
    def dimension_type(self, dimtype):
        if dimtype not in (DimensionType.Sample, DimensionType.Range,
                           DimensionType.Set):
            raise ValueError("Invalid dimension type.")
        self._h5group.set_attr("dimension_type", dimtype)

    @property
    def index(self):
        return self._h5group.get_attr("index")

    @index.setter
    def index(self, idx):
        util.check_attr_type(idx, int)
        self._h5group.set_attr("index", idx)


class SampledDimension(Dimension):

    def __init__(self, h5group):
        super(SampledDimension, self).__init__(h5group)

    @classmethod
    def _create_new(cls, parent, index, sample):
        newdim = super(SampledDimension, cls)._create_new(parent, index)
        newdim.dimension_type = DimensionType.Sample
        newdim.sampling_interval = sample
        return newdim

    def position_at(self, index):
        offset = self.offset if self.offset else 0
        sample = self.sampling_interval
        return index * sample + offset

    def index_of(self, position):
        offset = self.offset if self.offset else 0
        sample = self.sampling_interval
        index = round((position - offset) / sample)
        if index < 0:
            raise IndexError("Position is out of bounds of this dimension!")
        return index

    def axis(self, count, start=0):
        offset = self.offset if self.offset else 0
        sample = self.sampling_interval
        end = (count + start) * sample + offset
        return tuple(np.arange(offset, end, sample))

    @property
    def label(self):
        return self._h5group.get_attr("label")

    @label.setter
    def label(self, l):
        util.check_attr_type(l, str)
        self._h5group.set_attr("label", l)

    @property
    def unit(self):
        return self._h5group.get_attr("unit")

    @unit.setter
    def unit(self, u):
        util.check_attr_type(u, str)
        self._h5group.set_attr("unit", u)

    @property
    def offset(self):
        return self._h5group.get_attr("offset")

    @offset.setter
    def offset(self, o):
        util.check_attr_type(o, Number)
        self._h5group.set_attr("offset", o)


class RangeDimension(Dimension):

    def __init__(self, h5group):
        super(RangeDimension, self).__init__(h5group)

    @classmethod
    def _create_new(cls, parent, index, ticks):
        newdim = super(RangeDimension, cls)._create_new(parent, index)
        newdim.dimension_type = DimensionType.Range
        newdim._h5group.create_dataset("ticks", shape=np.shape(ticks))
        newdim._h5group.group["ticks"][:] = ticks
        return newdim

    @property
    def ticks(self):
        if "ticks" not in self._h5group:
            return None
        tdata = self._h5group.group["ticks"]
        return tuple(tdata)

    @ticks.setter
    def ticks(self, ticks):
        if np.any(np.diff(ticks) < 0):
            raise ValueError("Ticks are not given in an ascending order.")
        tshape = np.shape(ticks)
        dt = DataType.Double
        # TODO: Resize instead of delete?
        if "ticks" in self._h5group:
            del self._h5group.group["ticks"]
        self._h5group.create_dataset("ticks", shape=tshape, dtype=dt,
                                     chunks=True, maxshape=None)
        self._h5group.group["ticks"][:] = ticks

    @property
    def label(self):
        return self._h5group.get_attr("label")

    @label.setter
    def label(self, l):
        util.check_attr_type(l, str)
        self._h5group.set_attr("label", l)

    @property
    def unit(self):
        return self._h5group.get_attr("unit")

    @unit.setter
    def unit(self, u):
        util.check_attr_type(u, str)
        self._h5group.set_attr("unit", u)

    def index_of(self, position):
        ticks = self.ticks
        if position < ticks[0]:
            return 0
        elif position > ticks[-1]:
            return len(ticks) - 1

        ticks = np.array(ticks)
        pidxs = np.flatnonzero((ticks - position) >= 0)
        return pidxs[0]

    def tick_at(self, index):
        ticks = list(self.ticks)
        return ticks[index]

    def axis(self, count, start=0):
        ticks = self.ticks
        end = start + count
        if end > len(ticks):
            raise IndexError("RangeDimension.axis: Count is invalid, "
                             "reaches beyond the ticks stored in this "
                             "dimension.")
        return ticks[start:end]


class SetDimension(Dimension):

    def __init__(self, h5group):
        super(SetDimension, self).__init__(h5group)

    @classmethod
    def _create_new(cls, parent, index):
        newdim = super(SetDimension, cls)._create_new(parent, index)
        newdim.dimension_type = DimensionType.Set
        return newdim

    @property
    def labels(self):
        if "labels" not in self._h5group:
            return ()
        return tuple(self._h5group.group["labels"])

    @labels.setter
    def labels(self, labels):
        lshape = np.shape(labels)
        dt = util.vlen_str_dtype
        self._h5group.create_dataset("labels", shape=lshape, dtype=dt,
                                     chunks=True, maxshape=None)
        self._h5group.group["labels"][:] = labels
