from mlchain.base.serve_model import ServeModel
from mlchain.base.wrapper import GunicornWrapper
from mlchain.base.log import logger
from flask import Flask, request, jsonify, Response, send_file, render_template
from flask_cors import CORS
from .swagger import SwaggerTemplate
from .autofrontend import AutofrontendConfig
from .base import MLServer
from mlchain.log import format_exc
from mlchain.observe import apm
from typing import *
import numpy as np
from werkzeug.datastructures import FileStorage
from mlchain.config import apm_config
from mlchain.log.log import MLLogger
import time
import random
import json
import os
import re
import mlchain

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'server/templates')
STATIC_PATH = os.path.join(APP_PATH, 'server/static')


class FlaskEndpointAction(object):
    """
    Defines an Flask Endpoint for a specific action for any client.
    """

    def __init__(self, action, serializers_dict):
        """
        Create the endpoint by specifying which action we want the endpoint to perform, at each call
        :param action: The function to execute on endpoint call
        """
        # Defines which action (which function) should be called
        assert callable(action)

        self.action = action
        self.serializers_dict = serializers_dict

        self.json_serializer = self.serializers_dict['application/json']
        self.msgpack_serializer = self.serializers_dict['application/msgpack']
        self.msgpack_blosc_serializer = self.serializers_dict['application/msgpack_blosc']

    def __call__(self, *args, **kwargs):
        """
        Standard method that effectively perform the stored action of this endpoint.
        :param args: Arguments to give to the stored function
        :param kwargs: Keywords Arguments to give to the stored function
        :return: The response, which is a jsonified version of the function returned value
        """
        start_time = time.time()

        # If data POST is in msgpack format
        serializer = self.serializers_dict.get(request.content_type, self.serializers_dict[
            request.headers.get('serializer', 'application/json')])
        try:
            if request.method == 'POST':
                output = self.action(*args, **kwargs, serializer=serializer)
            else:
                output = self.action(*args, **kwargs)
            status = 200
        except AttributeError as ex:
            logger.debug(format_exc(name='mlchain.serve.server'))

            output = str(format_exc(name='mlchain.serve.server'))
            status = 404
        except AssertionError as ex:
            logger.debug(format_exc(name='mlchain.serve.server'))

            output = str(format_exc(name='mlchain.serve.server'))
            status = 422
        except Exception as ex:
            logger.debug(format_exc(name='mlchain.serve.server'))

            output = str(format_exc(name='mlchain.serve.server'))
            status = 500
        process_time = time.time() - start_time

        if request.content_type == 'application/msgpack':
            output_encoded = self.msgpack_serializer.encode(output)
            return Response(output_encoded, mimetype='application/msgpack', status=status,
                            headers=[('TIME', process_time)])
        elif request.content_type == 'application/msgpack_blosc':
            output_encoded = self.msgpack_blosc_serializer.encode(output)
            return Response(output_encoded, mimetype='application/msgpack_blosc', status=status,
                            headers=[('TIME', process_time)])
        else:
            output_encoded = self.json_serializer.encode(output)
            return Response(output_encoded, mimetype='application/json', status=status,
                            headers=[('TIME', process_time)])


def storage2ndarray(value: FileStorage) -> np.ndarray:
    from mlchain.base.utils import read_ndarray_from_FileStorage
    value = read_ndarray_from_FileStorage(value)
    return value


def storage2bytes(value: FileStorage) -> bytes:
    return value.read()


def storage2json(value: FileStorage) -> dict:
    return json.loads(value.read(), encoding='utf-8')


