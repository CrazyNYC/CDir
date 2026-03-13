# from argparse import ArgumentParser, Namespace
# from logging import exception
# from typing import Any
# from functools import lru_cache

# import sys, copy, os, re, pickle, time, subprocess, msvcrt, io
# import sys, gc,
import os, re, sys
from msvcrt import getch, kbhit
# from typing import Optional

from graphics.graphics_ops import BColors  #, LineDrawingCharacters, ColoredHelpFormatter, ColoredPaginatedArgumentParser
from common_tools.common_tools import strip_ascii, begin_timing, end_timing, print_except

co = BColors(False)

# denote assoc. app src
api_srcd = "a]"  # data srced from API calls
registry_srcd = "r]"  # data srced from registry lookup
dism_srcd = "d]"  # data srced from dism (from Windows initial install)

ext_cache = {}
ext_cache_ctr = {}
ext_cache_size = {}
file_name_start = 0  # just a default, gets reset below

user_profile = os.environ.get("USERPROFILE").replace("C:","H:").replace(r"\\", r"\\\\") + "\\"
dir_env_var = os.environ.get("DIRCMD") or ""
assoc_file = rf'{user_profile}\DefaultAppAssociations.xml'
debug = False
show_ext_dtls=False
gflags = None

run_arr = sys.argv

wide_cols = -1
wide_col_width = -1
file_wide_format=False
# time_start = time.time()

# def safe_print(*args, **kwargs):
#     try:
#         print(*args, **kwargs)
#     except (BrokenPipeError, OSError):
#         # sys.exit(0)
#         pass

