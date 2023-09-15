import sys
import os
import subprocess
import time
import shutil

def banner(__S, fmt = ""):
    print(f"{fmt}{'='*(len(__S)+2)}")
    print(f" {__S} ")
    print(f"{'='*(len(__S)+2)}\033[0m")

######################################
#              OPTIONS               #
######################################

color = True
if "--nocolor" in sys.argv or "-nc" in sys.argv:
    sys.argv.remove("--nocolor") if "--nocolor" in sys.argv else sys.argv.remove("-nc")
    color = ""

loud = False
if "-v" in sys.argv:
    loud = sys.argv.count("-v")
    while "-v" in sys.argv:
        sys.argv.remove("-v")

output = None
if "-o" in sys.argv or "--output" in sys.argv:
    ind = sys.argv.index("-o") if "-o" in sys.argv else sys.argv.index("--output")
    output = open(sys.argv.pop(ind + 1), "w")
    sys.argv.remove("-o") if "-o" in sys.argv else sys.argv.remove("--output")
    color = ""


def dprint(*args, **kwargs):
    print(*args, **kwargs, file=output or sys.stdout)


class bcolors:
    HEADER = color and "\033[95m"
    OKBLUE = color and "\033[94m"
    OKCYAN = color and "\033[96m"
    OKGREEN = color and "\033[92m"
    WARNING = color and "\033[93m"
    BLACK = color and "\033[30m"
    FAIL = color and "\033[91m"
    ENDC = color and "\033[0m"
    BOLD = color and "\033[1m"
    UNDERLINE = color and "\033[4m"
    RED_BACK = color and "\033[41m"
    GREEN_BACK = color and "\033[42m"

for i, arg in enumerate(sys.argv):
    if "obstacleChess.py" in arg:
        banner("obstacleChess.py should not be in the arguments", bcolors.WARNING)
        sys.argv.pop(i)
        exit(1)

######################################
#             FUNCTIONS              #
######################################


def clean_and_exit(n):
    shutil.rmtree(tmp_loc)
    if output:
        output.close()
    sys.exit(n)


def lzip(*args, set_l=None, default=None):
    set_l = set_l or max(map(len, args))

    if default is None:
        _default = lambda x: None
    elif callable(default):
        _default = default
    elif isinstance(default, (tuple, list)):
        _default = lambda x: default[x % set_l]
    else:
        _default = lambda x: default

    return [
        tuple(a[i] if i < len(a) else _default(i) for a in args) for i in range(set_l)
    ]


def print_ex_v_fd(ex: str, fd: str):
    lines: list = []
    for e, f in lzip(ex.split("\n"), fd.split("\n"), default=""):
        ex_line = f"{bcolors.OKGREEN}"
        fd_line = f"{bcolors.OKGREEN}"
        error = False
        for e_char, f_char in lzip(e, f, set_l=32, default=" "):
            if e_char == f_char == " ":
                ex_line += " "
                fd_line += " "
            else:
                if e_char == f_char:
                    ex_line += f"{bcolors.BLACK + bcolors.GREEN_BACK}"
                    fd_line += f"{bcolors.BLACK + bcolors.GREEN_BACK}"
                else:
                    ex_line += f"{bcolors.BLACK + bcolors.RED_BACK}"
                    fd_line += f"{bcolors.BLACK + bcolors.RED_BACK}"
                    error = True
                ex_line += f"{e_char}{bcolors.ENDC}"
                fd_line += f"{f_char}{bcolors.ENDC}"
        lines.append(
            f"| {ex_line}{bcolors.ENDC}"
            + (" >> " if error else " || ")
            + f"{fd_line}{bcolors.ENDC} |"
        )
    dprint(f"|{' Expected ':-^34}||{' Found ':-^34}|")
    dprint("\n".join(lines))
    dprint(f"|{' Expected ':-^34}||{' Found ':-^34}|")
    dprint()

######################################
#              HEADER                #
######################################

