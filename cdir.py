# from argparse import ArgumentParser, Namespace
# from logging import exception
# from typing import Any
# from functools import lru_cache

# import sys, copy, os, re, pickle, time, subprocess, msvcrt, io
import sys, os, re
from msvcrt import getch, kbhit
from typing import Optional

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
file_name_start = 43  # just a default, gets reset below

user_profile = os.environ.get("USERPROFILE").replace("C:","H:").replace(r"\\", r"\\\\") + "\\"
dir_env_var = os.environ.get("DIRCMD") or ""
assoc_file = rf'{user_profile}\DefaultAppAssociations.xml'
debug = False
show_ext_dtls=False
gflags = None
# time_start = time.time()


def main():
    global gflags
    global co
    import os
    global user_profile, dir_env_var
    global file_name_start
    global show_ext_dtls
    global ext_cache, ext_cache_ctr, ext_cache_size

    begin_timing()  # start timer

    os.system('')  # needed for subsequent ANSI color code rendering, especially in DOS Admin mode

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

    co = BColors(False)
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
            print(f"\n"
                  f"{co.DIMWHITEFG}Loaded {co.BLDWHITEFG}{len(ext_cache):,}{co.DIMWHITEFG} "+
                  f"extensions from {co.BLDWHITEFG}{pickle_dict}{co.ENDC}") \
                if debug else None
            # print(f"Pickle Data load = {pickle_data}")  # if gargs_lcl.verbose else None

    # Check for Admin rights (required for some file data in CDir)
    import ctypes
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if not os.path.exists(assoc_file):
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
            print(f"DISM extract file created -->  {assoc_file}")

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

    # if order is specified on the command-line
    order_specified = False
    if any((flag.lower() in sys.argv or flag in dir_env_var) for flag in ('/O', '/o', '-O', '-o')):
        order_specified = True

    # if /coltypeapp is specified on the command-line
    coltypeapp = False
    while any(flag.lower() in sys.argv for flag in (['/coltypeapp'])):
        coltypeapp = True
        sys.argv.remove('/coltypeapp')

    # if /nodetail is specified on the command-line
    no_detail = False
    while any(flag.lower() in sys.argv for flag in (['/nodetail'])):
        no_detail = True
        sys.argv.remove('/nodetail')

    # if /noextsum is specified on the command-line
    no_ext_sum = False
    while any(flag.lower() in sys.argv for flag in (['/noextsum'])):
        no_ext_sum = True
        sys.argv.remove('/noextsum')

    # if /novalsum is specified on the command-line
    no_val_sum = False
    while any(flag.lower() in sys.argv for flag in (['/novalsum'])):
        no_val_sum = True
        sys.argv.remove('/novalsum')

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

    # if /timer is specified on the command-line
    color_filename_only = False
    while any(flag.lower() in sys.argv for flag in (['/filecoloronly'])):
        color_filename_only = True
        sys.argv.remove('/filecoloronly')

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
        run_arr += ['/OGEN']  # 'G' needs to go 1stcdir

    # the /p parm is ignored by DIR when using subprocess, so, we simulate pagination
    paginate = False
    i_page = 50
    if any(flag in sys.argv for flag in ('-p', '/p', '/P', '-P')):
        # run_arr += [' | more']
        paginate = True

    print(f"{co.BLDYELLOWFG}\n\tReading directories/files, please wait...") if not show_help else None
    print(sys.argv) if debug else None
    print(f"DIR cmd = {run_arr}")  if debug else None
    # with open(p_file, "wt", encoding='utf-8') as dirtext:
    result = subprocess.run(run_arr,
                            shell=True,
                            bufsize=4096,    # block-buffered
                            stderr=subprocess.STDOUT,  # Redirects stderr to stdout
                            stdout=subprocess.PIPE,
                            errors='ignore',
                            encoding='utf-8',
                            # encoding='Latin-1',
                            text=True,
                            check=False
                            )
    block_relative_dirs = True  # do not display '.' and '..' <DIR>s

    if not show_help:
        i = 0
        lines = result.stdout.splitlines()
        print(f"{co.BLDYELLOWFG}\t...processing {len(lines):,} lines...\n") if len(lines) > 999 else None
        print()
        file_name_start = 0

        def replacer(match):
            prefix = match.group(1)  # everything up to AM/PM
            spaces = match.group(2)  # leading spaces
            number = match.group(3)  # the digits
            suffix = match.group(4)  # everything after
            return prefix + " " + co.DIMBLACKFG + ('-' * (max(len(spaces)-3,3))) + r"> " + co.DIMWHITEFG + number + suffix

        for line in lines:
            line = line.strip()
            is_dir = False
            is_dir_name = False
            is_file = False
            p_curr_dir = ""
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

            if block_relative_dirs:
                if (line + " ").find("  . ") > -1:
                    print(f'(line+" ").find("  . " )  = {(line + " ").find("  . ")}') if debug else None
                    file_name_start = max((line.strip() + " ").find("  . ") + 2,
                                          0) if file_name_start <= 1 else file_name_start
                    continue

                elif (line + " ").find("  .. ") > -1:
                    print(f'(line+" ").find("  .. ") = {(line + " ").find("  .. ")}') if debug else None
                    continue

            if any(ext in line for ext in ["<DIR>"]):
                is_dir = True
                file_name_start = max((line.strip() + " ").find("  . ") + 2, 0) if file_name_start <= 1 else file_name_start

            file_name_start = 43 if file_name_start == 0 else file_name_start
            color2use = color_2use(p_line=line)
            # directories (overrides any other color criteria)

            line = line.replace(f"Directory of", f"{co.BLDWHITEFG}Directory of{color2use}")
            line = line.replace(f"File Not Found", f"{co.BLDREDFG}\n\tFile Not Found{co.ENDC}")
            line = line.replace(f"The specified path is invalid.", f"{co.BLDREDFG}\n\tThe specified path is invalid.{co.ENDC}")

            if any(ext in line for ext in ["Directory of"]):
                is_dir_name = True
                # prefix_line = ''  # must be at least 1 char or will be set below
                p_curr_dir = strip_ascii(line).replace("Directory of ", "").strip()
            # reparse = False

            if any(ext in line for ext in ["<DIR>", "<JUNCTION>", "<SYMLINK>", "<SYMLINKD>", "<REPARSE>"]):
                is_dir = True
                if any(ext in line for ext in ["<JUNCTION>", "<SYMLINK>", "<SYMLINKD>", "<REPARSE>"]):
                    reparse = True
                else:
                    reparse = False

                prefix_line = (' '*len(f'-({i:>3})-> ')) if not prefix_line else prefix_line
                # we get the file-type and app-to-use fr that ext.
                p_filename, p_ext = os.path.splitext(line[file_name_start:])
                p_size = line[(file_name_start - 15):file_name_start - 1].replace(",", "")
                attrs = get_file_attributes(f"{p_curr_dir}")
                line += f"\t{co.DIMWHITEFG}" if len(attrs.items()) > 0 else ""
                line += '\t' if len(f"{p_filename}{p_ext}") < 4 else ""
                # line += f"\t{'\t' * max(int((24 - len(f"{p_filename}{p_ext}")) / 8), 1)}{co.DIMWHITEFG}" if len(attrs.items()) > 0 else ""

                # handle attributes
                color_true = co.BLDWHITEFG
                color_false = co.DIMBLACKFG
                for k, v in attrs.items():
                    if k == 'reparse':
                        line += f"{color_true}{k[0]}{color_false}" if str(v)[0].lower() == 't' or reparse else f"{color_false}{k[0]}"  # f'{chr(250)}'

                    else:
                        line += f"{color_true}{k[0]}{color_false}" if str(v)[0].lower() == 't' else f"{color_false}{k[0]}"  #f'{chr(250)}'

                line += f"{co.ENDC}" if len(attrs.items()) > 0 else ""

            elif line_lower.startswith(("mon", "tue", "wed", "thu", "fri", "sat", "sun")):
                is_file = True
                i += 1
                prefix_line = f'-({i:>3})-> '

                print(line[file_name_start:]) if debug else None

                # we get the file-type and app-to-use fr that ext.
                p_filename, p_ext = os.path.splitext(line[file_name_start:])
                p_size = line[(file_name_start - 15):file_name_start - 1].replace(",", "")

                # if entire line not color-coded, then files might be harder to follow left-to-right
                line = re.sub(r'^(.*?\b(?:AM|PM))(\s+)(\d+)(.*)$', replacer, line) if color_filename_only else line
                # print(f"{prefix_line}{line2}") if debug else None

                ret_val3 = get_metadata(p_ext, p_size) if p_ext else ""

                if coltypeapp:
                    # print(f"p_size = '{p_size}'") if p_size else None
                    # print(f"line[file_name_start:] = '{line[file_name_start-15:file_name_start-1]}'") if line[file_name_start-15:] else None
                    print(f"ret_val3={ret_val3}") if ret_val3 is not None and debug else None
                    # now, we'll add the type/app column
                    line += f"{format_line(ret_val3, line, color2use)}"