def main():
    global gflags
    global co
    import os, sys
    global user_profile, dir_env_var
    global file_name_start
    global show_ext_dtls
    global ext_cache, ext_cache_ctr, ext_cache_size
    global file_wide_format

    file_wide_format = False
    begin_timing()  # start timer

    os.system('')  # needed for subsequent ANSI color code rendering, especially in DOS Admin mode
    run_arr = sys.argv
    if file_wide_format: run_arr+=["*."]
    nocolor = False
    while any(flag.lower() in sys.argv for flag in (['/nocolor'])):
        nocolor = True
        sys.argv.remove('/nocolor')

    #  Are we going into DEBUG mode? (use /0 for debug)
    debug_flags = ('-0', '/0', '-1', '/1')  # that's a zero, not the letter 'o'
    debug = False
    for flag in debug_flags:
        if any(flag2 in sys.argv for flag2 in (['/1','-1'])):
            sys.argv.remove(flag)
            show_ext_dtls = True
            # sys.argv.remove('/1')
        elif flag in sys.argv:
            sys.argv.remove(flag)
            print(f"Debug is set to True {flag}")
            debug = True
        elif flag in dir_env_var:
            print(f"Debug is set to True {flag}")
            debug = True

    # if /reset is specified on the command-line
    reset = False
    if any(flag.lower() in sys.argv for flag in (['/reset'])):
        reset = True
        sys.argv.remove('/reset')

    # we setup, capture and potentially manipulate argparse and argv
    # dummy, gargs, orig_argv = parse_parms()
    # co.no_color(gargs.nocolor)

    co = BColors(nocolor)
    show_help = False
    pickle_dict = rf"{user_profile}cdir_cache.pkl.gz"

    # if we passed /reset
    if reset and os.path.exists(pickle_dict):
        os.remove(pickle_dict)

    #  load existing extension cache
    if os.path.exists(pickle_dict):
        import gzip
        with gzip.open(pickle_dict, 'rb') as f1:
            # pickle_data = pickle.load(f)
            import pickle
            pickle_data = pickle.load(f1)
            ext_cache = pickle_data['ext_cache']
            print(f"Pickle Data load = {pickle_data}") if debug else None
            print(f" \n"
                  f"{co.DIMWHITEFG}Loaded {co.BLDWHITEFG}{len(ext_cache):,}{co.DIMWHITEFG} "+
                  f"extensions from {co.BLDWHITEFG}{pickle_dict}{co.ENDC}") \
                if debug else None
            # print(f"Pickle Data load = {pickle_data}")  # if gargs_lcl.verbose else None

    if not os.path.exists(assoc_file):  # or refresh_assoc:
        # if we're already running w/elevated rights, then we justassoc  use current session
        #  if not, then we attempt to run in a powershell session using admin rights
        if not is_admin():
            # command_2use = ['dism']
            # parms_2use = ["/online", rf"/export-defaultappassociations:'{assoc_file}'"]
            print("Creating DISM file associations file (non-admin rights, so, we'll elevate using powershell)...")
            dism_args = f'/online /export-defaultappassociations:"{assoc_file}"'
            elevated_cmd = [
                "powershell",
                '-NoExit',
                "-Command",
                f"Start-Process dism -ArgumentList \'{dism_args}\' -Verb RunAs -Wait"

            ]
            subprocess.run(elevated_cmd)

        else:
            print("Creating DISM file associations file (admin rights, so, we'll use cmd.exe)...")
            command_2use = ['dism']
            parms_2use = ["/online", rf"/export-defaultappassociations:'{assoc_file}'"]
            subprocess.run(command_2use + parms_2use)

        if not os.path.exists(assoc_file):
            print(f"Unable to create DISM defaule associations file -> {assoc_file}... exiting!")
            exit()
        else:
            print(f"DISM extract file created -->  {assoc_file}") # if verbose else None

    # if a dir is specified and ends with '\' and is quoted, python mistakenly escapes the last quote,
    #  so, we strip the trailing backslashes to avoid
    # for i in range(1, len(sys.argv)-1):
    #     # sys.argv[i] = sys.argv[i][:-1] if sys.argv[i].endswith("\\") else sys.argv[i]
    #     sys.argv[i] = sys.argv[i].rstrip('\\')

    run_arr = ['dir']
    print(f"sys.argv before processing = {sys.argv}") if debug else None

    # if help requested (ignores any other parms)
    if any(flag.lower() in sys.argv for flag in ('-h', '/h', '/?', '-?')):
        run_arr += ['/?']
        show_help = True

    # if DOS filename (8.3) is specified on the command-line
    file_name_offset = 0
    if any((flag.lower() in sys.argv or flag in dir_env_var.lower()) for flag in ('/x', '/X')):
        file_name_offset += 13

    # if wide-format is specified on the command-line
    file_wide_format = False
    ok_2_get_metadata = True
    if any((flag.lower() in sys.argv or flag in dir_env_var.lower()) for flag in ('/w', '/W')):
        file_wide_format = True
        ok_2_get_metadata = False

    # if bare-format is specified on the command-line
    file_bare_format = False
    # ok_2_get_metadata = True
    if any((flag.lower() in sys.argv or flag in dir_env_var.lower()) for flag in ('/b', '/B')):
        file_bare_format = True
        ok_2_get_metadata = False

    # if order is specified on the command-line
    order_specified = False
    if any((flag.lower() in sys.argv or flag in dir_env_var.lower()) for flag in ('/o')):
        order_specified = True

    # if /coltypeapp is specified on the command-line
    #  we include extension associations column
    coltypeapp = False
    while any(flag.lower() in sys.argv for flag in (['/coltypeapp'])):
        coltypeapp = True
        sys.argv.remove('/coltypeapp')

    # if /nodetail is specified on the command-line
    no_detail = False
    while any(flag.lower() in sys.argv for flag in (['/nodetail'])):
        no_detail = True
        sys.argv.remove('/nodetail')

    while any(flag.lower() in sys.argv for flag in (['/detail'])):
        no_detail = False
        sys.argv.remove('/detail')

    # if /noextinfo is specified on the command-line
    #  we only color the filename, not the whole detail line
    no_ext_info_sum = False
    while any(flag.lower() in sys.argv for flag in (['/noextinfo'])):
        no_ext_info_sum = True
        sys.argv.remove('/noextinfo')

    # if /nocountsum is specified on the command-line
    #  we suppress file extensions by count summary
    no_count_sum = False
    while any(flag.lower() in sys.argv for flag in (['/nocountsum'])):
        no_count_sum = True
        sys.argv.remove('/nocountsum')

    while any(flag.lower() in sys.argv for flag in (['/countsum'])):
        no_count_sum = False
        sys.argv.remove('/countsum')

    # if /nosizesum is specified on the command-line
    #  we suppress file extensions by size summary
    no_size_sum = False
    while any(flag.lower() in sys.argv for flag in (['/nosizesum'])):
        no_size_sum = True
        sys.argv.remove('/nosizesum')

    while any(flag.lower() in sys.argv for flag in (['/sizesum'])):
        no_size_sum = False
        sys.argv.remove('/sizesum')

    # if /nodetail is specified on the command-line
    no_summary = False
    while any(flag.lower() in sys.argv for flag in (['/nosummary'])):
        no_summary = True
        no_count_sum = True
        no_size_sum = True
        no_ext_info_sum = True
        sys.argv.remove('/nosummary')

    # if /timer is specified on the command-line
    timer = False
    while any(flag.lower() in sys.argv for flag in (['/timer'])):
        timer = True
        sys.argv.remove('/timer')

    # if /notimer is specified on the command-line
    # timer = False
    while any(flag.lower() in sys.argv for flag in (['/notimer'])):
        timer = False
        sys.argv.remove('/notimer')

    # if /nocolorfileonly is specified on the command-line
    #  we color the whole detail line, not just the filename
    no_color_filename_only = False
    while any(flag.lower() in sys.argv for flag in (['/nocolorfileonly'])):
        no_color_filename_only = True
        sys.argv.remove('/nocolorfileonly')

    # if /quiet is passed, we try to be a little quieter
    #  we only color the filename, not the whole detail line
    verbose = True
    while any(flag.lower() in sys.argv for flag in (['/quiet'])):
        verbose = False
        sys.argv.remove('/quiet')

    # if /forcecache is specified on the command-line
    #  we update the ext cache whether there is an entry for that ext or not
    force_update_cache = False
    while any(flag.lower() in sys.argv for flag in (['/forcecache'])):
        force_update_cache = True
        sys.argv.remove('/forcecache')

    print(f"sys.argv after processing = {sys.argv}") if debug else None

    # certain switches reformat the screen thus that there is no convenient place for type/app col
    if any((flag.lower() in sys.argv or flag.lower() in dir_env_var.lower()) for flag in (['/w'])):
        coltypeapp = False

    # if /1 is specified on the command-line then show ext details
    #   every time a new ext is encountered
    show_ext_dtls = False

    # if any parms for DIR were passed then we pass-thru
    if len(sys.argv) > 1:
        run_arr += sys.argv[1:]

    if not order_specified:
        run_arr += ['/OGEN']  # 'G' needs to go first

    # the /p parm is ignored by DIR when using subprocess, so, we simulate pagination
    paginate = False
    i_page = 50
    if any(flag in sys.argv for flag in ('-p', '/p', '/P', '-P')):
        # run_arr += [' | more']
        paginate = True

    print(f"{co.BLDYELLOWFG} \n    Reading directories/files, please wait...{co.ENDC}") if not show_help else None
    print(sys.argv) if debug else None
    print(f"DIR cmd = {run_arr}") if debug else None
    # with open(p_file, "wt", encoding='utf-8') as dirtext:
    block_relative_dirs = True  # do not display '.' and '..' <DIR>s

    if not show_help:
        i = 0
        # lines = result.stdout.splitlines()
        # del result # memory cleanup
        # gc.collect()  # force garbage collect
        # print(f"{co.BLDYELLOWFG}\t...processing {len(lines):,} lines...\n") if len(lines) > 999 else None
        print(" ")
        if not file_wide_format: # and not file_bare_format:
            file_name_start = get_file_name_start()

        else:
            file_name_start = 0

        def replacer(match):
            min_dashes=1  # the minimum number of cashes before the arrow (if too large then moves size to the right)
            # parses DIR line
            prefix = match.group(1)  # everything up to AM/PM
            spaces = match.group(2)  # leading spaces
            number = match.group(3)  # the digits
            suffix = match.group(4)  # everything after
            return prefix + " " + co.DIMBLACKFG + ('-' * (max(len(spaces)-3,min_dashes))) + r"> " + co.DIMWHITEFG + number + suffix

        # import subprocess, sys, locale
        # encoding = locale.getpreferredencoding(False)
        proc = subprocess.Popen(
            run_arr,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # env=env,
            text=False  # RAW BYTES
        )

        import locale
        encoding = locale.getpreferredencoding(False)
        p_curr_dir = ""
        line = ""
        cleaned = ""
        for raw in proc.stdout:
            # print(f"DIR cmd = {run_arr}")  # if debug else None
            # line = ''.join(ch for ch in line if ch >= ' ')
            # line = line.rstrip("\n").rstrip("\r").rstrip("\n").rstrip("\r").strip()

            cleaned = raw.replace(b'\r', b'').replace(b'\n', b'')

            # line = cleaned.decode(encoding, errors='ignore')
            line = cleaned.decode(encoding, errors='replace')
            # line = cleaned.decode('utf-8', errors='ignore')
            # line = line.replace("\r", "").replace("\n", "")

            is_dir = False
            is_dir_name = False
            is_file = False
            p_filename = ""
            p_ext = ""
            # are we paging and are we at end-of-page
            if paginate and i % i_page == 0:
                print(f"{co.BLDMAGENTAFG}Press any key to continue (page {int(i/i_page)})... (Esc or Ctrl-C to exit){co.ENDC}")
                # keyboard.read_event()
                # if msvcrt.kbhit():
                key = getch()
                if key == b'\x1b':  # Esc key
                    print(f"{co.BLDREDFG}[Esc] key pressed. Exiting.{co.ENDC}")
                    break
                elif key == b'\x03':  # Ctrl-C keys
                    print(f"{co.BLDREDFG}[Ctrl-C] keys pressed. Exiting.{co.ENDC}")
                    break
                else:
                    print(f"{co.BLDGREENFG}[{key}] pressed.{co.ENDC}") if debug else None

            # any keypresses waiting in the buffer?
            elif kbhit():
                key = getch()
                if key == b'\x1b':  # Esc key
                    print(f"{co.BLDREDFG}[Esc] key pressed. Exiting.{co.ENDC}")
                    break
                elif key == b'\x03':  # Ctrl-C keys
                    print(f"{co.BLDREDFG}[Ctrl-C] keys pressed. Exiting.{co.ENDC}")
                    break
                # else:
                #     print(f"{co.BLDGREENFG}[{key}] pressed.{co.ENDC}") if debug else None

            line_lower = line.lower()
            prefix_line = ''

            if False:  # not block_relative_dirs:
                # if (line + " ").find(". ") > -1:
                if line.endswith("  ."):
                    print("line ended with '  .") if debug else None
                    print(f'(line+" ").find("  . " )  = {(line + " ").find("  . ")}') if debug else None
                    # file_name_start = max((line.strip() + " ").find("  . ") + 2,
                    #                       0) if file_name_start <= 1 else file_name_start
                    continue
                    # line += "\t"
                elif line.endswith("  .."):
                    print("line ended with '  ..") if debug else None
                    print(f'(line+" ").find("  .. ") = {(line + " ").find("  .. ")}') if debug else None
                    # line += "\t"
                    continue

            if any(ext in line for ext in ["<DIR>"]):
                is_dir = True
                # file_name_start = max((line.strip() + " ").find("  . ") + 2, 0) if file_name_start <= 1 else file_name_start

            # where on line does filename begin?
            # file_name_start = 43 if file_name_start == 0 else file_name_start
            # color for this filename exyension
            color2use = color_2use(p_line=line)
            # color for rest of detail info on filename line when not /nocolorfileonly
            color2use2 = co.DIMWHITEFG if not no_color_filename_only else color2use

            # directories (overrides any other color criteria)

            line = line.replace(f"Directory of", f"{co.BLDWHITEFG}Directory of{color2use}")
            line = line.replace(f"File Not Found", f"{co.BLDREDFG} \n\tFile Not Found{co.ENDC}")
            line = line.replace(f"The specified path is invalid.", f"{co.BLDREDFG} \n\tThe specified path is invalid.{co.ENDC}")

            if any(ext in line for ext in ["Directory of"]):
                is_dir_name = True
                # prefix_line = ''  # must be at least 1 char or will be set below
                p_curr_dir = strip_ascii(line).replace("Directory of ", "").strip()

            # handle attributes in color/hilite
            color_true = co.BLDWHITEFG
            color_false = co.DIMBLACKFG
            if any(ext in line for ext in ["<DIR>", "<JUNCTION>", "<SYMLINK>", "<SYMLINKD>", "<REPARSE>"]):
                is_dir = True
                if any(ext in line for ext in ["<JUNCTION>", "<SYMLINK>", "<SYMLINKD>", "<REPARSE>"]):
                    reparse = True
                else:
                    reparse = False

                prefix_line = (' '*len(f'-({i:>3})-> '))  # if not prefix_line else prefix_line
                # we get the file-type and app-to-use fr that ext.
                # p_filename, p_ext = os.path.splitext(line[file_name_start + file_name_offset:])
                p_filename, p_ext = os.path.splitext(line[file_name_start:])
                p_filename = p_filename.replace("\\","\\\\")
                p_size = line[(file_name_start - 15):file_name_start - 1].replace(",", "")
                attrs = get_file_attributes(f"{p_curr_dir}")
                line = line.strip()+""

                line += f"\t{color_false}"  # we'll start it off this way to reduce ANSI in the string
                for k, v in attrs.items():
                    if k == 'reparse':
                        line += f"{color_true}{k[0]}{color_false}" if str(v)[0].lower() == 't' or reparse else f"{k[0]}"

                    else:
                        line += f"{color_true}{k[0]}{color_false}" if str(v)[0].lower() == 't' else f"{k[0]}"
                        # line += f"{color_true}{k[0]}{color_false}" if str(v)[0].lower() == 't' else f"{color_false}{k[0]}"

                line += f"{co.ENDC}" if len(attrs.items()) > 0 else ""

            elif line_lower.startswith(("mon", "tue", "wed", "thu", "fri", "sat", "sun")):
                is_file = True
                i += 1
                # if we still haven't established the file name start position
                # file_name_start = line.rfind("(AM|PM)") + 21 if file_name_start <= 1 else file_name_start
                prefix_line = f'{co.DIMBLACKFG}-({co.DIMWHITEFG}{i:>3}{co.DIMBLACKFG})-> {color2use2}'

                print(line[file_name_start:]) if debug else None

                # we get the file-type and app-to-use fr that ext.
                # p_filename, p_ext = os.path.splitext(line[file_name_start + file_name_offset:])
                p_filename, p_ext = os.path.splitext(line[file_name_start:])
                p_filename = p_filename.replace("\\", "\\\\")
                # p_size = line[(file_name_start - 15):file_name_start - 1].replace(",", "")
                # ampm_found=line.rfind("(AM|PM)")
                ampm_found = max(line.rfind(" AM "), line.rfind(" PM "))
                # print(f"ampm_found={ampm_found}")
                # print(f"line={line}")
                p_size = line[(ampm_found + 4):(ampm_found + 21)] if ampm_found else 0
                # print(f"p_size={p_size}")
                # if entire line not color-coded, then files might be harder to follow left-to-right
                # So, this colors the filename
                line = re.sub(r'^(.*?\b(?:AM|PM))(\s+)(\d+)(.*)$', replacer, line) if not no_color_filename_only else line
                # print(f"{prefix_line}{line2}") if debug else None

                # metadata = get_metadata(p_ext, p_size, force_update_cache) if p_ext and ok_2_get_metadata else ""
                metadata = get_metadata(p_ext, p_size, is_dir, force_update_cache) if ok_2_get_metadata else ""

                if coltypeapp:
                    # print(f"p_size = '{p_size}'") if p_size else None
                    # print(f"line[file_name_start:] = '{line[file_name_start-15:file_name_start-1]}'") if line[file_name_start-15:] else None
                    print(f"metadata={metadata}") if metadata is not None and debug else None
                    # now, we'll add the type/app column
                    line += f"{format_line(metadata, line, color2use)}"
