from mlchain.base import ServeModel
from mlchain.base.serializer import JsonSerializer, MsgpackSerializer, MsgpackBloscSerializer
import warnings
from typing import *
import numpy as np
import os
from inspect import signature
from collections import defaultdict
cv2 = None 
ALL_LOWER_TRUE = ["true", "yes", "yeah", "y"]

def import_cv2():
    global cv2
    if cv2 is None:
        import cv2 as cv
        cv2 = cv
        
def str2ndarray(value: str) -> np.ndarray:
    if value[0:4] == 'http':
        from mlchain.base.utils import is_image_url_and_ready
        # If it is a url image
        if is_image_url_and_ready(value):
            from mlchain.base.utils import url_to_image
            return url_to_image(value)
        else:
            raise AssertionError("Image url is not valid")
    elif os.path.exists(value):
        import_cv2()
        return cv2.imread(value)
    else:
        import_cv2()
        # If it is a base64 encoded array
        try:
            from base64 import b64decode
            nparr = np.fromstring(b64decode(value), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
            return img
        except:
            pass

        try:
            # If it is a string array
            import ast
            return np.array(ast.literal_eval(value))
        except:
            raise Exception("There's no way to convert to numpy array with variable {}".format(value))

    return value


def list2ndarray(value: list) -> np.ndarray:
    return np.array(value)


def str2int(value: str) -> int:
    return int(value)


def str2float(value: str) -> float:
    return float(value)


def str2bool(value: str) -> bool:
    if value.lower() in ALL_LOWER_TRUE:
        return True
    return False


class MLServer:
    def __init__(self, model: ServeModel, name=None):
        if not isinstance(model, ServeModel):
            model = ServeModel(model)
        self.model = model
        self.name = name or model.name
        self.serializers_dict = {
            'application/json': JsonSerializer(),
            'application/msgpack': MsgpackSerializer(),
        }
        try:
            self.serializers_dict['application/msgpack_blosc'] = MsgpackBloscSerializer()
        except:
            self.serializers_dict['application/msgpack_blosc'] = self.serializers_dict['application/msgpack']
            warnings.warn("Can't load MsgpackBloscSerializer. Use msgpack instead")

        self.convert_dict = defaultdict(dict)

        self._add_convert(str2ndarray)
        self._add_convert(list2ndarray)
        self._add_convert(str2int)
        self._add_convert(str2float)
        self._add_convert(str2bool)

    def _add_convert(self, function):
        sig = signature(function)
        parameters = sig.parameters
        for key, input_types in parameters.items():
            input_types = input_types.annotation
            output_types = sig.return_annotation
            if input_types == Union:
                input_types = input_types.__args__
            else:
                input_types = [input_types]

            if output_types == Union:
                output_types = output_types.__args__
            else:
                output_types = [output_types]

            for i_type in input_types:
                for o_type in output_types:
                    self.convert_dict[i_type][o_type] = function
            break

    def _check_status(self):
        """
        Check status of a served model
        """
        return "pong"

    def _add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, methods=['GET', 'POST']):
        """
        Add one endpoint to the flask application. Accept GET, POST and PUT.
        :param endpoint: Callable URL.
        :param endpoint_name: Name of the Endpoint
        :param handler: function to execute on call on the URL
        :return: Nothing
        """
        raise NotImplementedError

    def _initalize_app(self):
        """
        Initalize all endpoint of server
        """

        self._add_endpoint('/api/get_params_<function_name>', '_get_parameters_of_func',
                           handler=self.model._get_parameters_of_func, methods=['GET'])
        self._add_endpoint('/api/des_func_<function_name>', '_get_description_of_func',
                           handler=self.model._get_description_of_func, methods=['GET'])

        self._add_endpoint('/api/ping', '_check_status', handler=self._check_status, methods=['GET'])
        self._add_endpoint('/api/description', '_get_all_description', handler=self.model._get_all_description,
                           methods=['GET'])
        self._add_endpoint('/api/list_all_function', '_list_all_function', handler=self.model._list_all_function,
                           methods=['GET'])
        self._add_endpoint('/api/list_all_function_and_description', '_list_all_function_and_description',
                           handler=self.model._list_all_function_and_description, methods=['GET'])

        # Each valid serve function of model will be an endpoint of server
        self._add_endpoint('/call/<function_name>', '__call_function', handler=self._call_function, methods=['POST'])
        # self._add_endpoint('/result/<key>', '__result', handler=self.model.result, methods=['GET'])

    def convert(self, value, out_type):
        if isinstance(value, out_type):
            return value
        out_type = Union[out_type]
        if out_type == Union:
            out_type = out_type.__args__
        else:
            out_type = (out_type,)
        if type(value) in out_type:
            return value
        else:
            for i_type in self.convert_dict:
                if isinstance(value, i_type):
                    for o_type in self.convert_dict[i_type]:
                        if o_type in out_type:
                            return self.convert_dict[i_type][o_type](value)
        return value

    def _normalize_kwargs_to_valid_format(self, kwargs, func_):
        """
        Normalize data into right formats of func_
        """
        inspect_func_ = signature(func_)

        accept_kwargs = "**" in str(inspect_func_)

        # Check valid parameters
        for key, value in kwargs.items():
            if key in inspect_func_.parameters:
                req_type = inspect_func_.parameters[key].annotation
                kwargs[key] = self.convert(value, req_type)

        return kwargs

    def get_kwargs(self, func, *args, **kwargs):
        sig = signature(func)
        parameters = sig.parameters

        kwgs = {}
        for key, value in zip(parameters.keys(), args):
            kwgs[key] = value
        kwgs.update(kwargs)
        return kwgs

    def _call_function(self, *args, **kwargs):
        """
        Flow request values into function_name and return output
        """
        raise NotImplementedError
