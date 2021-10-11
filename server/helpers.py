import subprocess
import json
import sys
import os
from typing import List

import shlex


def cmd2array(cmd: str) -> List[str]:
    if os.name == "posix":
        return shlex.split(cmd)
    else:
        # TODO: write a version of this that doesn't invoke a subprocess
        if not cmd:
            return []
        command = [
            "bash",
            "-c",
            "python -c \"import sys, json; print(json.dumps(sys.argv[1:]))\" {}".format(cmd)
        ]
        ret = subprocess.check_output(command).decode()
        return json.loads(ret)