# ???
                # file_path = r"C:\Users\Edward\Documents\secret.txt"
                attrs = get_file_attributes(rf"{p_curr_dir}\{p_filename}{p_ext}")
                line = line.strip()+" "
                line += f"\t{color_false}" if len(attrs.items()) > 0 else ""
                for k, v in attrs.items():
                    line += f"{color_true}{k[0]}{color_false}" if str(v)[0].lower() == 't' else f"{k[0]}"

                line +=  f"{co.ENDC}" if len(attrs.items()) > 0 else ""

            elif any(ext in line for ext in ["File(s)", "Dir(s)"]):
                line = "\t" + line

            elif file_wide_format:
                line = wide_line(strip_ascii(line))

            else:
                prefix_line = '' if not prefix_line else prefix_line

            try:
                # p_filename, p_ext = os.path.splitext(strip_ascii(line)[file_name_start + file_name_offset:]) if not p_filename else (p_filename, p_ext)
                p_filename, p_ext = os.path.splitext(strip_ascii(line)[file_name_start:]) if not p_filename else (p_filename, p_ext)
                line_1 = f"{prefix_line}{line}"
                if not no_color_filename_only and p_filename and file_name_start > 1 and (is_file or is_dir):
                    line_1 = line_1.replace(f'{p_filename.replace("\\\\","\\")}{p_ext}',
                                    f'{color2use}{p_filename}{p_ext}')

                    if line_1 and len(prefix_line.strip()) == 0:
                        line_1 = f"{color2use2}{line_1.rstrip(co.ENDC)}{co.ENDC}"

                    elif line_1 and len(prefix_line.strip()) > 0:
                        line_1 = f"{line_1.rstrip(co.ENDC)}{co.ENDC}"

                # both Dir name and filename rows have leading color settings already, so, save a few bytes
                elif is_dir_name or len(prefix_line.strip()) > 0 or is_file:
                    if line_1:
                        line_1 = f"{line_1.rstrip(co.ENDC)}{co.ENDC}"

                else:
                    if line_1:
                        line_1 = f"{color2use}{line_1.rstrip(co.ENDC)}{co.ENDC}"

                # the space after the "else" i necessary because blank lines cause
                #  issues when processing output w/FOR /F loops
                print(line_1 if line_1 and len(line_1) > 0 else " ") if not no_detail else None
                # print("You got here 1")

