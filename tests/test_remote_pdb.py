from __future__ import print_function

import unittest
import os
import sys
import re
import logging
import socket
from contextlib import closing

from process_tests import TestProcess, ProcessTestCase, setup_coverage

from remote_pdb import set_trace

TIMEOUT = int(os.getenv('REMOTE_PDB_TEST_TIMEOUT', 10))

class RedisLockTestCase(ProcessTestCase):
    def test_simple(self):
        with TestProcess(sys.executable, __file__, 'daemon', 'test_simple') as proc:
            with self.dump_on_error(proc.read):
                self.wait_for_strings(proc.read, TIMEOUT,
                    '{a1}',
                    '{b1}',
                    'RemotePdb session open at ',
                )
                host, port = re.findall("RemotePdb session open at (.+):(.+),", proc.read())[0]
                with closing(socket.create_connection((host, int(port)), timeout=TIMEOUT)) as conn:
                    fh = conn.makefile('rw')
                    self.wait_for_strings(proc.read, TIMEOUT, 'accepted connection from')
                    fh.readline()
                    self.assertEqual("-> print('{b2}')", fh.readline().strip())
                    fh.write('quit\r\n')
                self.wait_for_strings(proc.read, TIMEOUT,
                    'Restoring streams',
                    'DIED.',
                )

    def test_simple_break(self):
        with TestProcess(sys.executable, __file__, 'daemon', 'test_simple') as proc:
            with self.dump_on_error(proc.read):
                self.wait_for_strings(proc.read, TIMEOUT,
                    '{a1}',
                    '{b1}',
                    'RemotePdb session open at ',
                )
                host, port = re.findall("RemotePdb session open at (.+):(.+),", proc.read())[0]
                with closing(socket.create_connection((host, int(port)), timeout=TIMEOUT)) as conn:
                    fh = conn.makefile('rw')
                    self.wait_for_strings(proc.read, TIMEOUT, 'accepted connection from')
                    fh.readline()
                    self.assertEqual("-> print('{b2}')", fh.readline().strip())
                    fh.write('break func_a\r\n')
                    fh.write('continue\r\n')
                    fh.readline()
                    self.assertEqual("-> print('{a2}')", fh.readline().strip())
                    fh.write('continue\n')
                    self.assertEqual("(Pdb)", fh.readline().strip())

                self.wait_for_strings(proc.read, TIMEOUT,
                    'Restoring streams',
                    'DIED.',
                )

def func_b():
    print('{b1}')
    set_trace()
    print('{b2}')

def func_a(block=lambda _: None):
    print('{a1}')
    func_b()
    print('{a2}')
    x = block('{a3} ?')
    print('{=> %s}' % x)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'daemon':
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(process)d %(asctime)s,%(msecs)05d %(name)s %(levelname)s %(message)s',
            datefmt="%x~%X"
        )
        test_name = sys.argv[2]

        setup_coverage()

        if test_name == 'test_simple':
            func_a()
        elif test_name == 'test_?':
            pass
        else:
            raise RuntimeError('Invalid test spec %r.' % test_name)
        logging.info('DIED.')
    else:
        unittest.main()