# ???
                # file_path = r"C:\Users\Edward\Documents\secret.txt"
                attrs = get_file_attributes(rf"{p_curr_dir}\{p_filename}{p_ext}")
                line += f"\t{co.DIMWHITEFG}" if len(attrs.items()) > 0 else ""
                for k, v in attrs.items():
                    line += f"{co.BLDWHITEFG}{k[0]}{co.DIMWHITEFG}" if str(v)[0].lower() == 't' else f"{co.DIMBLACKFG}{k[0]}{co.DIMWHITEFG}"  #  # else  f'{chr(250)}'

                line +=  f"{co.ENDC}" if len(attrs.items()) > 0 else ""

                # print(f"{k}: {v}")
            # elif line.find("<DIR>") > -1:
            #     prefix_line = (' '*len(f'-({i:>3})-> ')) if not prefix_line else prefix_line

            elif any(ext in line for ext in ["File(s)", "Dir(s)"]):
                line = "\t" + line

            else:
                prefix_line = '' if not prefix_line else prefix_line
                
            try:
                p_filename, p_ext = os.path.splitext(strip_ascii(line)[file_name_start:]) if not p_filename else (p_filename, p_ext)
                if p_filename and file_name_start > 1 and color_filename_only and (is_file or is_dir):
                    print(line)
                    line_1 = re.sub(f'{p_filename}{p_ext}',f'{color2use}{p_filename}{p_ext}', line)
                    print(f"{co.DIMWHITEFG}{prefix_line}{line_1}{co.ENDC}") \
                        if not no_detail else None
                else:
                    print(f"{color2use}{prefix_line}{line}{co.ENDC}") \
                        if not no_detail else None

            except UnicodeEncodeError:
                # print_except(e, "CDIR oops!")
                # raise e
                print(f"{co.FAIL}Unicode Error{co.ENDC}")

            except Exception as e:
                print_except(e, "CDIR oops!!")
                raise e

        from common_tools.common_tools import print_dict

        # no sense in showing extension summary if less than 1 extensions encountered
        if ext_cache_ctr and len(ext_cache_ctr) > 0:

            print(f"\n{co.BLDYELLOWFG}All extensions encountered [{co.BLDGREENFG}{len(ext_cache_ctr)} "
                f"unique{co.BLDYELLOWFG}] are as follows:\n{co.ENDC}") \
                if not no_ext_sum or not no_val_sum else None
            if not no_ext_sum:
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
                s_print2 = ""
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
                comma_color = co.REDFG
                ext_color = co.BLDWHITEFG
                arrow_color = co.DIMWHITEFG
                num_color = co.BLDYELLOWFG
                for ext, val in ext_cache_ctr.items():

                    # # there IS GROUING by value for size
                    # groups_ctr[val].append(ext)
                    # # there IS NO GROUING by value for size
                    # groups_size[ext].append(val)

                    parts = []

                    # for every val (file count),list all keys (extensions) for that val
                    for val2 in sorted(groups_ctr.keys(), reverse=True):
                        # size2 = groups_size[val2]
                        exts = f"{comma_color},{ext_color} ".join(sorted(groups_ctr[val2]))
                        exts = wrap_at_nearest_space(exts, max_width=80, indent=28 * ' ', comma_color=comma_color)
                        parts.append(
                            f"\n\t{' '*6}{num_color}{val2:>9,} {arrow_color}-> {ext_color}{exts} {arrow_color}"
                            # f"\n\t{' '*6}{num_color}{val2:>9,} {arrow_color}-> {ext_color}{exts} ({size2}){arrow_color}"
                            # f"{max(8 - len(strip_ascii(exts).strip(', ')), 0) * '-'}"  #-> ({arrow_color}{groups_ctr[val]:,}"
                            # f"{arrow_color}){co.ENDC}"
                            )

                    joined = f"\n\t{co.BLDREDFG}Ext. file counts:\t"+" ".join(parts)

                    # print ttl files w/ext
                    joined += (
                        f"\n\t{' '*6}{co.BLDWHITEFG}{'-' * 9}\n\t{' '*6}{num_color}{ttl_value:>9,} {co.DIMREDFG}->{co.BLDWHITEFG} Total file(s) w/extension{co.ENDC}") \
                        if not no_ext_sum else None

                    # for every val (size),list all keys (extensions) for that val
                    parts = []
                    for key2, val2 in sorted(groups_size.items(), key=lambda item: item[1], reverse=True):
                        # exts = f"{comma_color},{ext_color} ".join(sorted(groups_size[val]))
                        exts = f"{key2}"
                        exts = wrap_at_nearest_space(exts, max_width=80, indent=28 * ' ', comma_color=comma_color)
                        parts.append(
                            f"\n\t{num_color}{val2[0]:>17,} {arrow_color}-> {ext_color}{exts} {arrow_color}"
                            f"{max(8 - len(strip_ascii(exts).strip(', ')), 0) * '-'}-> ({arrow_color}{ext_cache_ctr[key2]:,}"
                            f"{arrow_color}){co.ENDC}")

                    joined += f"\n\n\t{co.BLDREDFG}Ext. by size:"+"  ".join(parts)

                # prints directly under ext type/app list
                print(f"\t{co.BLDWHITEFG}{'-'*9}\n\t{ttl_value:>9,} {co.DIMREDFG}->{co.BLDWHITEFG} Total file(s) w/extension{co.ENDC}") \
                    if no_ext_sum else None

                print(f"{joined.replace(", ",f"{comma_color}, {co.BLDWHITEFG}")}")  \
                    if not no_val_sum else None

                # print ttl unique extensions
                print(f"\t\t\t     {co.BLDWHITEFG}{'-'*9}\n\t\t\t     {co.BLDWHITEFG}{len(ext_cache_ctr):<,} {co.DIMREDFG}-> {co.BLDWHITEFG}Total unique extension(s){co.ENDC}")\
                    if not no_val_sum else None

                # print ttl size
                print(f"\t{co.BLDWHITEFG}{'-' * 17}\n\t{num_color}{ttl_size:>17,}{co.DIMREDFG} ->{co.BLDWHITEFG} Total size (bytes){co.ENDC}") \
                    if not no_ext_sum else None

        # if there is anything to cache, then save
        if ext_cache:
            import gzip
            with gzip.open(pickle_dict, 'wb', compresslevel=7) as f2:
                import pickle
                pickle.dump({'ext_cache': ext_cache}, f2)
                print(f"\n"
                      f"{co.DIMWHITEFG}Saved {co.BLDWHITEFG}{len(ext_cache):,}{co.DIMWHITEFG} "
                      f"extensions to {co.BLDWHITEFG}{pickle_dict}{co.ENDC}") \
                    if debug else None
                print(f"Pickle dumped...") if debug else None

        # from common_tools.common_tools import convert_seconds
        print(f"\nElapsed time: {end_timing()[1]}") if timer else None

    else:  # showing HELP screen(s)
        for line in result.stdout.splitlines():
            line_lower = line.lower()

            # directories (overrides any other criteria-to-color)
            if any(ext in line for ext in ["Displays a list of files and subdirectories in a directory."]):
                color2use = co.PURPLEFG
                line = line.replace("Displays a list of files and subdirectories in a directory.",
                                    f"\nDisplays a {co.BLDREDFG}c{co.BLDCYANFG}o{co.BLDYELLOWFG}l{co.BLDORANGEFG}o{co.BLDGREENFG}r{color2use}-coded "
                                    f"list of files and/or subdirectories in a directory. (colorization based on file extension)")

                line += f"\n\n{co.BLDWHITEFG} --> This command supports ALL of the following DOS DIR command parms: " +\
                        f"{co.DIMWHITEFG}(as well as a few of it's own...)"

            elif any(ext in line for ext in ["DIR [drive:]", "[/O[[:]sortorder]]", "[drive:]", "Specifies "]):
                color2use = co.BLDYELLOWFG
                line = line.replace("[drive:][path][filename]", "[[drive:][path][filename]...]")
                line = line.replace(f"[", f"{co.DIMREDFG}[{color2use}")
                line = line.replace(f"]", f"{co.DIMREDFG}]{color2use}")
                line = line.replace("DIR ", f"{co.BLDREDFG}CDIR{color2use} ")
                line = line.replace("Specifies drive, directory, and/or files to list.", f"Specifies drive, and/or directory, and/or files to list.{co.DIMWHITEFG}  Multiple filespecs may be specified and are delimited by spaces.  Use quotes if necessary.")
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

        print(f"\n\t{co.BLDWHITEFG}The following are special parms and are handled apart from DOS DIR parms:{co.ENDC}")
        print(f"\n{co.BLDWHITEFG}      /0          {co.DIMWHITEFG}DEBUG mode (advanced use only){co.ENDC}")
        print(f"{co.BLDWHITEFG}      /1          {co.DIMWHITEFG}DEBUG mode (show ext dtls/advanced use only){co.ENDC}")
        print(f"{co.BLDWHITEFG}      /notypeapp  {co.DIMWHITEFG}Suppresses Type/App column{co.ENDC}")

        title_color = co.BLDWHITEFG
        pnemonic_color = co.BLDWHITEFG
        dash_color = co.DIMWHITEFG
        desc_color = co.DIMWHITEFG
        print(f"""\n{title_color}    File attribute flags are as follows;
        {pnemonic_color}r{dash_color} - {desc_color}read-only bit set
        {pnemonic_color}h{dash_color} - {desc_color}hidden file
        {pnemonic_color}s{dash_color} - {desc_color}system file
        {pnemonic_color}d{dash_color} - {desc_color}directory
        {pnemonic_color}a{dash_color} - {desc_color}archive bit set
        {pnemonic_color}n{dash_color} - {desc_color}normal file
        {pnemonic_color}t{dash_color} - {desc_color}temp file
        {pnemonic_color}c{dash_color} - {desc_color}compressed file
        {pnemonic_color}o{dash_color} - {desc_color}offline file
        {pnemonic_color}e{dash_color} - {desc_color}encrypted
        {pnemonic_color}i{dash_color} - {desc_color}no index file/dir
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

# def parse_parms() -> tuple[ArgumentParser, Namespace, list[str]]:
#
#     import argparse
#     # global gargs
#     @lru_cache(maxsize=None, typed=True)
#     def str2bool(v: str) -> bool | None:
#         if isinstance(v, bool):
#             return v
#         if v.lower() in ('yes', 'true', 'on'):
#             return True
#         elif v.lower() in ('no', 'false', 'off', 'none'):
#             return False
#         # else:
#         #     return True
#         # raise argparse.ArgumentTypeError(f"Boolean value expected. You used '{v}'. Please choose from the "
#         #                                  f"following: 'yes', 'true', 'on' or omit altogether for TRUE; 'no', "
#         #                                  f"'false' or 'off' for FALSE")
#
#     @lru_cache(maxsize=None, typed=True)
#     def str2none(v: str) -> str | None:
#         if isinstance(v, bool):
#             return v
#         # if v.lower() in ('yes', 'true', 't', 'on'):
#         #     return True
#         elif v.lower() in ('no', 'false', 'f', 'off', 'none', ''):
#             return None
#         else:
#             return v
#             # raise argparse.ArgumentTypeError(f"Negative-type value expected. You used '{v}'. Please choose from the following: 'no', 'false', 0 , 'off', 'no' or leave blank for [DEFAULT] value.")
#
#     @lru_cache(maxsize=None, typed=True)
#     def str2int(v: str) -> int | None:
#         if isinstance(v, int):
#             return v
#         if v.lower() in ('yes', 'true', 't', 'on'):
#             return int(v)
#         elif v.lower() in ('no', 'false', 'f', 'off', None):
#             return None
#         else:
#             return int(v)
#
#     @lru_cache(maxsize=None, typed=True)
#     def str2float(v: str) -> float | None:
#         if isinstance(v, float):
#             return v
#         if v.lower() in ('yes', 'true', 't', 'on'):
#             return float(v)
#         elif v.lower() in ('no', 'false', 'f', 'off'):
#             return None
#         else:
#             return float(v)
#
#     def to_dict(argv: list[str]) -> dict:
#         """
#         Converts a list of command-line arguments into a dictionary.
#
#         This function scans through a list like sys.argv and builds a dictionary
#         where each key is an option (starting with '-') and its value is the
#         next argument (unless it's another option, in which case the value is None).
#
#         Parameters:
#             argv (list[str]): The list of command-line arguments.
#
#         Returns:
#             dict: A dictionary mapping argument names to their values or None.
#
#         Example:
#             argv = ['script.py', '--title', 'Inception', '--debug', '--count', '3']
#             to_dict(argv) returns:
#             {
#                 '--title': 'Inception',
#                 '--debug': None,
#                 '--count': '3'
#             }
#         """
#         args = {}
#         i = 1  # Skip script name
#         while i < len(argv):
#             arg = argv[i]
#             if arg.startswith('-'):
#                 while True:
#                     if i + 1 < len(argv) and not argv[i + 1].startswith('-'):
#                         if not args.get(arg):
#                             args[arg] = argv[i + 1]
#                         else:
#                             args[arg] += ' ' + argv[i + 1]  # if args.get(arg) else ""
#                         i += 1
#                         # if i < len(argv) and not argv[i].startswith('-'):
#                         #     args[arg] += argv[i]
#                         # else:
#                         #     args[arg] = None
#                     else:
#                         i += 1
#                         # args[arg] = f"{args[arg]}".strip() if args.get(f"{arg}") else ""
#                         args[arg] = f"{args[arg]}" if args.get(f"{arg}") else None
#                         break
#                 # commented-out because of losing surrounding spaces inside quoted args
#                 # args[arg] = f"{args[arg]}".strip() if args.get(f"{arg}") else None
#                 # args[arg] = f"{args[arg]}".strip() if args.get(f"{arg}") else None
#             else:
#                 i += 1
#
#         return args
#
#     def parse_int(p_value: str) -> int:
#         try:
#             # Remove commas and convert to integer
#             return int(str(p_value).replace(',', ''))
#         except ValueError:
#             raise argparse.ArgumentTypeError(f"{co.FAIL}Invalid integer value: {p_value}{co.ENDC}")
#         # finally:  # only gets here from except-block
#         #     return 0
#
#     # def add_visible_argument(group, *arg_names, **kwargs) -> None:
#     def add_bool_argument(group: argparse._ArgumentGroup, *arg_names: str, **kwargs: Any) -> None:
#         """
#          Adds boolean arguments to an argparse group with centralized control.
#
#          Args:
#              group (argparse._ArgumentGroup): The argument group to add the argument to.
#              *arg_names (str): The argument names (e.g., '-a', '--argument').
#              **kwargs (Any): Additional keyword arguments passed to `add_argument`.
#
#         Return:
#              None: None
#          Raises:
#              ValueError: If no argument names are provided or if argument names do not start with '-'.
#              TypeError: If `arg_names` contains 'nargs', 'const', or 'type' as this func hard-codes them..
#
#          Note:
#              Will raise an error if `arg_names` contains 'nargs', 'const', or 'type'.
#          """
#
#         arg_names = [arg for arg in arg_names if arg and arg.strip()]
#
#         if not arg_names:
#             raise ValueError(f"{co.FAIL}No argument names provided.{co.ENDC}")
#
#         # must have at least one optional-style name
#         if not any(arg.startswith('-') for arg in arg_names):
#             raise ValueError(
#                 f"{co.FAIL}Expected optional-style arguments (starting with '-') in {co.WARNING}{arg_names}{co.ENDC}")
#
#         # Find the first long-form argument
#         parm_name = next((arg for arg in arg_names if arg.startswith('--')), arg_names[0])
#
#         # If help text contains '{parm_name}', replace it
#         help_text = kwargs.get('help')
#         if help_text and '{parm_name}' in help_text:
#             kwargs['help'] = help_text.format(parm_name=parm_name)
#
#         default = kwargs.pop('default', False)  # True/False toggle-switches usually start-out at default False
#         nargs = kwargs.pop('nargs', '?')  # default to 0 or more values
#         type = kwargs.pop('type', str2bool)  # Allow override of our custom handler
#
#         # Ensure we are matching the exact structure in the example you gave
#         group.add_argument(*arg_names,
#                            nargs=nargs,  # zero or one arg afterwards (True/False).  str2bool handles values.
#                            const=True,
#                            default=default,
#                            type=type,
#                            # validates and manipulates True/False switches (use '<parm> False' for merge to turn back-off)
#                            **kwargs
#                            )
#
#     def add_str_value_argument(group: argparse._ArgumentGroup, *arg_names, **kwargs):
#         """
#         Handles arguments that take one or more values, and supports disabling via 'off', 'none', etc.
#         """
#         arg_names = [arg for arg in arg_names if arg and arg.strip()]
#
#         # if not arg_names:
#         #     raise ValueError("No argument names provided.")
#         # if not any(arg.startswith('-') for arg in arg_names):
#         #     raise ValueError(f"Expected optional-style arguments in {arg_names}")
#         # Check for conflicting kwargs that we are hard-coding
#         for arg in ['type', 'default', 'nargs']:
#             if arg in kwargs:
#                 # raise ValueError(f"Conflict: '{arg}' is already hard-coded and cannot be passed in **kwargs.")
#                 # print(f"You specifically specified '{arg}' in a call to add_value_argument() in **kwargs.  This will override specific behavior(s). Please review!") if '--verbose' in sys.argv else None
#                 pass
#
#         # we allow override of all hard-coded parms for add_argument by including in and extracting from **kwargs above
#         #  and passing as hard vars below
#         default = kwargs.pop('default', None)
#         nargs = kwargs.pop('nargs', '*')  # default to 0 or more values
#         # Use custom type str2none to handle 'off' => None logic by default
#         type = kwargs.pop('type', str2none)  # Allow override of our custom handler
#         group.add_argument(*arg_names,
#                            nargs=nargs,
#                            default=default,
#                            type=type,
#                            **kwargs)
#
#     def add_int_value_argument(group: argparse._ArgumentGroup, *arg_names, **kwargs):
#         """
#         Handles arguments that take one or more values, and supports disabling via 'off', 'none', etc.
#         """
#         arg_names = [arg for arg in arg_names if arg and arg.strip()]
#
#         # if not arg_names:
#         #     raise ValueError("No argument names provided.")
#         # if not any(arg.startswith('-') for arg in arg_names):
#         #     raise ValueError(f"Expected optional-style arguments in {arg_names}")
#         # Check for conflicting kwargs that we are hard-coding
#         for arg in ['type', 'default', 'nargs']:
#             if arg in kwargs:
#                 # raise ValueError(f"Conflict: '{arg}' is already hard-coded and cannot be passed in **kwargs.")
#                 # print(f"You specifically specified '{arg}' in a call to add_value_argument() in **kwargs.  This will override specific behavior(s). Please review!") if '--verbose' in sys.argv else None
#                 pass
#
#         # we allow override of all hard-coded parms for add_argument by including in and extracting from **kwargs above
#         #  and passing as hard vars below
#         default = kwargs.pop('default', None)
#         nargs = kwargs.pop('nargs', '?')  # default to 0 or 1 values
#         # Use custom type str2none to handle 'off' => None logic by default
#         type = kwargs.pop('type', str2int)  # Allow override of our custom handler
#         group.add_argument(*arg_names,
#                            nargs=nargs,
#                            default=default,
#                            type=type,
#                            **kwargs)
#
#     def add_float_value_argument(group: argparse._ArgumentGroup, *arg_names, **kwargs):
#         """
#         Handles arguments that take one or more values, and supports disabling via 'off', 'none', etc.
#         """
#         arg_names = [arg for arg in arg_names if arg and arg.strip()]
#
#         # if not arg_names:
#         #     raise ValueError("No argument names provided.")
#         # if not any(arg.startswith('-') for arg in arg_names):
#         #     raise ValueError(f"Expected optional-style arguments in {arg_names}")
#         # Check for conflicting kwargs that we are hard-coding
#         for arg in ['type', 'default', 'nargs']:
#             if arg in kwargs:
#                 # raise ValueError(f"Conflict: '{arg}' is already hard-coded and cannot be passed in **kwargs.")
#                 # print(f"You specifically specified '{arg}' in a call to add_value_argument() in **kwargs.  This will override specific behavior(s). Please review!") if '--verbose' in sys.argv else None
#                 pass
#
#         # we allow override of all hard-coded parms for add_argument by including in and extracting from **kwargs above
#         #  and passing as hard vars below
#         default = kwargs.pop('default', None)
#         nargs = kwargs.pop('nargs', '?')  # default to 0 or 1 values
#         # Use custom type str2none to handle 'off' => None logic by default
#         type = kwargs.pop('type', str2float)  # Allow override of our custom handler
#         group.add_argument(*arg_names,
#                            nargs=nargs,
#                            default=default,
#                            type=type,
#                            **kwargs)
#
#     def merge_namespaces_preserve_saved(saved_ns: Namespace, current_ns: Namespace,
#                                         explicit_keys: set[str]) -> Namespace:
#         """
#         Merge two Namespace objects such that values from the saved namespace are used by default,
#         but for any keys explicitly specified that exist in the current namespace, the current
#         namespace's values are preserved.
#
#         The function works as follows:
#           1. Create a copy (as a dictionary) of all attributes from the saved namespace.
#           2. For each key in the provided `explicit_keys` set, if the current namespace has an
#              attribute with that key, update the saved copy's value for that key with the value
#              from the current namespace.
#           3. Iterate over the merged key-value pairs and set every attribute on the current namespace.
#           4. Return the modified current namespace.
#
#         This approach allows you to "preserve" explicitly provided options from the current namespace,
#         while filling in any missing values from the saved namespace.
#
#         Args:
#             saved_ns (Namespace): The namespace object containing previously saved or default values.
#             current_ns (Namespace): The namespace object with current values, possibly including
#                                     overrides for some keys.
#             explicit_keys (set[str]): A set of attribute names for which values in the current namespace
#                                       should override those from saved_ns.
#
#         Returns:
#             Namespace: The current namespace updated with the merged values from both saved_ns and current_ns.
#                        Attributes corresponding to the keys in `explicit_keys` will reflect the current_ns values,
#                        while all other attributes will come from saved_ns (if not present in current_ns).
#
#         """
#         merged = vars(saved_ns).copy()
#         for key in explicit_keys:
#             if hasattr(current_ns, key):
#                 merged[key] = getattr(current_ns, key)
#         for k, v in merged.items():
#             setattr(current_ns, k, v)
#         return current_ns
#
#     # TODO: Add parms to update both OMDB and Spotify Keys in keys.pkl
#     # let's see if we need to do any setup to raw, pre-argparse command-line parms/args before we start
#     orig_argv = copy.deepcopy(sys.argv)
#     # TODO: accept different root dir (override %USERPROFILE%) thru parm
#     # TODO: accept parms for cache, parms, keys directories
#     # TODO Redo help system and add templates
#     if "--rerun" in orig_argv:
#         new_args = [orig_argv[0], "--rerun"]
#         if "--dry-run" in orig_argv:
#             new_args.append("--dry-run")
#         sys.argv = new_args
#
#     hilite_color = co.BLDGREENFG
#     normal_color = co.GREENFG
#     parm_color = co.DIMBLUEFG
#     # parm_color   = hilite_color
#     help_text_bool_off = (
#                 f" Specify '{parm_color}--%(dest)s{hilite_color} off | no | False{normal_color}' to turn off explicitly. This is helpful in a" +
#                 f" {parm_color}--rerun-merge{normal_color} or {parm_color}--rerun-merge-save{normal_color} situation " +
#                 "to turn a previously specified True/False parameter from True back to False. ")
#
#     help_text_val_off = f" Specify '{parm_color}--%(dest)s{normal_color}' w/no value to return it to its' un-specified (i.e. default) value. This is helpful in a " \
#                         f"{parm_color}--rerun-merge{normal_color} or {parm_color}--rerun-merge-save{normal_color} " \
#                         f"scenario to reverse this parm from having been specified previously. "
#
#     help_text_tail = f"{hilite_color}(default : %(default)s){normal_color}"
#     help_text_tail2 = f"{hilite_color}(default : {parm_color}--set-max-items{hilite_color}){normal_color}"
#
#     # TODO: Create comprehensive Help system using templates, colors and vars for substitution
#     parser_lcl = ColoredPaginatedArgumentParser(
#         description=f'{co.MAGENTAFG}***** MM Updater™ - Metadata updater from IMDB via OMDB © 2024 *****',
#         formatter_class=ColoredHelpFormatter,
#         epilog=f"""
#
#         {normal_color}Modes:
#             TitleID-driven
#                 - By specifying TitleID(s) (Ex. {parm_color}--title-id tt063456 tt769345{normal_color}), you will only process records having those TitleID(s).  This is usually, but not always, 1 record per TitleID.
#                 - When specifying TitleID(s) you will ignore the record limits {parm_color}--set-max-items{normal_color}, {parm_color}--set-max-movies{normal_color} and {parm_color}--set-max-series{normal_color}.
#                 - The program will also not use the standard "Custom4 = 'ready'" which looks to see if the Custom4 field has the value of 'ready'.
#
#             --set-redo-code{normal_color}
#                 - By specifying this parm (& code), you will process every record matching the rest of the criteria
#
#             \n{normal_color}Introducing the {co.MAGENTAFG}MM Updater™ Metadata from IMDB via OMDB{normal_color}  \u00A9 2024 – an innovative, next-generation utility
#               engineered to revolutionize your file metadata management experience. Effortlessly glide through large and small Media Monkey databases
#               structures with unparalleled precision and speed. Empower your workflow with intelligent metadata searching,
#               ensuring seamless manipulation across vast media-file ecosystems. Say goodbye to mundane manual updating and say hello to
#               exciting, streamlined, intuitive, and adaptive MM metadata exploration. Perfect for professionals, aficionados and enthusiasts
#               alike, IntelliPath™ brings the future of file metadata organization to your fingertips.
#              Copyright © 2024{co.ENDC}"""
#     )
#
#     parser_lcl.max_help_position = 120
#
#     # s_multiargs = "If multiple args (or possible unquoted arg with embedded spaces) then will be concatenated to one arg."
#     # TODO: add parm for MM database location/name (especially handy for portable MM installation)
#     #       - wouldn't be able to use ActiveX control
#     #       - Might need coalation UI???
#     #       -
#
#     # --- GROUP 1 --- Media Selection & Limits
#     group = parser_lcl.add_argument_group("CDir Options/Settings")
#
#     add_bool_argument(group, '--reset', default=False, nargs='?',
#                       help=f'This will process a  reset of the extension cache. This may result in slower processing until the'
#                            f'cache is rebuilt as seperate runs of CDir encounter new extensions.'
#                            f'{help_text_bool_off} {help_text_tail}'
#                       )
#     add_bool_argument(group, '--col-typeapp', default=False,
#                       help=f'This will add the column showing the file type and app used to open/launch if available. '
#                            f'{help_text_bool_off} {help_text_tail}')
#
#     add_bool_argument(group, '--no-detail', default=False,
#                       help=f'This will process all files/dirs but not display any detail; only extension totals. '
#                            f'{help_text_bool_off} {help_text_tail}')
#
#     add_bool_argument(group, '--no-extsum', default=False,
#                       help=f'This will process all files/dirs but not display any detail; only extension totals. '
#                            f'{help_text_bool_off} {help_text_tail}')
#
#     add_int_value_argument(group, '-x', '--set-max-items', type=str2int, default=5, nargs='?',
#                            help=f"This sets the maximum number of files, per media-type (i.e. {parm_color}--movies{normal_color}, {parm_color}--episodes"
#                                 f"{normal_color}) to process. "
#                                 f"Use '0' just to check how many records would be processed. "
#                                 f'If running both "{parm_color}--movies{normal_color}" and "{parm_color}--series{normal_color}", and you want "'
#                                 f'different limit values, use "{parm_color}--set-max-movies{normal_color}" and '
#                                 f'"{parm_color}--sets-max-series{normal_color}". '
#                                 f"{help_text_val_off} {help_text_tail}")
#
#     add_int_value_argument(group, '-y', '--set-max-movies', type=str2int, default=-1,
#                            help=f"This sets the maximum number of movies to process. Specifying this parm overrides {parm_color}--set-max-items{normal_color} "
#                                 f"for Movies. Use '0' just to check how many movies could be processed. "
#                                 f"{help_text_val_off} {help_text_tail2}")
#
#     add_int_value_argument(group, '-z', '--set-max-series', type=str2int, default=-1,
#                            help=f"This sets the maximum number of episodes to process. Specifying this parm overrides {parm_color}--set-max-items{normal_color} "
#                                 f"for Series/Episodes. Use '0' just to check how many episodes could be processed. "
#                                 f"{help_text_val_off} {help_text_tail2}")
#
#     add_int_value_argument(group, '--set-max-albums', type=str2int, default=10,
#                            help=f"This sets the maximum number of albums to list for a particular song title in the Comment section. "
#                                 f"{help_text_val_off} {help_text_tail2}")
#
#     add_int_value_argument(group, '-w', '--set-max-tracks', type=str2int, default=-1,
#                            help=f"This sets the maximum number of music Tracks to process. Specifying this parm overrides "
#                                 f"{parm_color}--set-max-items{normal_color} for music Tracks. Use '0' just to check how many tracks could be processed. "
#                                 f"{help_text_val_off} {help_text_tail2}")
#
#     add_str_value_argument(group, '--title-id', nargs='+', default=None,
#                            help=f"Manually specify {hilite_color}IMDB ID(s){normal_color} to process these and ONLY these. If this is specified, all other limits for movies "
#                                 f"and episodes will be ignored. \n"
#                                 f'Example: "{parm_color}--title-id{hilite_color} tt0111161 tt0068646 [...]{normal_color}" '
#                                 f"If --tracks is also specified, any values specified here will not apply there."
#                                 f'{help_text_val_off} {help_text_tail}')
#
#     add_str_value_argument(group, '--track-id', nargs='+', default=None,
#                            help=f"Manually specify {hilite_color}Spotify Track ID(s){normal_color} to process these and ONLY these. If this is specified, "
#                                 f"all limits for music will be ignored. \n"
#                                 f'Example: "{parm_color}--track-id{hilite_color} 1Ud6moTC0KyXMq1Oxfien0 1Ud6moTC0KyXMq1Oxfien0 [...]{normal_color}" '
#                                 f"If --movies and/or --episodes is also specified, any values specified here will not apply there."
#                                 f'{help_text_val_off} {help_text_tail}')
#
#     add_int_value_argument(group, '--set-redo-code', default=-1, nargs='?',
#                            help=f'This INITIATES '
#                                 f'a full table update (as per specified and default parms). '
#                                 f'This also sets the code (use any number) to mark a record as having been modified during a full-table update.  '
#                                 f'By default, this batch-update method will only affect those records that do not already have this particular code set. This '
#                                 f"""allows possible restart after interruption. To override this behavior, specify {parm_color}--set-repl-where{normal_color} to something like {parm_color}--set-repl-where{normal_color} " {hilite_color}Custom5='9'{normal_color} " """
#                                 f'and then this method will only process those records which were last processed with {parm_color}--set-redo-code{hilite_color} 9{normal_color}.  Use 1=1 just to process everything. '
#                                 f'This table update initiates {hilite_color}ONLY{normal_color} if "{parm_color}--title-id{normal_color}" is {hilite_color}NOT{normal_color} also specified, otherwise it just updates and sets the modified code for '
#                                 f'only those specified Title-ID(s) "'
#                                 f'{help_text_val_off} {help_text_tail}')
#
#     add_str_value_argument(group, '--set-repl-where', nargs='?', default=None,
#                            help=f"This REPLACES the existing WHERE clause. If {parm_color}--set-addl-where{normal_color} is also specified then that will be concatenate to this. "
#                                 f"{help_text_val_off} {help_text_tail}")
#
#     add_str_value_argument(group, '--set-addl-where', nargs='?', default=None,
#                            help=f"This ADDS an additional WHERE clause to the existing where clause (AND will be used to concatenate) used vor updating "
#                                 f"{help_text_val_off} {help_text_tail}")
#
#     add_bool_argument(group, '--dry-run', default=False,
#                       help=f"This runs the program w/out making any changes to MM data via SQL. This parm may be used in conjunction with "
#                            f"{parm_color}--rerun{normal_color} to see what the last command would currently do. "
#                            f"{help_text_bool_off} {help_text_tail}")
#
#     # --- GROUP 2 --- Metadata Retrieval Options
#     group2 = parser_lcl.add_argument_group("Metadata Retrieval Options")
#
#     add_bool_argument(group2, '--imdb-only', default=False,
#                       help=f"This searches IMDB-only (very detailed info) and requires the IMDB title-id be populated (in Custom3) to do so. It is important "
#                            f"to get the title-id into the "
#                            f"Custom3 column first  in MM (see {parm_color}--omdb-only{normal_color} on how to do this automatically or manually input the "
#                            f"title-id directly into Custom3). The title-id for a Movie or Episode may "
#                            f"be obtained by going to IMDB and finding the movie and then copying the title-id from the URL for that Movie or Episode page. "
#                            f"{help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group2, '--omdb-only', default=False,
#                       help=f"WARNING: This will overwrite more detailed IMDB data (if already populated) with simple data. \nThis searches "
#                            f"OMDB-only (no IMDB). This is especially helpful if you are simply working on getting the title-id(s) for "
#                            f"movie(s)/series based on what is in MM for series->season->episode for Episodes and title->year for Movies. If these "
#                            f"are correct (or at least match IMDB) Then {parm_color}--omdb-only{normal_color} should automatically obtain the title-id and very basic info "
#                            f"on Cast/Crew.  This is the {hilite_color}ONLY way to get title-id automatically{normal_color}.  "
#                            f"This is also the only way to get the Rotten Tomatoes score. "
#                            f"{help_text_bool_off} {help_text_tail}")
#
#     # add_bool_argument(group2, '--full-credits-only', default=False,
#     #                   help=f"This handles some internals so that only full-credits satisfy requirements. (could cause multiple page refreshes) {help_text_bool_off} {help_text_tail}")
#
#     # add_bool_argument(group2, '--no-credits', default=False,
#     #                   help=f"This turns-off adding credits to the producer/director/writers names. This reduces to one entry in system table per person. {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group2, '--trackid-update', default=False,
#                       help=f"This updates (i.e. replaces) any track-id that pre-exists if a different one turns-out to be a better match. "
#                            f" {help_text_bool_off} {help_text_tail}")
#
#     # add_bool_argument(group2, '--no-animators', default=False,
#     #                   help=f"This stops Animators/Artists/Visual-Effects artists from being added to the description (normally they do if Animators exist in credits). "
#     #                        f" {help_text_bool_off} {help_text_tail}")
#
#     add_int_value_argument(group2, '--set-max-retries', default=10,
#                            help=f"This sets the maximum number of retries when getting metadata from the web (i.e. not avail. in cache).  To set the maximum number of errors before the program ends, see {parm_color}--set-max-errs{normal_color}. {help_text_tail}")
#
#     add_int_value_argument(group2, '--set-max-errs', default=5,
#                            help=f"This sets the maximum number of errors before program ends for that media type. {help_text_tail}")
#
#     add_int_value_argument(group2, '--set-cache-age', default=180,
#                            help=f"This sets the number of days a cached movie/episode/track may still be retrieved before being refreshed with non-cached data {help_text_tail} ")
#
#     add_float_value_argument(group2, '--set-min-delay', type=str2float, default=0.25,
#                              help=f"This sets the minimum number of seconds to wait for non-cached attempts when getting metadata. {help_text_tail} ")
#
#     add_float_value_argument(group2, '--set-max-delay', type=str2float, default=0.75,
#                              help=f"This sets the maximum number of seconds to wait for non-cached attempts when getting metadata. {help_text_tail} ")
#
#     # --- GROUP 3 --- Runtime & Behavior Settings
#     group3 = parser_lcl.add_argument_group("Runtime & Behavior Settings")
#
#     add_str_value_argument(group3, '-l', '--logging', nargs='+', default=None,
#                            help=f"Enable logging using the specified drive directory and file. Will replace file if it exists. {help_text_val_off} "
#                                 f"{help_text_tail}")
#
#     add_bool_argument(group3, '--verbose', default=False,
#                       help=f"This enables step-by-step status updates. {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--profiling', default=False,
#                       help=f"This turns-on profiling for the app. {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--rerun', default=False,
#                       help=f"This loads the parameters that were used last time the program was run.{hilite_color} Ignores any other parms specified this time except {parm_color}--dry-run{normal_color}. "
#                            f"{help_text_tail}")
#
#     add_bool_argument(group3, '--rerun-merge', default=False,
#                       help=f"This loads the parameters that were used last time the program was run. Any add'l parms specified this time are added (and override "
#                            f"saved values individually) but {hilite_color}ARE NOT{normal_color} themselves saved (see {parm_color}--rerun-merge-saved{normal_color}). {help_text_tail}")
#
#     add_bool_argument(group3, '--rerun-merge-save', default=False,
#                       help=f"This loads the parameters that were used last time the program was run. Any add'l parms specified this time are added (and override "
#                            f"saved values individually) and {hilite_color}ARE{normal_color} themselves saved). {help_text_tail}")
#
#     add_bool_argument(group3, '--nocolor', default=False,
#                       help=f"This turns-off color output to screen (logs are always b/w). {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--no-logbw', default=False,
#                       help=f"This turns-off B&W normally used for logging and uses the ASCII color codes seen in screen output. This will have no impact if {parm_color}--nocolor{normal_color} is also used.{help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--no-cache', default=False,
#                       help=f"This turns-off caching entirely.  This includes checking version and aging functionality. {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--force-cache', default=False,
#                       help=f"This forces caching refresh.  This will delete the cache-file so it may be recreated from scratch. {help_text_bool_off} {help_text_tail}")
#
#     add_int_value_argument(group, '--set-cache-compress', type=str2int, default=9,
#                            help=f"This sets the level of compression used in cache files.  Ex. {parm_color}--set-cache-compress{hilite_color} 2 "
#                                 f"{normal_color}sets the compression level to 9 (0-9) for any caches being written this session."
#                                 f"A lower compression level means larger cache files but faster access later.  This is usually best left at "
#                                 f"default (%(default)s) but can be changed for existing cache files, en masse, by using "
#                                 f"{parm_color}--force-cache{normal_color} and {parm_color}--dry-run{normal_color} in addition."
#                                 f"{help_text_val_off} {help_text_tail2}")
#
#     add_bool_argument(group3, '--no-logvars', default=False,
#                       help=f"This turns-off adding parms to the log file name (used to prevent too-long filenames). {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--no-logdt', default=False,
#                       help=f"This turns-off adding date/time to the log file name (used to append to existing log). {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--nobanner', default=False,
#                       help=f"This turns-off banner display. {help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--force-image', default=False,
#                       help=f"This overwrites the image (poster/cd cover) file if it exists. (no warning before overwrite). "
#                            f"{help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--suppress-sql', default=False,
#                       help=f"This ONLY SUPPRESSES DISPLAY of the SQL string to be used to update a record in the MediaMonkey database for that Movie/Episode. "
#                            f"{help_text_bool_off} {help_text_tail}")
#
#     add_bool_argument(group3, '--no-sound', default=False,
#                       help=f"This Turns-off sounds for the application. Sounds and volume will otherwise follow Windows settings. "
#                            f"{help_text_bool_off} {help_text_tail}")
#
#     # --- HIDDEN ARGS ---
#     group3.add_argument('--ghfw', type=str, default="py.exe", help=argparse.SUPPRESS)
#
#     add_bool_argument(group3, '-i', '--case-sensitive', default=False, help=argparse.SUPPRESS)
#
#     add_bool_argument(group3, '-d', '--debug', default=False, help=argparse.SUPPRESS)
#
#     group3.add_argument('-v', '--version', action='version',
#                         default=f">>---> MMUp ver. 0.8.0",
#                         version=f"{co.GREENFG}>>---> {co.GREENFG}MMUp {co.YELLOWFG}ver. 0.8.0 {co.ENDC}")
#
#     # Now, let's get parsing
#     gargs_lcl = parser_lcl.parse_args()
#     gargs_lcl_orig = copy.deepcopy(gargs_lcl)
#
#     def handle_none_argument(arg_name: str, args: argparse.Namespace, parser: argparse.ArgumentParser):
#         """
#         Return the current value for an argument, or its default if:
#         - the value is None
#         - the value is a list containing only None
#         """
#         val = getattr(args, arg_name)
#         if val is None or (isinstance(val, list) and set(val) == {None}):
#             return parser.get_default(arg_name)
#         return val
#
#     # these parms take 1 (or more) args and if no arg is present they should be set to their default value
#     args_to_process = [
#         'title_id',
#         'track_id',
#         'set_addl_where',
#         'set_repl_where',
#         'set_max_items',
#         'set_max_movies',
#         'set_max_series',
#         'set_max_tracks',
#         'set_max_albums',
#         'set_min_delay',
#         'set_max_delay',
#         'set_redo_code',
#         'set_max_retries',
#         'set_max_errs',
#         'set_cache_compress',
#         'set_cache_age',
#         'logging'
#     ]
#
#     # extracts the arguments for a cli parm from argv
#     def get_argv_param(param_name: str, default=None, argv=None):
#         # FOR DEBUGGING
#         if param_name == '--logging' or param_name == '--title-id':
#             pass
#         argv = argv or sys.argv
#         if param_name in argv:
#             index = argv.index(param_name)
#             args = ""
#             try:
#                 for arg in argv[index + 1:]:
#                     if arg.startswith("-"):
#                         break
#                     else:
#                         args += f"{arg} "
#
#                 return args.strip()
#             except IndexError:
#                 return default  # No value provided after the param
#
#         return default
#
#     def merge_argvs(saved_argv: list[str],
#                     current_argv: list[str],
#                     parser: ArgumentParser) -> list[str]:
#         """
#             Merge two lists of command-line arguments using an ArgumentParser to resolve flag mappings.
#
#             This function takes a list of previously saved command-line arguments (saved_argv) and a list of
#             current command-line arguments (current_argv), and merges them into one cohesive argument list.
#             The merging process relies on the flag-to-destination mapping provided by the parser to determine
#             which argument values should be used. Current arguments take precedence over saved arguments.
#
#             The process follows these steps:
#               1. Convert both saved_argv and current_argv into dictionaries using the helper function `to_dict()`.
#                  These dictionaries map command-line flags to their associated values.
#               2. Obtain two mappings from the parser by calling `build_dest_to_flag_map(parser)`:
#                  - `dest_to_flag`: maps a destination (i.e. the internal name of a command-line option) to its flag.
#                  - `flag_to_dest`: maps a flag (as it appears on the command line) to its destination.
#               3. Construct two dictionaries (`saved_dests` and `current_dests`) that map each destination
#                  (obtained via flag lookup) to a tuple (flag, value) derived from the saved and current arguments.
#               4. Merge the two dictionaries such that the current arguments override any conflicting saved arguments.
#               5. Rebuild a merged argument list starting with the executable name (taken from the first element
#                  of current_argv if available, otherwise from saved_argv) and then appending each flag and its
#                  associated value (if not None) as determined by the merged destination mapping.
#
#             Args:
#                 saved_argv (list[str]): A list of saved command-line arguments (usually starting with the executable name).
#                 current_argv (list[str]): A list of current command-line arguments that may override the saved ones.
#                 parser (ArgumentParser): An argparse.ArgumentParser instance that is used to build the mapping between
#                     command-line flags and their destination names. It is assumed that helper functions like
#                     `build_dest_to_flag_map` and `to_dict` are defined elsewhere to support this process.
#
#             Returns:
#                 list[str]: A newly merged list of command-line arguments where the current arguments override the saved
#                     arguments based on their flag-to-destination mapping.
#
#             Example:
#                 Suppose you have:
#                     saved_argv = ["app.py", "--verbose", "False", "--timeout", "10"]
#                     current_argv = ["app.py", "--timeout", "20"]
#                 And the parser maps:
#                     --verbose → dest "verbose"
#                     --timeout → dest "timeout"
#                 Then merge_argvs() will produce:
#                     ["app.py", "--verbose", "False", "--timeout", "20"]
#                 (Because the current timeout value "20" overrides the saved value "10".)
#
#             Note:
#                 - This function uses deep copies of the input argument lists to avoid side effects.
#                 - It assumes that the helper functions `to_dict()` and `build_dest_to_flag_map(parser)` are
#                   implemented and function correctly to map argument flags to their corresponding destinations.
#             """
#
#         # import copy
#
#         def build_dest_to_flag_map(parser: ArgumentParser) -> tuple[dict[str, str], dict[str, str]]:
#             dest_to_flag = {}
#             flag_to_dest = {}
#             for action in parser._actions:
#                 if not action.option_strings:
#                     continue
#                 preferred_flag = sorted(action.option_strings, key=lambda x: len(x))[-1]  # Prefer long names
#                 for flag in action.option_strings:
#                     flag_to_dest[flag] = action.dest
#                 dest_to_flag[action.dest] = preferred_flag
#             return dest_to_flag, flag_to_dest
#
#         saved_dict = to_dict(copy.deepcopy(saved_argv))
#         current_dict = to_dict(copy.deepcopy(current_argv))
#
#         dest_to_flag, flag_to_dest = build_dest_to_flag_map(parser)
#
#         current_dests = {
#             flag_to_dest[flag]: (flag, val)
#             for flag, val in current_dict.items()
#             if flag in flag_to_dest
#         }
#
#         saved_dests = {
#             flag_to_dest[flag]: (flag, val)
#             for flag, val in saved_dict.items()
#             if flag in flag_to_dest
#         }
#
#         # Combine with current taking precedence
#         merged_dests = {**saved_dests, **current_dests}
#
#         merged = [current_argv[0] if current_argv else saved_argv[0]]
#
#         for dest, (_, val) in merged_dests.items():
#             flag = dest_to_flag.get(dest)
#             merged.append(flag)
#             if val is not None:
#                 merged.append(val)
#
#         return merged
#
#     def merge_args(cli_args, pickle_args, default_args, lock_pickle=False):
#         merged = {}
#
#         all_keys = set(cli_args) | set(pickle_args) | set(default_args)
#
#         for key in all_keys:
#             if lock_pickle:
#                 if key in pickle_args:
#                     merged[key] = pickle_args[key]
#                 elif key in cli_args:
#                     merged[key] = cli_args[key]
#                 else:
#                     merged[key] = default_args.get(key)
#             else:
#                 # existing behavior (CLI overrides everything)
#                 merged[key] = (
#                         cli_args.get(key)
#                         or pickle_args.get(key)
#                         or default_args.get(key)
#                 )
#
#         return merged
#
#     # we process all 1 arg parms to make sure they have 1 parm passed, else we set to default val
#     for arg in args_to_process:
#         setattr(gargs_lcl, arg, handle_none_argument(arg, gargs_lcl, parser_lcl))
#         # handle_none_argument(arg, gargs_lcl, parser_lcl)
#
#     # TODO: Allow the pickle parm to accept path\file
#     #
#     # TODO: allow all dirs to be specified on the command-line
#     pickle_path = rf"{user_profile}CDir"
#     pickle_file = rf"{pickle_path}\CDir_last_run.pk1"
#
#     if not (pickle_path_exists := os.path.exists(pickle_path)):
#         print(f"Creating directory for CDir")
#         try:
#             os.makedirs(pickle_path, exist_0k=False)
#
#         except  FileExistsError:
#             print(f"{co.WARNING}Directory for {co.BLDMAGENTAFG}CDir{co.WARNING} already created (perhaps multi-threaded collision)!!!{co.ENDC}")
#
#     if not (pickle_exists := os.path.exists(pickle_file)):
#         pass
#         # print(f"{co.WARNING}Pickle file does not exist...yet.{co.ENDC}")
#
#     pickle_data = None
#
#     # Flags from CLI
#     parser_flags = {
#         arg.lstrip('-') for arg in sys.argv[1:]
#         # if arg.startswith('--') and not arg.startswith('---')  #  and not arg=='--rerun'  # ignore ---help, etc.
#         if arg.startswith('-') and not arg.startswith('---')  # and not arg=='--rerun'  # ignore ---help, etc.
#     }
#
#     # import pickle
#     #
#     # Determine modes
#     is_rerun_session = gargs_lcl.rerun
#     is_rerun_merge = gargs_lcl.rerun_merge
#     is_rerun_merge_save = gargs_lcl.rerun_merge_save
#
#     should_load_pickle = is_rerun_session or is_rerun_merge or is_rerun_merge_save
#     should_merge_pickle = is_rerun_merge or is_rerun_merge_save
#     should_save_pickle = (
#                                      not is_rerun_session and not is_rerun_merge) or is_rerun_merge_save  # Save only if not rerun or rerun-merge
#     pickle_orig_data = set()
#     merged_argv = []
#     # Load if needed
#     if should_load_pickle:
#         if not pickle_exists:
#             print(f"{co.FAIL}\nUnable to locate last-used parms (pickle) file: {co.WARNING}{pickle_file}{co.ENDC}")
#             exit(1)
#
#         with open(pickle_file, 'rb') as f1:
#             # pickle_data = pickle.load(f)
#             # import pickle
#             pickle_data = copy.deepcopy(pickle.load(f1))
#             # import copy
#             pickle_orig_data = copy.deepcopy(pickle_data)
#             print(
#                 f"{co.SUCCESS}Loaded last-used parm settings (for {co.APPARMS}--rerun{co.SUCCESS}, {co.APPARMS}--rerun-merge{co.SUCCESS} or {co.APPARMS}--rerun-merge-save{co.SUCCESS}){co.ENDC}")  # if gargs_lcl.verbose else None
#             print(f"Pickle Data load = {pickle_orig_data}")  # if gargs_lcl.verbose else None
#
#     # If --rerun (but NO --rerun-merge or --rerun-merge-save) if command-line specified (CLI)
#     if is_rerun_session:
#
#         # we brute-replace argparse with what is in the pickle file for 'args'
#         gargs_lcl = copy.deepcopy(pickle_data['args'])
#         # we brute-replace sys.argv with what is in the pickle file for 'argv'
#         sys.argv = copy.deepcopy(pickle_data['argv'])
#
#         #  if a rerun session and dry-run was specified, then put it back
#         #    as it has been replaced by an older args/argv
#         if "--rerun" in orig_argv:
#             if "--dry-run" in orig_argv and "--dry-run" not in sys.argv:
#                 new_args = sys.argv
#                 new_args.append("--dry-run")
#                 gargs_lcl.dry_run = True
#                 sys.argv = new_args
#
#         # since '--rerun' was specified on the command-line, we'll auto-override
#         #   any (errant) add'l (loaded) rerun settings clean out any old rerun flags in argparse and argv
#         sys.argv = [arg for arg in sys.argv if arg not in ('--rerun-merge', '--rerun-merge-save')]  # filter these out
#         gargs_lcl.rerun_merge = False
#         gargs_lcl.rerun_merge_save = False
#
#     # Merge mode
#     elif should_merge_pickle:
#         gargs_saved = copy.deepcopy(pickle_data['args'])
#         gargs_saved.rerun = False
#         gargs_saved.rerun_merge = is_rerun_merge
#         gargs_saved.rerun_merge_save = is_rerun_merge_save
#
#         sys_argv_saved = copy.deepcopy(pickle_data['argv'])
#         sys_argv_saved = [arg for arg in sys_argv_saved if
#                           not arg.startswith('--rerun-merge') and not arg.startswith('--rerun-merge-save')]
#
#         explicit_argv = {
#             flag.lstrip('-').replace('-', '_')
#             for flag in to_dict(sys.argv)
#         }
#
#         # now, MERGE data!  This has issues shen running under pytest, so, ignore results
#         gargs_lcl = copy.deepcopy(merge_namespaces_preserve_saved(gargs_saved, gargs_lcl, explicit_argv))
#         # sys.argv[:] = (merged_argv := copy.deepcopy(merge_argvs([arg for arg in sys_argv_saved if arg not in ('--rerun-merge', '--rerun-merge-save')], sys.argv, parser_lcl)))
#         # sys_argv_saved = [arg for arg in sys_argv_saved if not arg.startswith('--rerun-merge') and not arg.startswith('--rerun-merge-save')]
#         #   (that stupid colon (i.e. argv[:]) was causing issues in pytest with argv :-( )
#         sys.argv = copy.deepcopy(merged_argv := copy.deepcopy(merge_argvs(sys_argv_saved, sys.argv, parser_lcl)))
#
#     # Save if desired
#     if should_save_pickle:
#         with open(pickle_file, 'wb') as f2:
#             # import pickle
#             pickle.dump(pickle_new_data := {
#                 'args': gargs_lcl,
#                 'argv': sys.argv  # (already merged if applicable)
#                 # 'argv': merged_argv if should_merge_pickle else sys.argv
#                 # 'argv': orig_argv  #  if should_merge_pickle else sys.argv
#             }, f2)
#             print(
#                 f"{co.SUCCESS}\nSaved parm settings for possible {co.APPARMS}--rerun{co.SUCCESS}, {co.APPARMS}--rerun-merge{co.SUCCESS} or " + \
#                 f"{co.APPARMS}--rerun-merge-save{co.SUCCESS} on next run{co.ENDC}") if gargs_lcl.verbose else None
#             print(
#                 f"{co.SUCCESS}Pickle Data save = {co.BLDTEXT}{pickle_new_data}{co.ENDC}") if gargs_lcl.verbose else None
#
#     co.no_color(gargs_lcl.nocolor)  # go B&W if specified
#
#     if gargs_lcl.debug:
#         gargs_lcl.verbose = True
#         print(
#             f"\n\t{co.BLDTEXT}Specifying {co.APPARMS}--debug{co.BLDTEXT} enables {co.APPARMS}--verbose{co.BLDTEXT} automatically.{co.ENDC}\n")
#
#     # if not gargs_lcl.movies and not gargs_lcl.episodes and not gargs_lcl.tracks:
#     #     print(
#     #         f"\n\t{co.FAIL}You must specify {co.APPARMS}-M{co.FAIL} ({co.APPARMS}--movies{co.FAIL}) and/or {co.APPARMS}-E{co.FAIL} ({co.APPARMS}--episodes" + \
#     #         f"{co.FAIL}) and/or {co.APPARMS}-E{co.FAIL} ({co.APPARMS}--tracks{co.FAIL}), in addition to any other paramaters, to run this program.{co.ENDC}")
#     #     exit(1)
#
#     if gargs_lcl.imdb_only and gargs_lcl.omdb_only:
#         gargs_lcl.imdb_only = False
#         print(
#             f"{co.FAIL}You specified both {co.APPARMS}--omdb-only{co.FAIL} and {co.APPARMS}--imdb-only{co.FAIL}.  You may specify ONLY 1 of these!{co.ENDC}")
#         exit(1)
#
#     if gargs_lcl.profiling:
#         print(f"{co.SUCCESS}Profiling enabled: [{gargs_lcl.profiling}]")
#
#     if gargs_lcl.logging:
#         print(f"Logging '{gargs_lcl.logging}'") if gargs_lcl.debug else None
#         files = gargs_lcl.logging
#         # flatten list for Tee Class
#         files = tuple(item for sublist in files for item in (sublist if isinstance(sublist, list) else [sublist]))
#         # let's setup logging
#         # tee = Tee(gargs_lcl,
#         #           False,
#         #           # gargs_lcl.no_logvars,
#         #           # gargs_lcl.no_logdt,
#         #           # gargs_lcl.no_logbw,
#         #           *files,
#         #           sys.stdout,
#         #           tee_stderr=True)
#         # sys.stdout = tee  # Redirect (duplicate, actually) standard screen output to Tee
#         # for tee_file in tee.files[-1:]:
#         #     tee_log_name = tee_file
#         #     print(
#         #         f"{co.SUCCESS}Logging enabled  (tee):{co.BLDTEXT} [{tee_log_name}]{co.ENDC}") if gargs_lcl.verbose else None
#
#     # Function to find corresponding long name
#     def get_long_name(short_name, parser):
#         for action in parser._actions:
#             if short_name in action.option_strings or f"-{short_name}" in action.option_strings:
#                 # Return the longest option string
#                 return max(action.option_strings, key=len)
#         return short_name  # If no match, return original
#
#     # build an array of help=argparse.SUPPRESSED for dim display of
#     suppressed_args = {
#         action.dest for action in parser_lcl._actions
#         if action.help == argparse.SUPPRESS
#     }
#     # Now, let's get the whole parm CLI/Pickle thing printed-out
#     # Nothing here changes anything about argparse or argv, this just categorizes them out for printing on-screen
#     old_val = None
#     if gargs_lcl.verbose:
#
#         # explicit_flags = {arg2.lstrip('-') for arg2 in parser_flags}
#         explicit_flags_mapped = {get_long_name(arg2, parser_lcl).lstrip('-') for arg2 in parser_flags}
#
#         from common_tools.common_tools import quote_args
#         quoted_argv = quote_args(sys.argv)
#
#         for arg in vars(gargs_lcl):
#             # FOR DEBUGGING
#             if arg == 'logging' or arg == 'title_id':
#                 pass
#
#             dashed_arg = f"--{arg.replace('_', '-')}"
#
#             arg_val = getattr(gargs_lcl, arg)
#
#             # we preserve quotes as specified on CLI (or possibly retrieved from Pickle data)
#             arg_val_quoted = get_argv_param(dashed_arg, argv=quoted_argv)
#
#             # we allow flags to be set to true/false by specifying values on CLI
#             arg_val_quoted = False if arg_val_quoted and arg_val_quoted.lower() in {'off', 'false',
#                                                                                     'no'} else arg_val_quoted
#             arg_val_quoted = True if arg_val_quoted and arg_val_quoted.lower() in {'on', 'true', 'yes', '', 'none',
#                                                                                    None} else arg_val_quoted
#
#             old_val = (getattr(gargs_saved, arg) if (should_merge_pickle) else "")
#
#             if is_rerun_session:
#                 new_val = (get_argv_param(dashed_arg, argv=orig_argv) if not (should_merge_pickle) else "")
#
#             # Process all arguments in orig_argv through get_long_name()
#             mapped_orig_argv = {get_long_name(arg2, parser_lcl) for arg2 in orig_argv}
#
#             # Check if the mapped long name exists in the mapped pre-processed argv (mapped_orig_argv)
#             is_explicit_orig_mapped = get_long_name(dashed_arg, parser_lcl) in mapped_orig_argv
#
#             # Process all arguments in orig_argv through get_long_name()
#             mapped_pickle_argv = {get_long_name(arg, parser_lcl) for arg in pickle_data["argv"]} if pickle_data else []
#
#             is_in_pickle_mapped = dashed_arg in mapped_pickle_argv if pickle_data and dashed_arg not in (
#                 '--rerun-merge', '--rerun-merge-save') else False
#
#             # is this parm normally suppressed from display for -h
#             is_suppressed_arg = arg in suppressed_args
#
#             # was this parm specified on the command-line
#             is_explicit_mapped = arg.replace("_", "-") in explicit_flags_mapped
#             # is_explicit_orig = dashed_arg in orig_argv
#
#             # did user specify --rerun on the command-line (CLI) and are we processing that parm
#             #   right now?
#             is_rerun_arg = (dashed_arg == '--rerun' and is_explicit_mapped)
#
#             # if cli specified and also in pickle file, then cli overrides the rerun file if we-re
#             #   using --rerun-merge or --rerun-merge-save (NOT --rerun)
#             cli_override = (
#                                        gargs_lcl.rerun_merge or gargs_lcl.rerun_merge_save) and is_explicit_mapped and is_in_pickle_mapped
#
#             # if cli specified and also in pickle file, then rerun file overrides cli if we-re
#             #   using --rerun (NOT --rerun-merge or --rerun-merge-save)
#             cli_ignored = is_rerun_session and is_explicit_orig_mapped and dashed_arg not in ("--rerun",
#                                                                                               "--rerun-merge",
#                                                                                               "--rerun-merge-save",
#                                                                                               "--dry-run")
#
#             # Skip suppressed args entirely if not cli, pickled or overridden
#             if is_suppressed_arg and not (is_explicit_mapped or is_in_pickle_mapped or cli_override):
#                 continue
#
#             is_default = False
#             # Determine source label
#             if cli_override:
#                 source_text = f"{co.WARNING}[OVERRIDE]"
#
#             elif pickle_data and is_in_pickle_mapped:
#                 source_text = f"{co.CYANFG}[RERUN]   "
#
#             elif is_explicit_mapped:  # or is_explicit_orig:
#                 source_text = f"{co.GREENFG}[CLI]     "
#
#             else:
#                 is_default = True  # used for color formatting
#                 source_text = f"{co.DIMTEXT}[DEFAULT] "
#
#             # all we're doing here is preserving quotes for on-screen disp
#             val_2_disp = arg_val_quoted if arg_val_quoted is not None and arg_val_quoted != '' else arg_val
#
#             # Format line - If we used --rerun then we have to override the last saved value w/CLI (for screen purposes here as well).
#             line = (
#                     f"{source_text} {dashed_arg} : {co.BLDTEXT if is_default else co.SUCCESS}{val_2_disp if not is_rerun_arg else True}{co.ENDC}" +
#                     (
#                         f" {co.WARNING}(overrides : {co.REDFG}{old_val}{co.WARNING}){co.ENDC}" if cli_override else f"{co.ENDC}"
#                     ) +
#                     (
#                         (
#                             f" ({co.WARNING}ignores CLI-[{co.REDFG}{new_val}{co.WARNING}], {co.ENDC}use {co.APPARMS}--rerun-merge{co.BLDTEXT} or {co.APPARMS}--rerun-merge-save{co.BLDTEXT} to override){co.ENDC}") if cli_ignored else f"{co.ENDC}"
#                     )
#             )
#
#             # Dim suppressed non-default args
#             if is_suppressed_arg:  # doesn't get here much
#                 # from common_tools.common_tools import strip_ascii
#                 # print(f"line = {line}")
#                 # print(f"{co.BLDWHITEFG}{MediaStats.strip_ascii(line)}{co.ENDC}")
#                 print(f"{co.DIMWHITEFG}{line}{co.ENDC}")  # if dashed_arg not in ("--ghfw") else None
#             else:
#                 print(line)
#
#     gflags = re.IGNORECASE if not gargs_lcl.case_sensitive else 0  # used for case-sensitivity everywhere
#
#     # print(f"Max Files = {gargs_lcl.set_max_items}")
#     return parser_lcl, gargs_lcl, orig_argv


def format_line(val_2use: str, line: str, color2use: str) -> str:
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
                          indent: str = (' '*11),
                          comma_color: str = f"{co.REDFG}") -> str:
    """
    Wrap `text` preserving words (split on spaces/comma+space boundaries),
    preferring the last space before max_width; if none, use the first space after.
    Subsequent lines are indented to align with the start of the list (indent).
    """
    if indent is None:
        # default indent: everything up to and including "-> " on first line
        if "->" in text:
            prefix, _, rest = text.partition("->")
            indent = " " * (len(prefix) + 3)  # keep a space after arrow

        else:
            indent = ""

    out_lines = []
    s = text.strip()
    s_raw = strip_ascii(s)
    # diff = len(s) - len(s_raw)
    indent_prefix = ""
    indent_prefix = ""
    while s_raw:
        if len(s_raw) <= max_width:
            out_lines.append(s_raw)
            break

        # candidate window
        window = s_raw[:max_width+1]  # allow one char past limit to find a space after
        # try to find last space before or at max_width
        cut = window.rfind(" ", 0, max_width+1)
        if cut == -1:
            # no space before limit: find first space after limit in the remainder
            rest_space = s_raw.find(" ", max_width)
            if rest_space == -1:
                # no space at all: nothing to split on, shove whole remainder
                out_lines.append(s_raw)
                break

            cut = rest_space

        # append the current trimmed piece
        piece = s_raw[:cut].rstrip(", ")+f"{comma_color},{co.BLDWHITEFG}"
        out_lines.append(piece)
        # prepare remainder, trim any leading spaces and commas
        s_raw = s_raw[cut:].lstrip(" ,")
        # prefix subsequent lines with indent if they are continuation of list
        if out_lines and indent:
            # only apply indent to lines after the first
            indent_prefix = indent
            # build next visible line with indent
            # s_raw = indent_prefix + s_raw

    return f"\n{indent_prefix}".join(out_lines)


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
    attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
    if attrs == -1:  # did not find
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