#TODO treat SYMLINK as files (as per DIR in # File(s) totals)
            except UnicodeEncodeError as e:
                print_except(e, f"Unicode Error: {co.ENDC}")

            except Exception as e:
                print_except(e, "CDIR oops!!")
                raise e

        from common_tools.common_tools import print_dict

        # no sense in showing extension summary if less than 1 extensions encountered
        #  we check for ext_cache_ctr because we don't cache that, only the ext_cache
        #  with assoc, etc. info
        if ext_cache_ctr and len(ext_cache_ctr) > 0:

            print(f" \n{co.BLDYELLOWFG}All extensions encountered [{co.BLDGREENFG}{len(ext_cache_ctr)} "
                f"unique{co.BLDYELLOWFG}] are as follows:\n{co.ENDC}") \
                if not no_count_sum or not no_size_sum or not no_ext_info_sum else None
            if not no_ext_info_sum:

                s_print = print_dict(pass_filtered(ext_cache, ext_cache_ctr, 0),
                                     co, p_sorted=True, p_print=False, p_color=False)
                # color used for data-source designators
                color2use3 = f"{co.DIMWHITEFG}"
                # color for '=' equal-sign (seperates type from app type=app)
                color2use4 = f"{co.BLDREDFG}"
                # color for ttl file count
                color2use5 = f"{co.BLDYELLOWFG}"
                # alternate color for equal-sign if color2use is same as equal-sign color
                color2use6 = f"{co.DIMYELLOWFG}"
                # color for source designator(s)
                color2use7 = f"{co.BLDWHITEFG}"
                color2use8 = f"{co.WHITEFG}"
                s_print2 =  f"\t{color2use7}           Size     # Files     Ext.    Ext. Info - {color2use7}a]{color2use3} assoc/ftype, {color2use7}r]{color2use3} registry, {color2use7}d]{color2use3} dism install\n"
                s_print2 += f"\t{color2use2}       --------     -------     -----   --------------------------------------------------------\n"
                for ttl_line in s_print.splitlines():
                    ttl_line = ttl_line.strip()
                    ttl_ext = ttl_line[:max(ttl_line.find(":"),0)]
                    color2use2 = color_2use(p_ext=ttl_line[:max(ttl_line.find(":"),0)])
                    ttl_line = ttl_line.replace("=",
                                         f"{color2use4 if color2use2 not in (color2use4) else color2use6}={color2use2}")
                    ttl_line =  ttl_line.replace("/",
                                                f"{color2use4 if color2use4 not in (co.DIMWHITEFG, co.DIMBLACKFG) else co.WHITEFG}/{color2use2}")
                    ttl_line =  ttl_line.replace(": ",
                                                f"{color2use4 if color2use4 not in (co.DIMWHITEFG, co.DIMBLACKFG) else co.WHITEFG}:\t{color2use2}")
                    # color-code data-source designators
                    ttl_line = ttl_line.replace(f"{api_srcd}",
                                                f"{color2use7}{api_srcd}{color2use2}")
                    ttl_line = ttl_line.replace(f"{registry_srcd}",
                                                f"{color2use7}{registry_srcd}{color2use2}")
                    ttl_line = ttl_line.replace(f"{dism_srcd}",
                                                f"{color2use7}{dism_srcd}{color2use2}")

                    # ttl line file ct for ext
                    s_print2 += f"\t{color2use3}{ext_cache_size[ttl_ext]:>15,} -> ({ext_cache_ctr[ttl_ext]:>7,}) {color2use4}-> {color2use5}{ttl_line}{co.ENDC}\n"

                s_print2 = s_print2.rstrip('\n')
                # s_print = s_print2
                print(s_print2)

            # make group where multiple items might be listed after value
            # filter and group by value
            from collections import defaultdict
            groups_ctr  = defaultdict(list)
            groups_size = defaultdict(list)

            if ext_cache_ctr and len(ext_cache_ctr) > 1:
                # TTL count files by ext
                ttl_value = 0
                for key, value in sorted(ext_cache_ctr.items(), key=lambda item: item[1], reverse=True):
                    ttl_value += value
                    # this creates list of extension values (e.g. size, file count) the the extensions that have that value
                    groups_ctr[value].append(key)

                # TTL size files by ext
                ttl_size = 0
                for key, value in sorted(ext_cache_size.items(), key=lambda item: item[1], reverse=True):
                    ttl_size += value
                    groups_size[key].append(value)

                # this creates list of extensions and their value (e.g. size, file count)
                joined = ""
                comma_color = co.BLDREDFG
                ext_color = co.BLDWHITEFG
                arrow_color = co.DIMWHITEFG
                num_color = co.BLDYELLOWFG

                def get_short_size(p_size, p_decimals: int=1, p_width: int=5) -> str:
                    # p_decimals = 1
                    retval = ""
                    KiB = 1024
                    MiB = 1024 ** 2
                    GiB = 1024 ** 3
                    TiB = 1024 ** 4
                    PiB = 1024 ** 5

                    if p_size >= PiB:
                        retval = f"{p_size / PiB:>{p_width}.{p_decimals}f} PiB"
                    elif p_size >= TiB:
                        retval = f"{p_size / TiB:>{p_width}.{p_decimals}f} TiB"
                    elif p_size >= GiB:
                        retval = f"{p_size / GiB:>{p_width}.{p_decimals}f} GiB"
                    elif p_size >= MiB:
                        retval = f"{p_size / MiB:>{p_width}.{p_decimals}f} MiB"
                    elif p_size >= KiB:
                        retval = f"{p_size / KiB:>{p_width}.{p_decimals}f} KiB"
                    else:
                        retval = f"{p_size:>{p_width-1-p_decimals}} bytes"

                    return retval

                for ext, val in ext_cache_ctr.items():

                    # # there IS GROUING by value for size
                    # groups_ctr[val].append(ext)
                    # # there IS NO GROUING by value for size
                    # groups_size[ext].append(val)
                    parts = []
                    joined = ""

                    if not no_count_sum:
                        parts = []
                        # for every val (file count),list all keys (extensions) for that val
                        for val2 in sorted(groups_ctr.keys(), reverse=True):
                            # size2 = groups_size[val2]
                            exts = f"{comma_color},{ext_color} ".join(sorted(groups_ctr[val2]))
                            exts = wrap_at_nearest_space(exts, max_width=80, comma_color=comma_color)
                            parts.append(
                                f"\n\t{' '*6}{num_color}{val2:>9,} {arrow_color}-> {ext_color}{exts} {arrow_color}"
                                )

                        joined = ""
                        joined += (f" \n{co.BLDREDFG}Ext. by file count:\t\n "+" ".join(parts))  #if not no_count_sum else ""

                        # print ttl files w/ext
                        joined += (
                            f" \n\t{' '*6}{co.BLDWHITEFG}{'-' * 9}\n\t{' '*6}{num_color}{ttl_value:>9,} {co.DIMREDFG}->{co.BLDWHITEFG} Total file(s){co.ENDC}") \
                            # if not no_count_sum else ""

                    # print ttl unique extensions
                    # joined += (
                    #     f"\t\t\t     {co.BLDWHITEFG}{'-' * 9}\n\t\t\t     {co.BLDWHITEFG}{len(ext_cache_ctr):<,} {co.DIMREDFG}-> {co.BLDWHITEFG}Total unique extension(s){co.ENDC}") \
                    #     if not no_ext_sum else None

                    # for every val (size),list all keys (extensions) for that val
                    if not no_size_sum:
                        parts = []
                        for key2, val2 in sorted(groups_size.items(), key=lambda item: item[1], reverse=True):
                            exts = f"{key2}"
                            exts = wrap_at_nearest_space(exts, max_width=80, comma_color=comma_color)
                            parts.append(
                                f"\n{' '*7}{num_color}{val2[0]:>17,} {arrow_color}[{num_color}{get_short_size(val2[0])}{arrow_color}] {arrow_color}-> {ext_color}{exts} {arrow_color}"
                                f"{max(8 - len(strip_ascii(exts).strip(', ')), 0) * '-'}-> ({arrow_color}{ext_cache_ctr[key2]:,}"
                                f"{arrow_color}){co.ENDC}")

                        joined += (f" \n \n{co.BLDREDFG}Ext. by size:\n \n{' '*6}{co.WHITEFG}TB  GB  MB  kb bytes\n{' '*6}{co.DIMWHITEFG}-- --- --- --- ---{co.ENDC}")
                        joined += "".join(parts)

                # prints directly under ext type/app list when /nocountsum
                print(f"\t{' '*20}{co.BLDWHITEFG}{'-'*7}\n\t{' '*18}{ttl_value:>9,} {co.DIMREDFG}->{co.BLDWHITEFG} Total file(s){co.ENDC}") \
                    if not no_ext_info_sum and no_count_sum else None

                # print ttl size directly under ext type/app list when /nosizesum
                print(f"{' '*6}{co.BLDWHITEFG}{'-' * 17}\n{num_color}{' '*6}{ttl_size:>17,} [{num_color}{get_short_size(ttl_size)}{co.BLDWHITEFG}]{co.DIMREDFG} ->{co.BLDWHITEFG} Total size{co.ENDC}") \
                    if (not no_ext_info_sum and no_size_sum) else None

                print(f"{joined.replace(", ",f"{comma_color}, {co.BLDWHITEFG}")}")

                # print ttl size under size summary
                print(f"{' '*7}{co.BLDWHITEFG}{'-' * 17}\n{' '*7}{num_color}{ttl_size:>17,} [{num_color}{get_short_size(ttl_size)}{co.BLDWHITEFG}]{co.DIMREDFG} ->{co.BLDWHITEFG} Total size{co.ENDC}") \
                    if not no_size_sum else None

        # if there is anything to cache, then save
        if ext_cache:
            import gzip
            with gzip.open(pickle_dict, 'wb', compresslevel=7) as f2:
                import pickle
                pickle.dump({'ext_cache': ext_cache}, f2)
                print(f" \n"
                      f"{co.DIMWHITEFG}Saved {co.BLDWHITEFG}{len(ext_cache):,}{co.DIMWHITEFG} "
                      f"extensions to {co.BLDWHITEFG}{pickle_dict}{co.ENDC}") \
                    if debug else None
                print(f"Pickle dumped...") if debug else None

        # from common_tools.common_tools import convert_seconds
        print(f" \nElapsed time: {end_timing()[1]}") if timer else None

    else:  # showing HELP screen(s)
        result = subprocess.run(run_arr,
                                shell=True,
                                bufsize=4096,  # block-buffered
                                stderr=subprocess.STDOUT,  # Redirects stderr to stdout
                                stdout=subprocess.PIPE,
                                errors='ignore',
                                encoding='utf-8',
                                # encoding='Latin-1',
                                text=True,
                                check=False
                                )

        for line in result.stdout.splitlines():
            line_lower = line.lower()

            # directories (overrides any other criteria-to-color)
            if any(ext in line for ext in ["Displays a list of files and subdirectories in a directory."]):
                color2use = co.PURPLEFG
                line = line.replace("Displays a list of files and subdirectories in a directory.",
                                    f" \nDisplays a {co.BLDREDFG}c{co.BLDCYANFG}o{co.BLDYELLOWFG}l{co.BLDORANGEFG}o{co.BLDGREENFG}r{color2use}-coded "
                                    f"list of files and/or subdirectories in a directory. (colorization based on file extension)")

                line += f" \n \n{co.BLDWHITEFG} --> This command supports ALL of the following DOS DIR command parms: " +\
                        f"{co.DIMWHITEFG}(as well as a few of it's own...)"

            elif any(ext in line for ext in ["DIR [drive:]", "[/O[[:]sortorder]]", "[drive:]", "Specifies "]):
                color2use = co.BLDYELLOWFG
                line = line.replace("[drive:][path][filename]", "[[drive:][path][filename]...]")
                line = line.replace(f"[", f"{co.DIMREDFG}[{color2use}")
                line = line.replace(f"]", f"{co.DIMREDFG}]{color2use}")
                line = line.replace("DIR ", f"{co.BLDREDFG}CDIR{color2use} ")
                line = line.replace("Specifies drive, directory, and/or files to list.", f"Specifies drive, and/or directory path, and/or files to list.{co.DIMWHITEFG}  Multiple filespecs may be specified and are delimited by spaces.  Use quotes if necessary.")
            # elif line_lower.startswith(("mon", "tue", "wed", "thu", "fri", "sat", "sun")):
            #     prefix_line = '--> '

            else:
                color2use = co.DIMWHITEFG
                line = re.sub(
                    rf"(/A|/B|/C|/D|/L|/N|/O|/P|/Q|/R|/S|/T|/W|/X|/4|/-C|/-W|\s+([EGSD\-HLRAIOCWN])\s+)" ,
                    lambda m: f"{co.BLDYELLOWFG}{m.group(0)}{color2use}", line)
                line = re.sub(rf'\s*(Directories|Hidden files|Read-only files|Files ready for archiving|System files|' +
                              rf'Not content indexed files|Reparse Points|Prefix meaning not|Offline files|By name \(alphabetic\)|' +
                              rf'By extension \(alphabetic\)|Group directories first|By size \(smallest first\)|' +
                              rf'By date/time \(oldest first\)|Prefix to reverse order|Creation|Last Access|Last Written|' +
                              rf'attributes(?!\.)|sortorder|timefield)\s*',
                              lambda m: f"{co.BLDWHITEFG}{m.group(0)}{color2use}", line)

                line = line.replace("Pauses after each screenful of information.", "Pauses after each screenful of information (simulated).")
            prefix_line = '    '
            try:
                print(f"{color2use}{prefix_line}{line}{co.ENDC}")

            except Exception as e:
                print_except(e, "cdir oops!")
                raise e

        print(f" \n\t{co.BLDWHITEFG}The following are special parms and are handled apart from DOS DIR parms:{co.ENDC}")
        print(" ")
        print(f"{co.BLDWHITEFG}      /colorfileonly   {co.DIMWHITEFG}Color filename only, not entire detail line (DIR output){co.ENDC}")
        print(f"{co.BLDWHITEFG}      /nodetail        {co.DIMWHITEFG}Suppresses detail lines (DIR output){co.ENDC}")
        print(f"{co.BLDWHITEFG}      /detail          {co.DIMWHITEFG}Forces detail lines (DIR output){co.ENDC}")
        print(f"{co.BLDWHITEFG}      /nocountsum      {co.DIMWHITEFG}Suppresses file count summary{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /countsum        {co.DIMWHITEFG}Forces file count summary{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /nosizesum       {co.DIMWHITEFG}Suppresses file size summary{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /sizesum         {co.DIMWHITEFG}Forces file size summary{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /noextinfo       {co.DIMWHITEFG}Suppresses file association info summary{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /notimer         {co.DIMWHITEFG}Suppresses timers from the output{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /timer           {co.DIMWHITEFG}Adds a timer to the output{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /coltypeapp      {co.DIMWHITEFG}Adds Type/App column{co.ENDC}")
        print(f"{co.BLDWHITEFG}      /forcecache      {co.DIMWHITEFG}Force UPDATE the cache used for extension associations summary{co.ENDC}")
        # print(f"{co.BLDWHITEFG}      /0               {co.DIMWHITEFG}DEBUG mode (advanced use only){co.ENDC}")
        # print(f"{co.BLDWHITEFG}      /1               {co.DIMWHITEFG}DEBUG mode (show ext dtls/advanced use only){co.ENDC}")