if "obstacleChess.py" not in os.listdir():
    banner("obstacleChess.py not found in current directory", bcolors.FAIL)
    clean_and_exit(1)

tmp_loc = os.path.join(os.getcwd(), "tmp")
os.makedirs(tmp_loc, exist_ok=True)

py_file = os.path.join(os.getcwd(), "obstacleChess.py")

print(f"{bcolors.OKCYAN}Obstacle Chess Tester v2{bcolors.ENDC}")
print(f"{bcolors.OKCYAN}========================{bcolors.ENDC}")
print()
if len(sys.argv) < 2 or "-h" in sys.argv or "--help" in sys.argv:
    print("Usage: python3 test.py [options] <testcase folder> [<testcase folder> ...]")
    print()
    print("Options:")
    print("    -v [-v]          | verbose mode, '-v' for summary, '-v -v' for summary and comparisons")
    print("    <testcase folder>    | folder(s) to search for testcase folders in")
    print("    -nc|--nocolor        | disable color output (use if colors are not supported on your terminal)")
    print("    -h|--help            | show this help message")
    print("    -o|--output <file>   | output the results to a file instead of stdout")
    print()
    print(f"The following should be purple: {bcolors.HEADER}purple{bcolors.ENDC}")
    print("If not, your terminal does not support colors, and you should use the --nocolor option.")
    print()
    print(f"{bcolors.OKCYAN}========================{bcolors.ENDC}")
    print()
    print(
        "The tester will search for testcase folders in the given folders, and run the tests in them."
    )
    print()
    print(
        "Testcases are folders containing the following files (from the format supplied by markers):"
    )
    print(" -: initial.board        | the initial board state")
    print(" -: moves.game           | the moves to be played")
    print(" -: stdout.output        | the expected stdout output")
    print("And either of the following files:")
    print(
        " -: output.board         | the expected board state after the moves have been played (for positive testcases)"
    )
    print(
        " -: stderr.output        | the expected stderr output (for negative testcases)"
    )
    print()
    print(f"{bcolors.OKCYAN}========================{bcolors.ENDC}")
    print()
    clean_and_exit(0)
else:
    print(f"CWD:            {os.getcwd()}")
    print(f"Python Version: {sys.version}")
    print(f"Arguments:      {'|'.join(sys.argv[1:])}")
    print(f"Tmp folder:     {tmp_loc}")
    if output: print(f"Output file:    {output.name}")
    print()
    print(f"{bcolors.OKCYAN}========================{bcolors.ENDC}")
    print()

######################################
#         TESTCASE DISCOVERY         #
######################################

print(f"{bcolors.OKCYAN}Searching for testcases...{bcolors.ENDC}")
search_folders = sys.argv[1:]
testcases = {}
for folder in search_folders:
    if not os.path.exists(folder):
        if loud >= 1:
            print(f" -: {bcolors.WARNING}Folder {folder} does not exist!{bcolors.ENDC}")
    elif os.path.isdir(folder):
        for subfolder in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, subfolder)):
                testcases[subfolder] = os.path.join(folder, subfolder)
    else:
        print(f"{bcolors.WARNING}Path '{folder}' is not a folder!{bcolors.ENDC}")
print()

######################################
#        TESTCASE VALIDATION         #
######################################

if not testcases:
    print(f"{bcolors.FAIL}No testcases found in supplied folders{bcolors.ENDC}")
    clean_and_exit(1)