def get_metadata(p_ext: str, p_size: str) -> str | None:
    # Gets assoc. app from API/Registry/DISM extract

    p_ext = p_ext.lower()
    p_size = p_size.strip().replace(",","").replace("(","").replace(")","")
    if not p_ext or p_ext.startswith(('.movie_')):  # or p_ext.startswith((f'.movie_','.dll_','.fon_','.exe_','.mui_','.sys_')):
        print(f"No ext was found or will be cached! [{p_ext}]") if debug else None
        return

    elif p_ext in ext_cache:
        print(f"{p_ext} was cached.") if debug else None

        # ext_cache_ctr[p_ext] += 1
        try:
            ext_cache_ctr[p_ext] += 1
        except KeyError:
            ext_cache_ctr[p_ext] = 1

        try:
            ext_cache_size[p_ext] += int(p_size)

        except KeyError:
            ext_cache_size[p_ext] = int(p_size)

        return ext_cache[p_ext]

    print(f"{p_ext} was NOT cached but now is!") if debug else None

    assoc = None  # ret val from DOS assoc command (e.g. ".exe=exefile")
    assoc_ext = None  # will hold assoc[0] (extension e.g. '.exe')
    assoc_type = None  # will hold assoc[1] (file type e.g. 'exefile')

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
            str_2use2 = f'{str_2use[:4]}...{str_2use[-6:]}'
            str_2use = str_2use2

        return str_2use

    def shorten_app(str_2use: str) -> str:
        print(f"str_2use={str_2use}") if debug else None
        # if str_2use.find(r"C:\Program Files\WindowsApps\Microsoft.Windows") > -1:
        str_2use = str_2use.replace(r"C:\Program Files\WindowsApps\Microsoft.Windows", r"C:\...")
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
            line_1 = f"{registry_srcd}{api_srcd}{prog_reg_id_1}/{ftype_out_1}"

        # if we either don't have a prog_id, or what we got was redundant and/or cryptic (AppX)
        #  we'll just use the output from the 'ftype' DOS command
        else:
            line_1 = f"{registry_srcd}{ftype_out_1}"

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
        line_1 = f'{p_ext}=<undefined>'  # ??? are there any more places to look?

    print(f"line_1={line_1}") if debug else None

    ext_cache[p_ext] = line_1
    ext_cache_ctr[p_ext] = 1

    print()

    print(f"ext_cache[ext]={ext_cache[p_ext]}") if debug else None
    # ext_cache[ext] = ast.literal_eval(ext_cache[ext])

    return ext_cache[p_ext]