# TODO: Create test for C:\Mount\Windows\BitLockerDiscoveryVolumeContents (has .. but no .)
        title_color = co.BLDWHITEFG
        pnemonic_color = co.BLDWHITEFG
        dash_color = co.DIMWHITEFG
        desc_color = co.DIMWHITEFG
        print(f""" \n{title_color}    File attribute flags are as follows;
        {pnemonic_color}r{dash_color} - {desc_color}read-only bit set
        {pnemonic_color}h{dash_color} - {desc_color}hidden file
        {pnemonic_color}s{dash_color} - {desc_color}system file
        {pnemonic_color}d{dash_color} - {desc_color}directory
        {pnemonic_color}a{dash_color} - {desc_color}archive bit set
        {pnemonic_color}n{dash_color} - {desc_color}normal file
        {pnemonic_color}t{dash_color} - {desc_color}temp file
        {pnemonic_color}c{dash_color} - {desc_color}compressed file
        {pnemonic_color}o{dash_color} - {desc_color}offline file
        {pnemonic_color}e{dash_color} - {desc_color}encrypted file
        {pnemonic_color}i{dash_color} - {desc_color}do not index file/dir
        {pnemonic_color}r{dash_color} - {desc_color}reparse [SYMLINK, etc.]
        {pnemonic_color}s{dash_color} - {desc_color}sparse
        {pnemonic_color}x{dash_color} - {desc_color}extended attributes
        {pnemonic_color}p{dash_color} - {desc_color}pinned
        {pnemonic_color}u{dash_color} - {desc_color}unpinned
        """)
# TODO: check-out icacls for additional attributes like owner icacls
    # signal.signal(signal.SIGINT, signal.default_int_handler)

    # print(result.stdout)
    print(co.ENDC)

def get_file_name_start(mode_2use: int=0):
    # mode: 0 - normal, 1 bare format (/B), 2 wide format
    global verbose, run_arr
    run_arr2 = []
    file_name_start = -1
    # run_arr2 = ["cmd", "/c", "dir", "*."]
    run_arr2 += ["dir"]
    # we use this in addition to no matter what, so, we always get '.' and '..' dirs
    #  and we find the beginning of the filename column relative to that
    # TODO: test with /A-D and see what happens
    run_arr2 += ["*."]
    # copy only switches
    for x in run_arr[1:]:
        if x[:2].lower() == "/b" or x[:2].lower() == "/w":
            # TODO: make sure we don't
            file_name_start = 0
            continue

        if x[:2].lower() == "/q" or x[:2].lower() == "/x" or x[:2].lower() == "/4" or x[:2].lower() == "/w":
            run_arr2 +=[x]# TODO: make case-insensitive

    # print(run_arr)
    # print(run_arr2)
    if file_name_start == -1:
        proc = subprocess.run(
            run_arr2,
            shell=True,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.STDOUT,
            capture_output=True,
            text=True  # RAW BYTES
        )
        line = ""
        cleaned = ""
        lines = proc.stdout.splitlines()
        for line in lines:
            # print(f"line={line}")
            # we use *. to only get dirs
            if not (line + " ").endswith("  . "):
                # print(f"line={line}")
                continue
            else:
                # file_name_start = max(line.find("  .") + 2, 0)
                file_name_start = (line + " ").find("  . ") + 2
                print(f"file_name_start={file_name_start}")  if debug else None

    return file_name_start

def format_line(val_2use: str, line: str, color2use: str) -> str | None:
    if val_2use is None or val_2use == "":
        return val_2use

    tab_length = 4
    min_spaces = 1  # the minimum # of spaces between the last col and the one we're adding
    space_char = ' '
    max_filename_len = 42
    line_prepend = ''
    right_margin = max(file_name_start + max_filename_len - len(line), min_spaces)

    if val_2use.find(f"{registry_srcd}") != -1:
        val_2use = val_2use.replace(f"{registry_srcd}", "")
        line_prepend += registry_srcd[:1]

    if val_2use.find(f"{api_srcd}") != -1:
        val_2use = val_2use.replace(f"{api_srcd}", "")
        line_prepend += api_srcd[:1]

    if val_2use.find(f"{dism_srcd}") != -1:
        val_2use = val_2use.replace(f"{dism_srcd}", "")
        line_prepend += dism_srcd[:1]

    line_prepend += ('}' if line_prepend else "")
    line_add = f"{space_char * int((right_margin))}{co.BLDWHITEFG}{line_prepend}{color2use}({co.DIMWHITEFG}{val_2use}{color2use}){co.ENDC}"
    line_add = line_add.replace("=",
                                f"{color2use if color2use not in (co.DIMWHITEFG, co.DIMBLACKFG) else co.WHITEFG}={co.DIMWHITEFG}")
    line_add = line_add.replace("/",
                                f"{color2use if color2use not in (co.DIMWHITEFG, co.DIMBLACKFG) else co.WHITEFG}={co.DIMWHITEFG}")

    return line_add


