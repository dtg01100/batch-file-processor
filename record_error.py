import time


def do(run_log, errors_log, error_message, filename, error_source, threaded=False):

    # generate log message from input parameters
    message = "At: " + str(time.ctime()) + "\r\n" + "From module: " + error_source + "\r\n" + "For object: " +\
              filename + "\r\n" + "Error Message is:" + "\r\n" + (str(error_message) + "\r\n\r\n")
    # record error to both the run log and the errors log
    if not threaded:
        run_log.write(message.encode())
        errors_log.write(message)
    else:
        run_log.append(message)
        errors_log.append(message)
        return run_log, errors_log
