import traceback

import sys
from contextlib import contextmanager
from mlchain.base.log import logger
import re
from traceback import StackSummary, extract_tb

def exception_handle(type, value, traceback):
    logger.error(format_exc(tb=traceback, exception=value))

@contextmanager
def except_handler():
    "Sets a custom exception handler for the scope of a 'with' block."
    sys.excepthook = exception_handle
    yield
    sys.excepthook = sys.__excepthook__

def format_exc(name='mlchain', tb=None, exception=None):
    if exception is None:
        formatted_lines = traceback.format_exc().splitlines()
    else:
        formatted_lines = []
        if tb is not None:
            for item in StackSummary.from_list(extract_tb(tb)).format():
                str_item = str(item)
                if str_item.endswith("\n"):
                    formatted_lines.append(str_item[:-1])
                else:
                    formatted_lines.append(str_item)
        formatted_lines += [x for x in re.split('(\\\\n)|(\\n)', str(exception)) if x not in ["\\n", "\n", "", None]]
    
    output = []
    kt = True
    last_mlchain_append = -1
    for x in formatted_lines:
        output.append(x)
        # if x.strip().startswith("File"):
        #     if ('site-packages/mlchain' in x or 'site-packages/trio' in x) and not ("mlchain.base.exceptions" in x or "AssertionError" in x):
        #         kt = False
        #     else:
        #         kt = True

        # if kt or 'AssertionError' in x or 'mlchain.base.exceptions' in x:
        #     if x.startswith("'), AssertionError"):
        #         output.append("\n" + x[4:])
        #     else:
        #         output.append(x)
        # elif last_mlchain_append != len(output):
        #     output.append('  File "{}" collapsed errors'.format(name))
        #     last_mlchain_append = len(output)
    
    return "\n".join(output) + "\n"

