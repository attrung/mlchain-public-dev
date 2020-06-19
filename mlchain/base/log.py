"""
This code is referenced from Floyhub
https://github.com/Floydhub/floyd-cli
"""

import logging

logger = logging.Logger('mlchain')
hand = logging.StreamHandler()
hand.setLevel(logging.DEBUG)
hand.setFormatter(logging.Formatter('%(asctime)s-%(levelname)s-%(message)s'))
logger.addHandler(hand)