# import subprocess, os, winreg
import winreg

def wide_line(line: str) -> str:
    global wide_cols, wide_col_width

    print(f"line={line}") if debug else None
    process_line = False
    line_out = ""

    scol1 = "[.]"
    scol2 = "[..]"
    col1 = -1
    col2 = -1

    # if first line for this directory
    if scol1 in line and scol2 in line:
        col1 = line.find(scol1)
        col2 = line.find(scol2)
        wide_col_width=col2-col1
        wide_cols = int((len(line)/wide_col_width)+.99999)

     # prob 1 col per line
    elif scol1 in line:
        wide_cols=1
        wide_col_width=255

    elif r"File(s)" in line or r"Dir(s)" in line:
        wide_cols = -1
        wide_col_width = -1
        p_color_2use=co.BLDWHITEFG
        line_out=f"{p_color_2use}{line}{co.ENDC}"

    elif "Directory of " in line:
        wide_cols = -1
        wide_col_width = -1
        p_color_2use=co.BLDPURPLEFG
        line_out=f"{p_color_2use}{line}{co.ENDC}"

    elif line.strip() == "":
        wide_cols=-1
        wide_col_width=-1
        p_color_2use=co.BLDWHITEFG
        line_out=f"{p_color_2use}{line}{co.ENDC}"

    # so, we have a filespec and don't
    elif wide_cols==-1:
        wide_cols_list=line.split("  ")
        wide_cols=len(wide_cols_list)

    if debug:
        print(f"col1={col1}")
        print(f"col2={col2}")
        print(f"len(line)={len(line)}")
        print(f"line={line}")
        print(f"cols per line={wide_cols}")
        print(f"col width={wide_col_width}")

    if line_out=="":
        for x in range(wide_cols):
            base = x * wide_col_width
            fname = line[base: base + wide_col_width].strip()
            p_color_2use = color_2use(fname)
            fname_out = f"{p_color_2use}{fname}{co.ENDC}"
            line_out += f"{fname_out}{" "*(wide_col_width-len(fname))}"

    # print(f"line_out={line_out}".strip())
    # for x in range(wide_cols):
    #     fname=line[(wide_col_width*x)+1:wide_col_width+(wide_col_width*x)-1]
    #     p_color_2use = color_2use(fname)
    #     print(f"fname={p_color_2use}{fname}{co.ENDC}")
    #
    return line_out.strip()


def get_user_prog_id(ext: str) -> str | None:
    # def get_user_prog_id(ext: str) -> str | None:

    # Gets prog_id (used for assoc. app lookup) from registry by .ext

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            fr"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\UserChoice") as key:
            return winreg.QueryValueEx(key, "ProgId")[0]
    except FileNotFoundError:
        return None


def get_open_command(prog_id: str | None) -> str | None:
    # Gets assoc. app from Registry by prog_id

    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                            fr"{prog_id}\shell\open\command") as key:
            return winreg.QueryValueEx(key, None)[0]

    except FileNotFoundError:
        return None

    except OSError:
        # Covers other registry access errors
        return None

import xml.etree.ElementTree as ET


def get_record_by_extension(xml_path: str, target_ext: str) -> str | None:
    # Gets assoc. app from DISM extract by .ext

    tree = ET.parse(xml_path)
    root = tree.getroot()

    for assoc in root.findall('Association'):
        # ext = assoc.find('Identifier')
        ext = assoc.attrib.get('Identifier')
        if ext is not None and ext == target_ext:
            return ET.tostring(assoc, encoding='unicode')
    return None


import subprocess  #, os
def wrap_at_nearest_space(text: str,
                          max_width: int,
                          indent: str = (' '*27),
                          comma_color: str = f"{co.BLDREDFG}") -> str:
    """
    Wrap `text` preserving words (split on spaces/comma+space boundaries),
    preferring the last space before max_width; if none, use the first space after.
    Subsequent lines are indented to align with the start of the list (indent).
    """
    # if indent is None:
    #     # default indent: everything up to and including "-> " on first line
    #     if "->" in text:
    #         prefix, _, rest = text.partition("->")
    #         indent = " " * (len(prefix) + 3)  # keep a space after arrow
    #
    #     else:
    #         indent = " " * 27

    out_lines = []
    s_raw = strip_ascii(text).lstrip(", ").strip()
    indent_prefix = ""
    while s_raw:
        # s_raw = s_raw.lstrip(", ")

        if len(s_raw) <= max_width:
            out_lines.append(s_raw)
            break

        # candidate window
        window = s_raw[:max_width+1]  # allow one char past limit to find a space after
        # try to find last space before or at max_width
        cut = window.rfind(", .", 0, max_width+1)
        if cut == -1:
            # no space before limit: find first space after limit in the remainder
            cut = s_raw.find(", .", max_width)
            if cut == -1:
                # no space at all: nothing to split on, shove whole remainder
                out_lines.append(s_raw)
                break

        # append the current trimmed piece
        # the +1 is so we include the first char of the delim at the end of piece - ','
        piece = (s_raw[:cut+1])

        # if we have a trailing comma, color it
        if piece.endswith(","):
            piece = piece[:len(piece)-1] + f"{comma_color},{co.BLDWHITEFG}"
        # color all embedded extension delimiters
        piece = piece.replace(", .", f"{comma_color},{co.BLDWHITEFG} .")

        try:
            out_lines.append(piece)
        except Exception as e:
            print(f"len(out_lines) = [{len(out_lines):,}")
            print(f"piece = [{piece}]")
            print(f"len(piece) = [{len(piece):,}]")
            print(f"cut = [{cut}]")
            # print(f"len(cut) = {len(cut)}")
            print(f"s_raw = [{s_raw}]")
            print(f"len(s_raw) = {len(s_raw):,}")

        # prepare remainder, trim any leading comma and/or spaces
        s_raw = s_raw[cut + 2:].lstrip(", ")
        # prefix subsequent lines with indent if they are continuation of list
        if out_lines:  # and indent:
            # only apply indent to lines after the first
            indent_prefix = indent
            # build next visible line with indent
            # s_raw = indent_prefix + s_raw

    return f" \n{indent_prefix}".join(out_lines)


def pass_filtered(d1, d2, threshold):
    # return a new dict with items from d1 whose keys are in d2 and d2[key] > threshold
    return {k: v for k, v in d1.items() if k in d2 and d2[k] > threshold}

# import ctypes
# from ctypes import wintypes

def has_reparse_point(path):
    has_reparse = False
    # has_reparse2 = False
    # FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
    # GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
    # GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    # GetFileAttributesW.restype = wintypes.DWORD
    #
    # attrs = GetFileAttributesW(path)
    # if attrs == 0xFFFFFFFF:
    #     # raise FileNotFoundError(f"Cannot access: {path}")
    #     print(f"{co.FAIL}Cannot access: {co.BLDYELLOWFG}{path}{co.ENDC}")
    #
    # if bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT):
    #     has_reparse = True
    #
    # else:
    reparse = subprocess.run(["fsutil", "reparsepoint", "query", f"{path}"],
                             stderr=subprocess.STDOUT,  # Redirects stderr to stdout
                             stdout=subprocess.PIPE,
                             errors='ignore',
                             encoding='utf-8'
                             )
    if "Reparse Tag" in reparse.stdout:
        has_reparse = True

    return has_reparse

# import os

def is_reparse(path):
    try:
        stat = os.lstat(path)
        return stat.st_reparse_tag != 0
    except Exception:
        return False

import ctypes
import os

