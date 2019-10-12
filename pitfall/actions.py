# Copyright 2019 Ali (@bincyber)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import exceptions
from . import utils
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Union
import json
import re
import subprocess


def print_verbose_output(args: list, stdout: str, stderr: str):
    print(f'$ {" ".join(args)}\n', stdout)

    if stderr:
        print(stderr)


@dataclass(frozen=True)
class PulumiStep:
    op: str
    urn: str
    parent: str
    provider: str
    new_state: dict
    old_state: dict
    detailed_diff: dict
    diff_reasons: list

    @property
    def old_state_type(self) -> Union[str, None]:
        return self.old_state.get("type", None)

    @property
    def old_state_inputs(self) -> dict:
        return self.old_state.get("inputs", {})

    @property
    def old_state_outputs(self) -> dict:
        return self.old_state.get("outputs", {})

    @property
    def new_state_type(self) -> Union[str, None]:
        return self.new_state.get("type", None)

    @property
    def new_state_inputs(self) -> dict:
        return self.new_state.get("inputs", {})

    @property
    def new_state_outputs(self) -> dict:
        return self.new_state.get("outputs", {})


class PulumiAction(ABC):
    def __init__(self, verbose=False):
        self.verbose = verbose

    @abstractmethod
    def execute(self):  # pragma: no cover
        pass

    @property
    def stdout(self) -> str:
        return self._stdout

    @property
    def stderr(self) -> str:
        return self._stderr


class PulumiPreview(PulumiAction):
    def execute(self) -> subprocess.CompletedProcess:
        pulumi_binary = utils.find_pulumi_binary()
        cmd           = [pulumi_binary, 'preview', '--non-interactive', '--json']

        process = subprocess.run(cmd, capture_output=True)

        self._stdout = utils.decode_utf8(process.stdout)
        self._stderr = utils.decode_utf8(process.stderr)

        if process.returncode != 0:
            err = self._stdout
            if len(err) == 0:
                err = self._stderr
            raise exceptions.PulumiPreviewExecError(err)

        if self.verbose:
            print_verbose_output(args=process.args, stdout=self._stdout, stderr=self._stderr)

        return process

    @property
    def stdout(self) -> dict:
        return json.loads(self._stdout)

    @property
    def config(self) -> dict:
        return self.stdout["config"]

    @property
    def steps(self) -> List[PulumiStep]:
        steps = []

        preview_steps = self.stdout.get("steps", [])

        regex = re.compile('pulumi:.+:.+')

        for i in preview_steps:
            step_type = i["newState"]["type"]
            if regex.match(step_type):
                continue

            pulumi_step = PulumiStep(
                op=i["op"],
                urn=i["urn"],
                parent=i.get("parent", None),
                provider=i.get("provider", None),
                new_state=i["newState"],
                old_state=i.get("oldState", {}),
                detailed_diff=i.get("detailedDiff", {}),
                diff_reasons=i.get("diffReasons", [])
            )
            steps.append(pulumi_step)
        return steps

    @property
    def diagnostics(self) -> list:
        return self.stdout.get("diagnostics", [])

    @property
    def create(self) -> int:
        return self.stdout["changeSummary"]["create"]

    @property
    def same(self) -> int:
        return self.stdout["changeSummary"]["same"]

    @property
    def update(self) -> int:
        return self.stdout["changeSummary"]["update"]

    @property
    def delete(self) -> int:
        return self.stdout["changeSummary"]["delete"]


class PulumiUp(PulumiAction):
    def execute(self, expect_no_changes=False) -> subprocess.CompletedProcess:
        pulumi_binary = utils.find_pulumi_binary()
        cmd           = [pulumi_binary, 'up', '--non-interactive', '--skip-preview']  # TODO: enable json output with "--json"

        if expect_no_changes:
            cmd.append('--expect-no-changes')

        process = subprocess.run(cmd, capture_output=True)

        self._stdout = utils.decode_utf8(process.stdout)
        self._stderr = utils.decode_utf8(process.stderr)

        if process.returncode != 0:
            err = self._stdout
            if len(err) == 0:
                err = self._stderr
            raise exceptions.PulumiUpExecError(err)

        if self.verbose:
            print_verbose_output(args=process.args, stdout=self.stdout, stderr=self.stderr)

        return process


class PulumiDestroy(PulumiAction):
    def execute(self) -> subprocess.CompletedProcess:
        pulumi_binary = utils.find_pulumi_binary()
        cmd           = [pulumi_binary, 'destroy', '--non-interactive', '--skip-preview']  # TODO: enable json output with "--json"

        process = subprocess.run(cmd, capture_output=True)

        self._stdout = utils.decode_utf8(process.stdout)
        self._stderr = utils.decode_utf8(process.stderr)

        if process.returncode != 0:
            err = self._stdout
            if len(err) == 0:
                err = self._stderr
            raise exceptions.PulumiDestroyExecError(err)

        if self.verbose:
            print_verbose_output(args=process.args, stdout=self.stdout, stderr=self.stderr)

        return process
