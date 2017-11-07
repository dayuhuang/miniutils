import functools
import inspect
import pickle
import struct
import subprocess as sp
import os
import textwrap
import re


# TODO: Use fd's besides stdin and stdout, so that you don't mess with code that reads or writes to those streams
class MakePython2():
    pickle_protocol = 2
    template = os.path.join(*(list(os.path.split(__file__))[:-1] + ['py2_template.py']))

    def __init__(self, function=None, *, imports=None, global_values=None, copy_function_body=True,
                 python2_path='python2'):
        """

        :param function:
        :param imports:
        :param global_values:
        :param copy_function_body:
        :param python2_path:
        """
        self.imports = imports or []
        self.globals = global_values or {}
        self.copy_function_body = copy_function_body
        self.python2_path = python2_path
        self.proc = None

        valid_name = re.compile(r'^[\w.]+$', re.UNICODE)
        if isinstance(self.imports, dict):
            self.imports = list(self.imports.items())
        for i, imp in enumerate(self.imports):
            if isinstance(imp, str):
                self.imports[i] = (imp,)
            elif isinstance(imp, (tuple, list)):
                if len(imp) not in [1, 2]:
                    raise ValueError("Imports must be given as 'name', ('name',), or ('pkg', 'name')")
            if not all(isinstance(n, str) and valid_name.match(n) for n in imp):
                raise ValueError("Invalid import name: 'import {}{}'"
                                 .format(imp[0], 'as {}'.format(imp[1]) if len(imp) == 2 else ''))

        if function:
            self(function)

    def _write_pkl(self, obj):
        data = pickle.dumps(obj, protocol=MakePython2.pickle_protocol)
        self.proc.stdin.write(struct.pack('@I', len(data)))
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def _read_pkl(self):
        outp_length = int(struct.unpack('@I', self.proc.stdout.read(4))[0])
        return pickle.loads(self.proc.stdout.read(outp_length))

    def _wrapped_function(self, *args, **kwargs):
        self._write_pkl((args, kwargs))
        success, result = self._read_pkl()
        if success:
            return result
        else:
            raise RuntimeError(result)

    @property
    def function(self):
        return self._wrapped_function

    def __call__(self, function):
        if callable(function):
            function_code = textwrap.dedent(inspect.getsource(function)) if self.copy_function_body else ''
            function_code = '\n'.join(line for line in function_code.split('\n') if not line.startswith('@MakePython2'))
            function_name = function.__name__
        elif isinstance(function, str):
            function_code = ''
            function_name = function


        self.proc = sp.Popen([self.python2_path, MakePython2.template], executable=self.python2_path,
                             stdin=sp.PIPE, stdout=sp.PIPE)
        self._write_pkl((self.imports, self.globals, function_name, function_code))

        return self._wrapped_function

    def __del__(self):
        if self.proc:
            self._write_pkl(None)
            self.proc.stdin.close()
            self.proc.stdout.close()
            self.proc.terminate()
            self.proc.wait()