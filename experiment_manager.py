import os
import sys
import typing
from typing import Iterable
from copy import deepcopy
import numpy as np
from beautifultable import BeautifulTable
from dataclasses import dataclass
import Labber

sys.path.append(os.path.abspath(r"G:\My Drive\guy PHD folder\util"))
import Labber_util as lu


@dataclass
class Parameter:  # TODO - I realized this class can be used for output data as well. consider change the name
    """
    a physical parameter with name, value, units.
    """
    name: str
    value: typing.Any
    units: str = 'n.u.'
    is_iterated = None

    def __init__(self, name: str, value, units='n.u.', is_iterated=None):
        """

        :param name: str -  name of the parameter
        :param value: any type -  value of the parameter
        :param units: str  - physical units of the parameter, by default 'n.u.' = no units, which is not exactly the same thing as a.u. (arbitrary units).
        :param is_iterated: bool. detemines whether the value is constant or iterated. if iterated, then value should be an Iterable.
                                    by default self.is_iterated is defined according to whether value is an Iterable, but thie can be changed if you want, for example, a constant value that is a list.
        """
        self.name = name
        self.value = value
        self.units = units

        if is_iterated == None:
            if isinstance(self.value, Iterable):
                self.is_iterated = True
            else:
                self.is_iterated = False
        else:
            self.is_iterated = is_iterated


class Config:  # TODO - I realized this class can be used for output data as well. consider change the name
    """
    this is a package for a list of Parameter objects
    with some useful methods.
    I am assuming that the user is not going to change attributes of this class once an object is created. TODO: fix this.
    """

    def __init__(self, *param_list):
        """
        creates a Config object from a list of Parameter objects
        :param param_list: a list of Parameter objects
        """
        self.param_list = list(param_list)
        for param in self.param_list:
            setattr(self, param.name, param)

    def add_parameter(self, param: Parameter):
        self.param_list.append(param)
        setattr(self, param.name, param)

    def get_dict(self):
        d = {}
        for param in self.param_list:
            d[param.name] = param
        return d

    def get_values(self):
        values = []
        for param in self.param_list:
            values.append(param.value)
        return values

    def get_iterables(self):
        iter_list = []
        for param in self.param_list:
            if param.is_iterated:
                iter_list.append(param)
        return iter_list

    def get_constants(self):
        const_list = []
        for param in self.param_list:
            if not param.is_iterated:
                const_list.append(param)
        return const_list

    def get_metadata_table(self):
        table = BeautifulTable()
        table.columns.header = ["name", "value", "units"]
        for param in self.param_list:
            print(param)
            if param.is_iterated:
                val = "iterated"
            else:
                val = param.value
            table.rows.append([param.name, val, param.units])
        return table

    def is_constant(self):
        pass  # TODO - implement

    def get_labber_step_list(self):
        iterated_config = Config(*self.get_iterables())  # build a new config with just the iterables of self
        steplist = []
        for param in iterated_config.param_list:
            steplist.append(dict(name=param.name, unit=param.units, values=param.value))
        return steplist

    def get_labber_log_list(self):
        # thinking about the Config object as an output data
        loglist = []
        for param in self.param_list:
            loglist.append(dict(name=param.name, unit=param.units, vector=param.is_iterated))
        return loglist


def get_labber_trace(output_config_list: list[Config]):
    labber_dict = {}

    for param in output_config_list[0].param_list:
        labber_dict[param.name] = []

    for c in output_config_list:
        for param in c.param_list:
            labber_dict[param.name].append(param.value)
    for param in output_config_list[0].param_list:
        if not param.is_iterated:
             labber_dict[param.name] = np.array(labber_dict[param.name])

    return labber_dict


class Experiment:
    """
    a procedure (a computation or phyisical experiment with some controlled hardware) that you might like to run many
    times with different configurations.
    """

    def __init__(self):
        pass

    def run(self, config: Config):
        raise NotImplemented('run method not implemented')

    def one_dimensional_sweep(self, const_config: Config, variable_param: Parameter, save_to_labber=False):
        """
        execute self.run in a loop on a certain variable parameter
        :param const_config: a Config object without any iterated Parameters TODO: input verification
        :param variable_param: : an iterated Parameter TODO: input verification
        :return:
        """

        result = []
        for val in variable_param.value:
            current_param = Parameter(variable_param.name, val, units=variable_param.units)
            current_config = deepcopy(const_config)
            current_config.add_parameter(current_param)
            result.append(self.run(current_config))

        labber_trace = get_labber_trace(result)
        if save_to_labber:
            log_name = lu.get_log_name('test_exp_new')  # TODO: automatic renaming
            logfile = Labber.createLogFile_ForData(log_name, result[0].get_labber_log_list(),
                                                   Config(variable_param).get_labber_step_list())
            logfile.addEntry(get_labber_trace(result))

        return dict(output_config=result, labber_trace=labber_trace)

        product = []
        vector = []
        for val in values:
            kwargs[name] = val
            result = single_run(**kwargs)
            product.append(result["product"])
            vector.append(result["vector"])
            # for i in range(3):
            #   vector[i].append(result["vector"][i])

        product_trace = lb.getTraceDict(product, x=values)['y']
        vector_traces = [lb.getTraceDict(single_vector, x=values)['y'] for single_vector in vector]

        return dict(product_trace=product_trace, vector_traces=vector_traces)


class TestExperiment(Experiment):

    def run(self, config: Config):
        # TODO : verify that config is constant (first need to implement an is_const method for config)
        product = 1
        for param in config.param_list:
            product = product * param.value

        vector = np.array(config.get_values())

        output_config = Config(Parameter('product', product),
                               Parameter('vector', vector))
        return output_config


########################################################################################################################
config = Config(Parameter('x', 5, 'a.u.'),
                Parameter('y', 4.5, 'a.u.'),
                Parameter('z', 3))

print(config.get_metadata_table())

e = TestExperiment()

result = e.one_dimensional_sweep(config, Parameter('v', np.linspace(0,10,10)), save_to_labber=True)