def color_2use(p_line: str = "",
               p_ext: str = "") -> str:

    p_line = p_ext if p_ext else p_line
    p_line_lower = p_line.lower()

    if p_ext:
        pass

    if any(ext in p_line for ext in ["<DIR>"]):
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
                              ".com", ".cmd", ".msi", ".wsf", ".cpl", ".ocx", ".js", ".vbs")):
        p_color_2use = co.BLDGREENFG

    # PYTHON related files (perhaps later we add all source-code-related files)
    elif p_line_lower.endswith(
            (".py", ".pyc", ".c", ".cpp", ".h", ".lib", ".msc", ".pyi", ".pyd", ".pyz", ".pyzw", ".toc",
             ".pyw", ".cs", ".asp", ".aspx", ".ascx", ".html", ".htm", ".url", ".css", ".resx",
             "installer", "license", ".metadata", "record", "wheel", "requested", "notice", "authors",
             "copying", "head", "py.typed", "readme.md", ".gitignore")):
        p_color_2use = co.BLUEFG

    # compressed / virtualized
    elif p_line_lower.endswith((".zip", ".gzip", ".gz", ".iso", ".cab", ".vhdx", ".vhd", ".rar", ".7z", ".xz",
                              ".bz2", ".z", ".lz", ".lzma")):
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
             '.wmv', '.flv', '.3gp', '.mpeg', '.mxf', '.braw', '.r3d', '.yuv', '.ts',
             '.m2ts', '.f4v', '.divx', '.rm', '.asf', '.dvr-ms', '.ogv')):
        p_color_2use = co.BLDORANGEFG

    # music files
    elif p_line_lower.endswith(
            (".mp3", ".flac", ".wav", ".m4a", ".m4p", ".ra", ".m3u", ".ogg", ".wma", ".aac",
             ".alac", ".ape", ".wv", ".aiff", ".pcm", ".mka", ".mod", ".xm", ".mid", ".midi",
             ".rmi", ".dts", ".ac3")):
        p_color_2use = co.ORANGEFG

    # e-book / document files
    elif p_line_lower.endswith(
            ('.epub', '.mobi', '.pdf', '.djvu', '.txt', '.log', '.rtf', '.nfo', '.doc', '.docx')):
        p_color_2use = co.DIMGREENFG

    # pic / image files
    elif p_line_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
                              ".tif", ".webp", ".heic", ".heif", ".raw", ".cr2",
                              ".nef", ".arw", ".orf", ".dng", ".svg", ".ai", ".eps",
                              ".ico", ".icns", ".dds", ".exr", ".psd", ".xcf"
                              )):
        p_color_2use = co.DIMBLUEFG

    # system files
    elif p_line_lower.endswith(
            (".dll", ".sys", ".bin", ".inf_loc", ".mui", ".inf", ".cat", ".tlb", ".targets", ".ttf")):
        p_color_2use = co.DIMBLACKFG

    else:
        p_color_2use = co.DIMWHITEFG

    return p_color_2use

