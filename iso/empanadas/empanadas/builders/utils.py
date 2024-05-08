import pathlib
import subprocess

from typing import Callable, List, Tuple, Union

CMD_PARAM_T = List[Union[str, Callable[..., str]]]

STR_NONE_T = Union[bytes, None]
BYTES_NONE_T = Union[bytes, None]
# Tuple of int, stdout, stderr, uuid
CMD_RESULT_T = Tuple[int, BYTES_NONE_T, BYTES_NONE_T, STR_NONE_T]




def render_template(path, template, **kwargs) -> pathlib.Path:
    with open(path, "wb") as f:
        _template = template.render(**kwargs)
        f.write(_template.encode())
        f.flush()
    output = pathlib.Path(path)
    if not output.exists():
        raise Exception("Failed to template")
    return output


def runCmd(ctx, prepared_command: List[str], search: Callable = None) -> CMD_RESULT_T:
    ctx.log.info(f"Running command: {' '.join(prepared_command)}")

    kwargs = {
        "stderr": subprocess.PIPE,
        "stdout": subprocess.PIPE
    }

    if ctx.debug:
        del kwargs["stderr"]

    with subprocess.Popen(prepared_command,  **kwargs) as p:
        uuid = None
        # @TODO implement this as a callback?
        if search:
            for _, line in enumerate(p.stdout):  # type: ignore
                ln = line.decode()
                if ln.startswith("UUID: "):
                    uuid = ln.split(" ")[-1]
                    ctx.log.debug(f"found uuid: {uuid}")

        out, err = p.communicate()
        res = p.wait(), out, err, uuid

        if res[0] > 0:
            ctx.log.error(f"Problem while executing command: '{prepared_command}'")
        if search and not res[3]:
            ctx.log.error("UUID not found in stdout. Dumping stdout and stderr")
        log_subprocess(ctx, res)

        return res


def log_subprocess(ctx, result: CMD_RESULT_T):
    def log_lines(title, lines):
        ctx.log.info(f"====={title}=====")
        ctx.log.info(lines.decode())
    ctx.log.info(f"Command return code: {result[0]}")
    stdout = result[1]
    stderr = result[2]
    if stdout:
        log_lines("Command STDOUT", stdout)
    if stderr:
        log_lines("Command STDERR", stderr)


def remove_first_directory(path):
    p = pathlib.Path(path)
    # Check if the path is absolute
    if p.is_absolute():
        # For an absolute path, start the new path with the root
        new_path = pathlib.Path(p.root, *p.parts[2:])
    else:
        # For a relative path, simply skip the first part
        new_path = pathlib.Path(*p.parts[1:])
    return new_path
