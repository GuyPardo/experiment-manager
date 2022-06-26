import itertools

import Labber as lb
import sys
import os
from general_utils import enumerated_product
import numpy as np

sys.path.append(os.path.abspath(r"G:\My Drive\guy PHD folder\util"))
import Labber_util as lu

loop_dict = {'param 1': np.linspace(0, 10, 10), 'param 2': np.linspace(0, 10, 5), 'param 3': np.linspace(0, 10, 5)}


# log_name = lu.get_log_name('test_loops')

# lStep = [dict(name=key, values=loop_dict[key]) for key in loop_dict.keys()]

# lLog = [dict(name='scalar_log', vector=False), dict(name='vector_log', vector=True)]


def single_run(**kwargs):
    '''

    :param kwargs:
    :return:
    '''
    product = kwargs['param 1'] * kwargs['param 2'] * kwargs["param 3"]
    vec = np.array([kwargs['param 1'], kwargs['param 2'], kwargs['param 3']])

    result = {'product': product, 'vector': vec}
    return result


def one_dimensional_sweep(name, values, **kwargs):
    '''    '''
    product = []
    vector = []
    for val in values:
        kwargs[name] = val
        result = single_run(**kwargs)
        product.append(result["product"])
        vector.append(result["vector"])
        #for i in range(3):
         #   vector[i].append(result["vector"][i])

    product_trace = lb.getTraceDict(product, x=values)['y']
    vector_traces = [lb.getTraceDict(single_vector, x=values)['y'] for single_vector in vector]

    return dict(product_trace=product_trace, vector_traces=vector_traces)


def sweep(names, values):
    # here i assume we sweep on al and do not make distinction btw constants and variables.
    # for now i just want to see that i can write into labber a 3d loop with scalars and vectors
    names.reverse()
    values.reverse()

    lStep = [dict(name=name, values=values[i]) for i, name in enumerate(names)]

    lLog = [dict(name='product', vector=False), dict(name='vector', vector=True)]

    log_name = lu.get_log_name('test_loops')

    logfile = lb.createLogFile_ForData(log_name, lLog, lStep)

    names.reverse()
    values.reverse()
    inner_name = names[-1]
    inner_values = values[-1]

    outer_names = names[:-1]
    outer_values = values[:-1]

    for indices, vals in enumerated_product(*outer_values):
        single_run_dict = {}
        for i, name in enumerate(outer_names):
            single_run_dict[name] = vals[i]

        res = one_dimensional_sweep(inner_name, inner_values, **single_run_dict)
        dd = {}

        dd['product'] = res['product_trace']
        dd['vector'] = res['vector_traces']
        print(dd['vector'])
        logfile.addEntry(dd)



#############################################################
# const_dict = {'param 1': 1, 'param 2': 1, 'param 3': 1}

# res = one_dimensional_sweep('param 2', np.linspace(0, 9, 10), **const_dict)
sweep(list(loop_dict.keys()), list(loop_dict.values()))