if __name__ == '__main__':
    main()
    # return None



# prog_id = ""
# ftype = None
# exit()
# add extension metadata to new dict entry
# ext_cache[ext] = {'type': prog_id or filetype, 'app': filetype, 'ext': ext}
# ext_cache[ext] = {'type': prog_id or prog_id, 'app': ftype, 'ext': ext}
# if not isinstance(ftype, ET.Element):
#     ext_cache[p_ext] = {'type': filetype or prog_id, 'app': ftype, 'ext': p_ext}
#
# else:
#     ext_cache[p_ext] = ftype

#  *.ini  <- no API (assoc) and subsequently no ftype either
#  *.txt
#  *.log
#  *.exe

# if filetype:  # DOS Source
#     ftype_out = subprocess.run(['ftype', filetype], shell=True, capture_output=True, text=True).stdout.strip()
#     ftype = ftype_out.split('=', 1)[1] if '=' in ftype_out else ftype_out
#     # print(f"ftype_out={ftype_out}") if debug else None
#     if ftype_out:
#         ftype = f"{api_srcd}{ftype_out}"
#         print(f"ftype5={ftype}") if debug else None
#     elif not ftype_out:  # Registry Source
#             prog_id = get_user_prog_id(p_ext)
#             print(f"ftype0={ftype}") if debug else None
#             if prog_id:
#                 ftype = get_open_command(prog_id)
#                 ftype = f"{registry_srcd if ftype else ''}{prog_id}={ftype}"
#                 print(f"ftype1={ftype}") if debug else None
#                 filetype=ftype if not filetype else filetype
#                 if not ftype:  # DISM Source
#                     ftype = get_record_by_extension(r'c:\users\emues\AppAssoc.xml', p_ext)
#                     ftype = ET.fromstring(ftype)
#                     ftype = f"{dism_srcd if ftype else ''}{ftype}"
#                     print(f"ftype2={ftype}") if debug else None
#             else:  # DISM Source
#                 ftype = get_record_by_extension(r'c:\users\emues\AppAssoc.xml', p_ext)
#                 if ftype:
#                     ftype = ET.fromstring(ftype)
#                     print(f"ftype3={ftype}") if debug else None
#                     prog_id = ftype.attrib.get("ProgId")
#                     filetype = ftype.get("ApplicationName")
#                     prog_id = (f"{dism_srcd}{prog_id}={filetype}" if prog_id else '')
# else:  # Registry source
#     # ftype = get_record_by_extension(r'c:\users\emues\AppAssoc.xml', p_ext)
#     # ftype = (ET.fromstring(ftype) if ftype is not None else None)
#     #
#     # print(f"ftype4={ftype}") if debug else None
#     # filetype = ftype.get("ApplicationName") if not ftype is None else None
#     # prog_id  = (ftype.get("ProgId") if not ftype is None else None)
#     # prog_id = (f"{dism_srcd}{prog_id}={filetype}" if prog_id else '')
#
#     prog_id = get_user_prog_id(p_ext)
#     print(f"ftype0={ftype}") if debug else None
#     if prog_id:
#         ftype = get_open_command(prog_id)
#         ftype = f"{registry_srcd if ftype else ''}{prog_id}={ftype}"
#         print(f"ftype1={ftype}") if debug else None
#         filetype = ftype if not filetype else filetype
#         if not ftype:  # DISM Source
#             ftype = get_record_by_extension(r'c:\users\emues\AppAssoc.xml', p_ext)
#             ftype = ET.fromstring(ftype)
#             ftype = f"{dism_srcd if ftype else ''}{ftype}"
#             print(f"ftype2={ftype}") if debug else None
#     else:  # DISM Source
#         ftype = get_record_by_extension(r'c:\users\emues\AppAssoc.xml', p_ext)
#         if ftype:
#             ftype = ET.fromstring(ftype)
#             print(f"ftype3={ftype}") if debug else None
#             prog_id = ftype.attrib.get("ProgId")
#             filetype = ftype.get("ApplicationName")
#             prog_id = (f"{dism_srcd}{prog_id}={filetype}" if prog_id else '')