else:
    broken = 0
    if loud >= 1:
        print(f"{bcolors.OKCYAN}Found {len(testcases)} testcases.{bcolors.ENDC}")
    for testcase_name, location in list(testcases.items()):
        testcase_name_color = (
            bcolors.OKGREEN
            if (
                valid := all(
                    [
                        os.path.exists(os.path.join(location, "moves.game")),
                        any(
                            [
                                os.path.exists(os.path.join(location, "output.board")),
                                os.path.exists(os.path.join(location, "stderr.output")),
                            ]
                        ),
                        os.path.exists(os.path.join(location, "initial.board")),
                        os.path.exists(os.path.join(location, "stdout.output")),
                    ]
                )
            )
            else bcolors.FAIL
        )
        annotation = location if valid else "Testcase not valid"
        if loud >= 2 or not valid:
            print(
                f"  -: {testcase_name_color}{testcase_name}{bcolors.ENDC} ".ljust(
                    50, "-"
                )
                + f"| {annotation}"
            )
        if not valid:
            broken += 1
            del testcases[testcase_name]
    if loud >= 1 and broken:
        print(f"{bcolors.WARNING}Found {broken} invalid testcases{bcolors.ENDC}")
    print()

######################################
#              TESTING               #
######################################

if not testcases:
    print(f"{bcolors.FAIL}No valid testcases found{bcolors.ENDC}")
    clean_and_exit(1)
