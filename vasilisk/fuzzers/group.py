import logging
import os
import subprocess
import uuid

from datetime import datetime

from coverage.groups import recorder

from .base import BaseFuzzer


class GroupFuzzer(BaseFuzzer):
    def __init__(self, threads, d8, crashes, tests, debug):
        self.logger = logging.getLogger(__name__)

        self.d8 = d8
        self.crashes = crashes
        self.tests = tests
        self.debug = debug

        coverage_dir = os.path.join('/dev/shm', 'vasilisk_coverage')
        if not os.path.exists(coverage_dir):
            self.logger.info('creating coverage dir')
            os.makedirs(coverage_dir)

        self.coverage_paths = []
        for thread in range(threads):
            coverage_path = os.path.join(
                coverage_dir, 'thread-{}'.format(thread)
            )
            self.coverage_paths.append(coverage_path)

            if not os.path.exists(coverage_path):
                self.logger.info('creating thread specific coverage dir')
                os.makedirs(coverage_path)

        self.coverage = recorder.CoverageRecorder()

    def execute(self, test_case, thread):
        options = ['--allow-natives-syntax', '--trace-turbo',
                   '--trace-turbo-path', self.coverage_paths[thread], '-e']

        cmd = ' '.join([self.d8] + options + [test_case])
        try:
            return subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            if int(e.returncode) == 1:
                return 'Syntax Error'
            self.logger.error(e)
            return None

    def fuzz(self, test_case, thread):
        unique_id = None
        id, grammar = test_case

        output = self.execute(grammar, thread)

        status = self.validate(output)
        if status == 1:
            if unique_id is None:
                curr_time = datetime.now().strftime('%Y.%m.%d-%H:%M:%S')
                unique_id = str(uuid.uuid4()) + '_' + curr_time

            self.commit_test(grammar, unique_id)
            self.coverage.found(id)
        elif status == 0:
            self.coverage.record(id, grammar, self.coverage_paths[thread])
        else:
            self.coverage.invalid(id)

    def validate(self, output):
        if output is 'Syntax Error':
            return -1
        if output is not None:
            return 0
        return 1