class FlaskServer(MLServer):
    def __init__(self, model: ServeModel, name=None, version='latest', trace=False, log=False,
                 monitor_sampling_rate=0.0):
        MLServer.__init__(self, model, name)
        self.app = Flask(self.name, static_folder=STATIC_PATH, template_folder=TEMPLATE_PATH, static_url_path="/static")
        self.app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
        self.version = version
        self._initalize_app()
        self.apm = apm.Client(config=apm_config, service_name=self.name) if trace else None
        self._add_convert(storage2ndarray)
        self._add_convert(storage2bytes)
        self._add_convert(storage2json)
        self.logger = MLLogger(self.name) if log else None
        self.model.log = min(monitor_sampling_rate, log)
        self.monitor_sampling_rate = monitor_sampling_rate
        self.register_home()

    def _add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, methods=['GET', 'POST']):
        """
        Add one endpoint to the flask application. Accept GET, POST and PUT.
        :param endpoint: Callable URL.
        :param endpoint_name: Name of the Endpoint
        :param handler: function to execute on call on the URL
        :return: Nothing
        """
        self.app.add_url_rule(endpoint, endpoint_name, FlaskEndpointAction(handler, self.serializers_dict),
                              methods=methods)

    def __get_kwargs_from_request_FORM(self, args, kwargs, files_args, serializer):
        """
        Get all key, value of request.form
        """

        temp = request.form.to_dict(flat=False)

        for key, value in temp.items():
            if key == "MLCHAIN INPUT":
                data = serializer.decode(value[0].encode())
                args, kwargs = list(data['input'])
                files_args = data.get('files_args', {})
            elif len(value) == 1:
                kwargs[key] = value[0]
            else:
                kwargs[key] = value

        return args, kwargs, files_args

    def __update_args_kwargs_from_request_FILES(self, args, kwargs, files_args):
        """
        Get all key, value of request.file
        """
        args = list(args)

        temp = request.files.to_dict(flat=False)

        for key, value in temp.items():
            if key in files_args:
                trace_position = files_args[key]
                if isinstance(trace_position, int):
                    args[files_args[key]] = value
                else:
                    args[trace_position[0]][trace_position[1]] = value
            else:
                if len(value) == 1:
                    kwargs[key] = value[0]
                else:
                    kwargs[key] = value

        return tuple(args), kwargs

    def __update_args_kwargs_from_request_ARGS(self, args, kwargs):
        """
        Get all key, value of request.args
        """
        temp = request.args.to_dict(flat=False)

        for key, value in temp.items():
            if len(value) == 1:
                kwargs[key] = value[0]
            else:
                kwargs[key] = value

        return args, kwargs

    def get_param_from_request(self, serializer):
        try:
            data = serializer.decode(request.data)
        except Exception as ex:
            logger.debug(format_exc(name='mlchain.serve.flask_server decode data'))
            logger.debug("ERROR: Can not decode request.data")
            data = {}

        if "input" in data:
            args, kwargs = data['input']
            files_args = data.get('files_args', {})
        else:
            args, kwargs = (), {}
            files_args = {}

        args, kwargs, files_args = self.__get_kwargs_from_request_FORM(args, kwargs, files_args, serializer)
        args, kwargs = self.__update_args_kwargs_from_request_FILES(args, kwargs, files_args)
        args, kwargs = self.__update_args_kwargs_from_request_ARGS(args, kwargs)
        return args, kwargs

    def _call_function(self, function_name, serializer):
        if self.apm and 'Traceparent' in request.headers:
            trace_parent = apm.TraceParent.from_string(request.headers.get('Traceparent'))
        else:
            trace_parent = None
        log = (random.random() < self.monitor_sampling_rate or trace_parent is not None)
        id = None
        if self.apm and log:
            transaction = self.apm.begin_transaction(str(function_name), trace_parent=trace_parent)
            if transaction:
                id = transaction.id
        if function_name is None:
            raise AssertionError("You need to specify the function name (API name)")
        info = {}
        if isinstance(function_name, str):
            # Serializer POST data
            args, kwargs = self.get_param_from_request(serializer)
            func = self.model.get_function(function_name)
            kwargs = self.get_kwargs(func, *args, **kwargs)
            kwargs = self._normalize_kwargs_to_valid_format(kwargs, func)
            try:
                start = time.time()
                output = self.model.call_function(function_name, id, **kwargs)
                duration = time.time() - start
                info["time"] = duration
                # Response data
                if self.apm and log:
                    self.apm.end_transaction(str(function_name), result="done")

                if self.logger and log:
                    self.logger.log(info, id=id, function_name=function_name, **kwargs)
            except Exception as e:
                if self.apm and log:
                    self.apm.capture_exception()
                    self.apm.end_transaction(self.name, result="error")
                info['error'] = True
                info['time'] = 0
                if self.logger and log:
                    self.logger.log(info, id=id, function_name=function_name, **kwargs)
                raise e
        else:
            if self.apm and log:
                self.apm.end_transaction(self.name, result="error")
            info['error'] = True
            info['time'] = 0
            if self.logger and log:
                self.logger.log(info, id=id, function_name=str(function_name))
            raise AssertionError("function_name must be str")

        return output

    def register_swagger(self, host, port):
        from flask_swagger_ui import get_swaggerui_blueprint
        swagger_template = SwaggerTemplate('/', [{'name': self.name}], title=self.name,
                                           description=self.model.model.__doc__, version=self.model.name)
        for name, func in self.model.get_all_func().items():
            swagger_template.add_endpoint(func, f'/call/{name}', tags=[self.name])

        SWAGGER_URL = '/swagger'
        API_URL = '/swagger_json'

        @self.app.route(API_URL, methods=['GET'])
        def swagger_json():
            return jsonify(swagger_template.template)

        SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
        self.app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)

    def register_autofrontend(self, host, port, endpoint=None, mlchain_management=None):
        if endpoint is None:
            endpoint = ''
        autofrontend_template = AutofrontendConfig(endpoint, title=self.name)
        if self.model.config is not None:
            out_configs = self.model.config
        else:
            out_configs = {}
        for name, func in self.model.get_all_func().items():
            if name in out_configs:
                out_config = out_configs[name]
                if 'config' in out_config:
                    config = out_config['config']
                else:
                    config = None
                if 'example' in out_config:
                    @self.app.route(f'/sample/{name}', methods=['POST', 'GET'])
                    def sample():
                        return jsonify({'output': out_config['example']})

                    sample_url = f'{endpoint}/sample/{name}'
                else:
                    sample_url = None
            else:
                config = None
                sample_url = None
            autofrontend_template.add_endpoint(func, f'{endpoint}/call/{name}', output_config=config,
                                               sample_url=sample_url)
        if os.path.exists("Readme.md"):
            description = open("Readme.md", encoding='utf-8').read()
        else:
            description = ""

        if os.path.exists("changelog.md"):
            changelog = open("changelog.md", encoding='utf-8').read()
        else:
            changelog = ""

        @self.app.route('/model', methods=['GET', 'POST'])
        def model_summary():
            return jsonify(autofrontend_template.summary)

        @self.app.route('/model/demo', methods=['GET', 'POST'])
        def demo_config():
            return jsonify(autofrontend_template.config)

        @self.app.route('/model/description', methods=['GET', 'POST'])
        def model_description():
            return Response(json.dumps({"value": description}), status=404)

        @self.app.route('/model/changelog', methods=['GET', 'POST'])
        def model_changelog():
            return Response(json.dumps({"value": changelog}), status=404)

        if mlchain_management and mlchain.model_id is not None:
            config_version = {
                "model_id": mlchain.model_id,
                "version": self.version,
                "input_config": autofrontend_template.input_config,
                "output_config": autofrontend_template.output_config,
                'endpoint': endpoint,
                'readme': description,
                'changelog': changelog
            }
            try:
                import requests
                r = requests.post(mlchain_management, json=config_version)
            except:
                pass

    def register_home(self):
        @self.app.route("/", methods=['GET'])
        def home():
            return render_template("home.html")

    def run(self, host='127.0.0.1', port=8080, bind=None, cors=False, cors_resources={}, cors_allow_origins='*',
            gunicorn=False, debug=False, use_reloader=False,
            workers=1, timeout=60, keepalive=10, max_requests=0, threads=1, worker_class='gthread', umask='0',
            endpoint=None, mlchain_management=None,
            **kwargs):
        """
        Run a server from a Python class
        :model: Your model class
        :host: IP address you want to start server
        :port: Port to start server at
        :bind: Gunicorn: The socket to bind. A list of string or string of the form: HOST, HOST:PORT, unix:PATH, fd://FD. An IP is a valid HOST.
        :deny_all_function: Default is False, which enable all function except function with @except_serving or function in blacklist, True is deny all and you could use with whitelist
        :blacklist: All listing function name here won't be served
        :whitelist: Served all function name inside whitelist
        :cors: Enable CORS or not
        :cors_resources: Config Resources of flask-cors
        :cors_allow_origins: Allow host of cors
        :gunicorn: Run with Gunicorn or not
        :debug: Debug or not
        :use_reloader: Default False, which is using 1 worker in debug instead of 2
        :workers: Number of workers to run Gunicorn
        :timeout: Timeout of each request
        :keepalive: The number of seconds to wait for requests on a Keep-Alive connection.
        :threads: The number of worker threads for handling requests. Be careful, threads would break your result if it is bigger than 1
        :worker_class: The type of workers to use.
        :max_requests: Max Request to restart Gunicorn Server, default is 0 which means no restart
        :umask: A bit mask for the file mode on files written by Gunicorn.
        :kwargs: Other Gunicorn options
        """
        if cors:
            CORS(self.app, resources=cors_resources, origins=cors_allow_origins)
        try:
            self.register_swagger(host, port)
        except Exception as e:
            logger.error("Can't register swagger with error {0}".format(e))

        try:
            self.register_autofrontend(host, port, endpoint=endpoint, mlchain_management=mlchain_management)
        except Exception as e:
            logger.error("Can't register autofrontend with error {0}".format(e))
        if not gunicorn:
            if bind is not None:
                if isinstance(bind, str):
                    bind = [bind]
                if isinstance(bind, list):
                    for ip_port in bind:
                        if re.match(r'(localhost:|((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.|:)){4})\d+', ip_port):
                            logger.warning("Using host and port in bind to runserver")
                            host, port = ip_port.split(":")

            logger.info("-" * 80)
            logger.info("Served model with Flask at host={0}, port={1}".format(host, port))
            logger.info("Debug = {}".format(debug))
            logger.info("-" * 80)

            self.app.run(host=host, port=port, debug=debug, use_reloader=use_reloader, threaded=threads > 1)
        else:
            # Process bind, host, port
            if isinstance(bind, str):
                bind = [bind]

            bind_host_port = '%s:%s' % (host, port)
            if bind is None:
                bind = [bind_host_port]

            logger.info("-" * 80)
            logger.info("Served model with Flask and Gunicorn at bind={}".format(bind))
            logger.info("Number of workers: {}".format(workers))
            logger.info("Number of threads: {}".format(threads))
            logger.info("API timeout: {}".format(timeout))
            logger.info("Debug = {}".format(debug))
            logger.info("-" * 80)

            loglevel = kwargs.get('loglevel', 'warning' if debug else 'info')
            gunicorn_server = GunicornWrapper(self.app, bind=bind, workers=workers, timeout=timeout,
                                              keepalive=keepalive, max_requests=max_requests, loglevel=loglevel,
                                              worker_class=worker_class, threads=threads, umask=umask, **kwargs).run()