else:
    pad = len(str(len(testcases)))
    print(
        f"{bcolors.UNDERLINE + bcolors.OKCYAN}Running {len(testcases)} testcases...{bcolors.ENDC}"
    )
    print()
    if loud >= 1 or output:
        dprint(f" {'TEST':^{pad}} | RESULT  | REASON     | TIME  | NAME ")
        dprint(
            "-" * (max(pad, 4) + 2)
            + "+---------+------------+-------+-------------------------------"
        )

    for i, (name, location) in enumerate(testcases.items()):
        if loud >= 1 and not output:
            print(f" {str(i+1): >{max(pad,2)}}/{len(testcases)} | {bcolors.BOLD + bcolors.HEADER}RUNNING{bcolors.ENDC} | {'-'*10} | ----- | {bcolors.OKCYAN}{name.rstrip().ljust(50)}{bcolors.ENDC} \r",end="")
        fail = False
        start = time.time()
        proc = subprocess.Popen(
            [
                sys.executable,
                "-E",
                py_file,
                "initial.board",
                os.path.join(tmp_loc, f"output_{name}.tmp"),
                "moves.game",
            ],
            cwd=location,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        stdout = ""
        stderr = ""
        fail = []
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
            ret = 1
            fail += ["timeout"]
            delta = time.time() - start
        else:
            delta = time.time() - start
            ret = proc.returncode
            
            stdout = "" if not proc.stdout else proc.stdout.read()# sourcery skip: swap-if-expression
            stderr = "" if not proc.stderr else proc.stderr.read()# sourcery skip: swap-if-expression
            
            if os.path.exists(os.path.join(location, "stdout.output")):
                with open(os.path.join(location, "stdout.output"), "r") as ex_out:
                    if stdout.rstrip() != ex_out.read().rstrip():
                        fail += ["stdout"]
            elif stdout:
                fail += ["stdout"]
                        
            if os.path.exists(os.path.join(location, "stderr.output")):
                with open(os.path.join(location, "stderr.output"), "r") as ex_err:
                    if stderr.rstrip() != ex_err.read().rstrip():
                        fail += ["stderr"]
            elif stderr:
                    fail += ["stderr"]
                        
            if os.path.exists(
                os.path.join(location, "output.board")
            ) and os.path.exists(os.path.join(tmp_loc, f"output_{name}.tmp")):
                with open(os.path.join(location, "output.board"), "r") as ex_out, open(
                    os.path.join(tmp_loc, f"output_{name}.tmp"), "r"
                ) as py_out:
                    for k, (sh_line, py_line) in enumerate(
                        zip(ex_out.readlines(), py_out.readlines())
                    ):
                        if k < 8 and sh_line != py_line:
                            fail += ["board"]
                            break
                        elif k >= 8 and sh_line.strip() != py_line.strip():
                            fail += ["status"]
                            break

        anno_col = bcolors.FAIL if ret or fail else bcolors.OKGREEN
        testcases[name] = (ret, fail, delta)
        if loud >= 1 or output:
            dprint(
                f" {str(i+1):>{max(pad,2)}}/{len(testcases)} | {bcolors.BOLD + anno_col}{'FAIL' if ret or fail else 'PASS'}{bcolors.ENDC}    | {(fail[0] if len(fail) < 2 else 'various') if fail else 'passed':<10} | {delta:.2f}s | {bcolors.OKCYAN}{name.ljust(50)}{bcolors.ENDC} "
            )

        if (fail or ret) and loud >= 2:
            if "timeout" in fail:
                dprint(f"{bcolors.FAIL}Testcase {name!r} timed out{bcolors.ENDC}")

            if "board" in fail or "status" in fail:
                dprint(f"{bcolors.FAIL}output board does not match{bcolors.ENDC}")
                with open(os.path.join(location, "output.board"), "r") as ex_out, open(
                    os.path.join(tmp_loc, f"output_{name}.tmp"), "r"
                ) as fd_out:
                    ex = ex_out.read().rstrip()
                    fd = fd_out.read().rstrip()
                    print_ex_v_fd(ex, fd)
                    

            if "stderr" in fail or ret:
                dprint(f"{bcolors.FAIL}stderr does not match{bcolors.ENDC}")
                try:
                    with open(os.path.join(location, "stderr.output"), "r") as ex_out:
                        print_ex_v_fd(
                            ex_out.read().rstrip(), stderr.rstrip()
                        )
                except FileNotFoundError:
                    if ret:
                        by_lines = stderr.split("\n")
                        dprint("\n".join(([by_lines[0]] + by_lines[-4:])))
                    else:
                        print_ex_v_fd("", stderr.rstrip())

            if "stdout" in fail:
                dprint(f"{bcolors.FAIL}stdout does not match{bcolors.ENDC}")
                try:
                    with open(os.path.join(location, "stdout.output"), "r") as ex_out:
                        print_ex_v_fd(
                            ex_out.read().rstrip(), stdout.rstrip()
                        )
                except FileNotFoundError:
                    dprint(stdout)

######################################
#              SUMMARY               #
######################################

times = [delta for ret, fail, delta in testcases.values()]
errors = [
    *[
        len([1 for ret, fail, delta in testcases.values() if any((e in fail) for e in err)])
        for err in [["board", "status"], ["stderr"], ["stdout"]]
    ],
    len([1 for ret, fail, delta in testcases.values() if ret]),
]
dprint()
dprint(f"{bcolors.OKCYAN}TIME{bcolors.ENDC}   | {sum(times):.3f}s")
dprint(
    f"{bcolors.OKGREEN}PASSED{bcolors.ENDC} | {len([1 for ret, fail, delta in testcases.values() if ret == 0 and not fail])}"
)
dprint(
    f"{bcolors.FAIL}FAILED{bcolors.ENDC} | {len([1 for ret, fail, delta in testcases.values() if ret != 0 or fail])}"
)
dprint()
if any(stat > 0 for stat in errors):
    dprint("|----------------+----------------+----------------+----------------|")
    dprint(
        f"| {bcolors.WARNING}Board errors{bcolors.ENDC}   | {bcolors.WARNING}Stderr errors{bcolors.ENDC}  | {bcolors.WARNING}Stdout errors{bcolors.ENDC}  | {bcolors.WARNING}Program errors{bcolors.ENDC} |"
    )
    dprint("|----------------+----------------+----------------+----------------|")
    dprint(
        f"| {bcolors.WARNING}"
        + f"{bcolors.ENDC} | ".join(
            [
                (bcolors.OKGREEN if stat == 0 else bcolors.FAIL) + f"{stat}".center(14)
                for stat in errors
            ]
        )
        + f"{bcolors.ENDC} |"
    )
    dprint("|----------------+----------------+----------------+----------------|")
    dprint()
    banner("Done", bcolors.OKCYAN)
clean_and_exit(0)
