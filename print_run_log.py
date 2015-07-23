import platform
import textwrap

def do(filename):
    filename = filename.read()
    formatted_log = '\r\n'.join(textwrap.wrap(filename, width=75, replace_whitespace=False))
    if platform.system() == 'Windows':
        import os, sys
        import win32print
        printer_name = win32print.GetDefaultPrinter ()
        #
        # raw_data could equally be raw PCL/PS read from
        #  some print-to-file operation
        #
        if sys.version_info >= (3,):
            raw_data = bytes (formatted_log, "utf-8")
        else:
            raw_data = formatted_log

        hPrinter = win32print.OpenPrinter (printer_name)
        try:
            hJob = win32print.StartDocPrinter (hPrinter, 1, ("Log File Printout", None, "RAW"))
            try:
                win32print.StartPagePrinter (hPrinter)
                win32print.WritePrinter (hPrinter, raw_data)
                win32print.EndPagePrinter (hPrinter)
            finally:
                win32print.EndDocPrinter (hPrinter)
        finally:
            win32print.ClosePrinter (hPrinter)

    else:
        import subprocess
        lpr = subprocess.Popen("/usr/bin/lpr", stdin=subprocess.PIPE)
        lpr.stdin.write(formatted_log)