#  some values from the registry are very long, so, we shorten
# if ret_val3 is not None:
#     typ = (ret_val3.get('type')
#            # or ret_val3.attrib.get('type')
#            or ret_val3.get('ProgId')
#            # or ret_val3.attrib.get('ProgID')
#            )
#     if typ and (typ[:4] == 'AppX' or typ[1:5] == 'AppX' or typ[2:6] == 'AppX'):
#         pass
#         # ret_val3['type'] = f"{typ[:typ.find('Appx')+7]}...{typ[-6:]}"
#         ret_val3['type'] = f"{typ[:typ.find('Appx')+7]}...{typ[(-6-(len(typ)-max(0,typ.find('=')))):]}"
#
# line += format_line(f"{ret_val3['type']}") if (ret_val3
#                                           and ret_val3['type'] is not None
#                                           and ret_val3['app'] is None) else ""
# line += format_line(f"{ret_val3['type']}={ret_val3['app']}")  if (ret_val3
#                                           and ret_val3['app'] is not None
#                                           and ret_val3['type'] not in ret_val3['app']) \
#                                           and ret_val3['type'].find("=") == -1 else ""
# line += format_line(f"{ret_val3['type']}")  if (ret_val3
#                                           and ret_val3['app'] is not None
#                                           and ret_val3['type'] not in ret_val3['app']) \
#                                           and ret_val3['type'].find("=") != -1 else ""
# line += format_line(f"{ret_val3['app']}") if (ret_val3
#                                           and ret_val3['app']  is not None
#                                           and ret_val3['type'] in ret_val3['app']) else ""
