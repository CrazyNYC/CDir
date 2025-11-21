# test_py_CDir.py
# import re
import os
import subprocess
import shlex

# used for hint-typing
import pytest
from pytest_benchmark.plugin import BenchmarkFixture
from _pytest.fixtures import FixtureRequest

# from argparse import Namespace

# import sys
# from pymediainfo import MediaInfo
from graphics.graphics_ops import BColors

from common_tools.common_tools import print_benchmark
from common_tools.common_tools import py_test_run_guts

# from io import StringIO
# TODO: need to create py_test object to be used in houskeep and mm32, initially.


def run_match_001(benchmark: BenchmarkFixture,
                  args: str,
                  expects_custom: list[str],
                  unexpects_custom: list[str]) -> subprocess.CompletedProcess:
    # Set up any required environment variables
    # Define your command-line arguments here
    # shlex.split() removes one layer of backslashes, so, we'll add a layer
    #   to counter-effect that
    args = args.replace('\\', '\\\\')
    # args_lcl [f'{str_2use}'] + shlex.split(args)  # respects quoted strings
    args_lcl = shlex.split(args)  # respects quoted strings
    result = subprocess.run(
        ['py.exe', 'CDir.py'] + args_lcl,
        # ['mmu.bat'] + args_lcl,
        capture_output=True,
        bufsize=4096,  # block-buffered
        encoding='utf-8',
        text=True
    )

    unexpectations = [
        r"There was an error processing benchmark data.",
        r'There was an error somewhere.  Please check traceback()',
        r'Unable to locate --rerun file!',
        r'Exception Type: ',
        r'Exception Message:',
        r'Traceback Details:',
        r'Failed to retrieve page (response code):',
        r'Failed to retrieve IMDb Full Credits page (',
        r'Unable to locate Cast after',
        r'Failed to retrieve main page!',
        r'Failed to find metadata!',
        r'Unable to locate Dirs/Prods/Writers/Actors after',
        r'Error opening file : ',
        r'OMDB Error for ',
        r'Error loading OMDB!',
        r'Error downloading image:',
        r'Error saving image:',
        r'ERROR: ',
        r'Maximum number of errors (--set-err-max ',
        r'Failed to fetch data.',
        r'Unicode Error',
        r'CDIR oops!',
        r'Failed to retrieve page/cache'
    ]

    expectations = [
        r"Total Files Listed:",
        r"File(s)",
        r"Dir(s)",
        r"Reading directories/files, please wait...",
        r"Volume in drive",
        r"Volume Serial Number is"
    ]

    py_test_run_guts(p_expecteds=expectations,
             p_unexpecteds=unexpectations,
             p_cust_expecteds=expects_custom,
             p_cust_unexpecteds=unexpects_custom,
             p_result=result,
             p_args=args_lcl)

    return result

@pytest.mark.parametrize("args, expected, unexpected", [
    (
        r'c:\windows\system32\*.ini c:\windows\system32\*.exe /s',
        (  # 1
                r"tcpmon.ini<<.*>>^^(AppXhk4des8gf2xat3wtyzc5q06ny78jhkqx=Notepad)",
                r'winver.exe<<.*>>..(exefile="%1" %*)'
        ),
        (
                r"Error",
                r"Error"
        )  # test of unexpecteds
    )

])
def test_match_001(benchmark:   BenchmarkFixture,
                   request:     FixtureRequest,
                   args:        str,
                   expected:    list[str],
                   unexpected:  list[str]) -> None:
    # setup for color
    co = BColors(False)

    result = benchmark(run_match_001, request, args, expected, unexpected)

    # Accessing benchmark results directly
    assert result.returncode == 0

    # Print detailed benchmark results
    print_benchmark(benchmark, request, co, result, 'baseline_1st.json')

@pytest.fixture(scope="session", autouse=True)
def set_timezone():
    os.environ['TZ'] = 'America/New_York'  # Set the timezone to GMT-5 (Eastern Time)
    # time.tzset()  # Apply the timezone (only needed on Unix-like systems)

# TODO: Add routines to use bat file as well (and write bat file)
# TODO: make sure we're using more 'off' args in rerun-merge* parms, title-id,

