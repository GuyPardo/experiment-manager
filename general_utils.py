# -*- coding: utf-8 -*-
"""
Created on Sun Jun  5 12:57:13 2022

@author: guypa
"""


import itertools
def enumerated_product(*args):
    yield from zip(itertools.product(*(range(len(x)) for x in args)), itertools.product(*args))