def get_file_attributes(path):
    # Ensure path is absolute and normalized
    # path = os.path.abspath(path)

    # Constants from Win32 API
    FILE_ATTRIBUTE_READONLY   = 0x0001
    FILE_ATTRIBUTE_HIDDEN     = 0x0002
    FILE_ATTRIBUTE_SYSTEM     = 0x0004
    FILE_ATTRIBUTE_DIRECTORY  = 0x0010
    FILE_ATTRIBUTE_ARCHIVE    = 0x0020
    FILE_ATTRIBUTE_NORMAL     = 0x0080
    FILE_ATTRIBUTE_TEMPORARY  = 0x0100
    FILE_ATTRIBUTE_SPARSE_FILE= 0x0200
    FILE_ATTRIBUTE_REPARSE_POINT        = 0x0400
    FILE_ATTRIBUTE_COMPRESSED = 0x0800
    FILE_ATTRIBUTE_OFFLINE    = 0x1000
    FILE_ATTRIBUTE_NOT_CONTENT_INDEXED  = 0x2000
    FILE_ATTRIBUTE_ENCRYPTED  = 0x4000
    FILE_ATTRIBUTE_EA         = 0x40000
    FILE_ATTRIBUTE_PINNED     = 0x80000
    FILE_ATTRIBUTE_UNPINNED   = 0x100000

    # Call GetFileAttributesW from kernel32
    import ctypes
    # path_abs = os.path.abspath(path)
    # attrs = ctypes.windll.kernel32.GetFileAttributesW(ctypes.c_wchar_p(path})

    GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
    GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    GetFileAttributesW.restype = ctypes.c_uint32

    attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
    if attrs == -1:  # did not find
        err = ctypes.GetLastError()
        # print("Error code (2-fnf, 3-pnf, 5-AD): ", err)

        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.kernel32.FormatMessageW(
            0x00001000,  # FORMAT_MESSAGE_FROM_SYSTEM
            None,
            err,
            0,
            buf,
            len(buf),
            None
        )
        # print( f"\t{co.FAIL}Error code: {err} -> {buf.value.strip()} -> {path}{co.ENDC}")
        print( f"\t{co.FAIL}get_file_attributes() -> Error code: {err} -> {buf.value.strip()} -> {path}{co.ENDC}")

        # raise FileNotFoundError(f"File not found or inaccessible: {path}")
        return {}

    # Decode attributes
    flags = {
        'readonly': bool(attrs & FILE_ATTRIBUTE_READONLY),
        'hidden': bool(attrs & FILE_ATTRIBUTE_HIDDEN),
        'system': bool(attrs & FILE_ATTRIBUTE_SYSTEM),
        'directory': bool(attrs & FILE_ATTRIBUTE_DIRECTORY),
        'archive': bool(attrs & FILE_ATTRIBUTE_ARCHIVE),
        'normal': bool(attrs & FILE_ATTRIBUTE_NORMAL),
        'temporary': bool(attrs & FILE_ATTRIBUTE_TEMPORARY),
        'compressed': bool(attrs & FILE_ATTRIBUTE_COMPRESSED),
        'offline': bool(attrs & FILE_ATTRIBUTE_OFFLINE),
        'encrypted': bool(attrs & FILE_ATTRIBUTE_ENCRYPTED),
        'indexednot': bool(attrs & FILE_ATTRIBUTE_NOT_CONTENT_INDEXED),
        # 'reparse': bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT),
        'reparse': bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT) or is_reparse(path), # or has_reparse_point(path),
        # 'reparse': bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT) or is_reparse(path),
        'sparse': bool(attrs & FILE_ATTRIBUTE_SPARSE_FILE),
        'xtendedatt': bool(attrs & FILE_ATTRIBUTE_EA),
        'pinned': bool(attrs & FILE_ATTRIBUTE_PINNED),
        'unpinned': bool(attrs & FILE_ATTRIBUTE_UNPINNED)
    }

    return flags


def get_metadata(p_ext: str, p_size: str, p_is_dir: bool, force_update_cache: bool = False) \
        -> str | None:
    # Gets assoc. app from API/Registry/DISM extract

    #  we are now logging no extension files as well
    p_ext = p_ext.lower() if p_ext else "<???>"

    p_size = p_size.strip().replace(",","").replace("(","").replace(")","")
    if p_ext.startswith(('.movie_')):  # or p_ext.startswith((f'.movie_','.dll_','.fon_','.exe_','.mui_','.sys_')):
        print(f"No ext was found or will be cached! [{p_ext}]") if debug else None
        # TODO: maintain an empty/null list member for no-ext files
        return

    elif p_ext in ext_cache:
        print(f"{p_ext} was cached.") if debug else None

        # try to increment ctr by 1
        try:
            ext_cache_ctr[p_ext] += 1

        # this ext (key) isn't in the list yet, so, we'll add it
        except KeyError:
            ext_cache_ctr[p_ext] = 1

        # try to increment ext size by file size
        try:
            ext_cache_size[p_ext] += int(p_size)

        # this ext (key) isn't in the list yet, so, we'll add it
        except KeyError:
            ext_cache_size[p_ext] = int(p_size)

        # somehow, we didn't grab the file size correctly, so, we'll use 0
        except ValueError:
            ext_cache_size[p_ext] += int(0)

        except Exception as e:
            print("Error:", e)

        # if we're not forcing a cache refresh we'll leave since
        #  the ext is already in the cache
        if not force_update_cache:
            return ext_cache[p_ext]

    #-----------------------------------------
    # if cahce entry was already found, then we never get this far
    #  unless /forcecache was specified CLI
    # now, let's get the info for an extension so we can (re-)cache it.
    print(f"{p_ext} was NOT cached but now is!") if debug else None

    # Run assoc and ftype only if not cached
    assoc_1 = subprocess.run(['assoc', p_ext], shell=True, capture_output=True, text=True).stdout.strip()
    assoc_1 = (assoc_1.split('=') if '=' in assoc_1 else assoc_1)
    assoc_1_ext = assoc_1[0] if isinstance(assoc_1, list) else assoc_1
    assoc_1_type = assoc_1[1] if isinstance(assoc_1, list) else assoc_1

    filetype_1 = assoc_1_type if assoc_1_type else assoc_1

    # if we got something from 'assoc' then we have what we need to call 'ftype'
    if assoc_1:
        ftype_out_1 = subprocess.run(['ftype', assoc_1_type],
                                     shell=True,
                                     capture_output=True,
                                     text=True).stdout.strip()
    else:
        # ftype_out_1 = "<unknown> assoc"
        ftype_out_1 = ""

    prog_reg_id_1 = get_user_prog_id(p_ext)

    if prog_reg_id_1:
        ftype_reg_out_1 = get_open_command(prog_reg_id_1)

    else:
        ftype_reg_out_1 = ""

    def shorten_prog_id(str_2use: str) -> str:
        print(f"str_2use[:4]={str_2use[:4]}") if debug else None
        if str_2use[:4] == 'AppX':
            str_2use = f'{str_2use[:4]}...{str_2use[-6:]}'

        return str_2use

    def shorten_app(str_2use: str) -> str:
        print(f"str_2use={str_2use}") if debug else None
        # if str_2use.find(r"C:\Program Files\WindowsApps\Microsoft.Windows") > -1:
        str_2use = str_2use.replace(r"C:\Program Files\WindowsApps\Microsoft.Windows", r"C:\...")
        return str_2use

    def shorten_ext(str_2use: str) -> str:
        print(f"len(str_2use)={len(str_2use)}") if debug else None
        if len(str_2use) > 35:
            str_2use = f'{str_2use[:10]}...{str_2use[-15:]}'

        return str_2use

    ftype_dism_1 = get_record_by_extension(assoc_file, p_ext)
    ftype_dism_1 = ET.fromstring(ftype_dism_1) if ftype_dism_1 else None

    if show_ext_dtls:  # debug:
        print(f"p_ext            = {p_ext}")
        print()
        print(f"assoc_1          = {assoc_1}")
        print(f"assoc_1_ext      = {assoc_1_ext}")
        print(f"assoc_1_type     = {assoc_1_type}")
        print(f"ftype_out_1      = {ftype_out_1}")
        print()
        print(f"prog_reg_id_1    = {prog_reg_id_1}")
        print(f"ftype_reg_out_1  = {ftype_reg_out_1}")
        print()
        print(f"ftype_dism_1     = {ftype_dism_1}")
        print(
            f"ftype_dism_1.get('ProgId')          = {ftype_dism_1.get('ProgId')}") if ftype_dism_1 is not None else None
        print(
            f"ftype_dism_1.get('ApplicationName') = {ftype_dism_1.get('ApplicationName')}") if ftype_dism_1 is not None else None

    # if we have info fs rom DOS 'ftype' command, let's just use that.
    if ftype_out_1:
        # if we have a prog_id in the registry for that ext, and it's neither a duplicate of
        #   what came from 'ftype' or a mosly cryptic 'AppX...' designation, we'll
        #  prepend that as well
        if prog_reg_id_1 and prog_reg_id_1[:4] != 'AppX' and not ftype_out_1.startswith(prog_reg_id_1):
            line_1 = f"{api_srcd}{registry_srcd}{prog_reg_id_1}/{ftype_out_1}"

        # if we either don't have a prog_id, or what we got was redundant and/or cryptic (AppX)
        #  we'll just use the output from the 'ftype' DOS command
        else:
            line_1 = f"{api_srcd}{ftype_out_1}"

    # if there was no output from the DOS 'ftype' command but we did get data from the DOS 'assoc'
    #  command, and there is registry information for the app for this ext as well, then we use that
    elif assoc_1_type and ftype_reg_out_1:
        line_1 = f"{api_srcd}{registry_srcd}{shorten_prog_id(assoc_1_type)}={shorten_app(ftype_reg_out_1)}"

    # if there was no output from the DOS 'ftype' command and we did NOT get data from the DOS 'assoc'
    #  command, but there is registry information for the app, then we use that
    elif ftype_reg_out_1 and prog_reg_id_1:
        line_1 = f"{registry_srcd}{shorten_prog_id(prog_reg_id_1)}={shorten_app(ftype_reg_out_1)}"

    # if there is no assoc->ftype or complete registry info, we'll use dism (if avail.)
    elif ftype_dism_1 is not None:
        if assoc_1_type:  # ??? do we ever get here?, only if we have no 'ftype' but have 'assoc' and 'dism' info
            line_1 = f"{co.BLDWHITEFG}{api_srcd}{dism_srcd}{assoc_1_type}={shorten_app(ftype_dism_1.get("ApplicationName"))}"

        elif prog_reg_id_1:
            line_1 = f"{registry_srcd}{dism_srcd}{shorten_prog_id(prog_reg_id_1)}={shorten_app(ftype_dism_1.get("ApplicationName"))}"

        else:
            line_1 = f"{dism_srcd}{shorten_prog_id(ftype_dism_1.get("ProgId"))}={shorten_app(ftype_dism_1.get("ApplicationName"))}"

    elif assoc_1_type:
        line_1 = f"{api_srcd}{p_ext}={assoc_1_type}=<unknown>"

    else:
        #  we only call shorten_ext() if the extension is <undefined> and long (>30 chars)
        # ??? are there any more places to look?
        line_1 = f'{shorten_ext(p_ext)}=<undefined>'

    print(f"line_1={line_1}") if debug else None

    # if we got here then we don't have any cach'd info/items for this p_ext yet, so, we create them
    ext_cache[p_ext] = line_1
    ext_cache_ctr[p_ext] = 1
    ext_cache_size[p_ext] = int(p_size)

    print(" ")

    print(f"ext_cache[ext]={ext_cache[p_ext]}") if debug else None
    print(f"ext_cache_ctr[ext]={ext_cache_ctr[p_ext]}") if debug else None
    print(f"ext_cache_size[ext]={ext_cache_size[p_ext]}") if debug else None
    # ext_cache[ext] = ast.literal_eval(ext_cache[ext])

    return ext_cache[p_ext]

