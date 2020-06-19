import click
import os
import sys
from mlchain import logger


op_config = click.option("--config", "-c", default=None, help="file json or yaml")

@click.command("prepare", short_help="Download files from object storage to local.")
@op_config
@click.option('--force/--no-force', default=False)
def prepare_command(config,force):
    from mlchain import config as mlconfig
    default_config = False
    if config is None:
        default_config = True
        config = 'mlconfig.yaml'
    if os.path.isfile(config):
        if config.endswith('.json'):
            config = mlconfig.load_json(config)
        elif config.endswith('.yaml') or config.endswith('.yml'):
            config = mlconfig.load_yaml(config)
        else:
            raise AssertionError("Not support file config {0}".format(config))
    else:
        if not default_config:
            raise FileNotFoundError("Not found file {0}".format(config))
        config = {}

    mlconfig.prepare(config,force)