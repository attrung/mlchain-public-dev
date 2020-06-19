# Parameters of MLchain
__version__ = "0.0.9h1"
host = "https://www.api.mlchain.ml"
web_host = host
api_address = host
model_id = None
from os import environ

environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
from mlchain.base.log import logger
from .config import mlconfig