def color_2use(p_line: str = "",
               p_ext: str = "") -> str:

    global file_wide_format
    p_line = p_ext if p_ext else p_line
    p_line_lower = p_line.lower()

    # if p_ext:
    #     pass
    # do we have a dir in /W wide file format? (always [dir])
    if file_wide_format and p_line[:1]=="[" and p_line[len(p_line)-1:].strip() == "]":
        p_color_2use = co.PURPLEFG

    elif any(ext in p_line for ext in ["<DIR>"]):
        p_color_2use = co.PURPLEFG
        # line_2 = f" ({len(line)})({line.find('<DIR>')})"
        # FIXME: if add'l columns are specified, these strings don't match
        # file_name_start = max((line.strip() + " ").find("  . ") + 2, file_name_start)
        # file_name_start = 0
        # print(f"file_name_start={file_name_start}") if debug else None
        # line += line_2

    elif any(ext in p_line for ext in ["<JUNCTION>", "<SYMLINK>", "<SYMLINKD>", "<REPARSE>"]):
        p_color_2use = co.BLDPURPLEFG
        # reparse = True

    # directory name
    elif any(ext in p_line for ext in ["Directory of"]):
        # prefix_line = ''  # must be at least 1 char or will be set below
        p_color_2use = co.PURPLEFG
        # p_curr_dir = p_line.replace("Directory of ", "")

    # info lines
    elif any(ext in p_line for ext in ["Volume in drive", "Volume Serial Number",
                                     "File(s)", "Dir(s)",
                                     "Total Files Listed"]):
        p_color_2use = co.BLDWHITEFG

    # executable / command files
    elif p_line_lower.endswith((".exe", ".bat", ".ps1", ".psc1", ".psm1", ".psd1",
                              ".com", ".cmd", ".msi", ".ws f", ".cpl", ".ocx", ".js", ".vbs")):
        p_color_2use = co.BLDGREENFG

    # PYTHON and app related files (perhaps later we add all source-code-related files)
    elif p_line_lower.endswith(
            (".py", ".pyc", ".c", ".cpp", ".h", ".lib", ".msc", ".pyi", ".pyd", ".pyz", ".pyzw", ".toc",
             ".pyw", ".cs", ".asp", ".aspx", ".ascx", ".html", ".htm", ".url", ".css", ".resx",
             "installer", "license", "license_apache", "metadata", "record", "wheel", "requested", "notice", "authors",
             "license-header", "copying", ".head", "py.typed", "readme.md", ".gitignore", ".csproj", ".xhtml",
             ".website", ".vssettings", ".vsix", ".user", ".udl", ".sln", ".sh", ".obj")):
        p_color_2use = co.BLUEFG

    # compressed / virtualized / encryption
    elif p_line_lower.endswith((".zip", ".gzip", ".gz", ".iso", ".cab", ".vhdx", ".vhd", ".rar", ".7z", ".xz",
                              ".bz2", ".z", ".lz", ".lzma", ".cer", ".cat", ".001", ".crt",
                              ".crl", ".uue", ".tar", ".sst", ".rev", ".lic", ".kdbx")):
        p_color_2use = co.REDFG

    # data files
    elif p_line_lower.endswith(
            (".sql", ".json", ".db", ".xml", ".xsd", ".ini", ".dat", ".csv", ".config", ".cfg", ".chm",
             ".bak", ".pkl",
             ".config.default", ".manifest", ".reg", ".ps1xml", ".cdxml", ".torrent", ".resume")):
        p_color_2use = co.DIMREDFG

    # Video files
    elif p_line_lower.endswith(
            ('.mkv', '.avi', '.mp4', '.mpg', '.mov', '.m4v', '.vob', '.bup', '.ifo', '.webm',
             '.wmv', '.flv', '.3gp', '.3gpp', '.mpeg', '.mxf', '.braw', '.r3d', '.yuv', '.ts',
             '.m2ts', '.f4v', '.divx', '.rm', '.asf', '.dvr-ms', '.ogv', ".cue", ".asx",
             ".xspf", ".wmz")):
        p_color_2use = co.BLDORANGEFG

    # music files
    elif p_line_lower.endswith(
            (".mp3", ".flac", ".wav", ".m4a", ".m4p", ".ra", ".m3u", ".ogg", ".wma", ".aac",
             ".alac", ".ape", ".wv", ".aiff", ".pcm", ".mka", ".mod", ".xm", ".mid", ".midi",
             ".rmi", ".dts", ".ac3", ".au", ".apl", ".amr", ".aifc", ".aif", ".mac", ".m4b",
             ".m3u8")):
        p_color_2use = co.ORANGEFG

    # e-book / document files
    elif p_line_lower.endswith(
            ('.epub', '.mobi', '.pdf', '.djvu', '.txt', '.log', '.rtf', '.nfo', '.doc', '.docx',
             ".wsc")):
        p_color_2use = co.DIMGREENFG

    # pic / image files
    elif p_line_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
                              ".tif", ".webp", ".heic", ".heif", ".raw", ".cr2",
                              ".nef", ".arw", ".orf", ".dng", ".svg", ".ai", ".eps",
                              ".ico", ".icns", ".dds", ".exr", ".psd", ".xcf", ".bay",
                              ".wmf" )):
        p_color_2use = co.DIMBLUEFG

    # system files
    elif p_line_lower.endswith(
            (".dll", ".sys", ".bin", ".inf_loc", ".mui", ".inf", ".cat", ".tlb", ".targets", ".ttf", ".compositefont",
             ".diagpkg", ".theme", ".resmoncfg")):
        p_color_2use = co.GREENFG

    else:
        p_color_2use = co.WHITEFG

    return p_color_2use

# Check for Admin rights (required for some file data in CDir)
import ctypes
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if __name__ == '__main__':
    main()
    # return None
