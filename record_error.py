import time


def do(run_log, errors_log, error_message, filename, error_source):

    # generate log message from input parameters
    message = "At: " + str(time.ctime()) + "\r\n" + "From module: " + error_source + "\r\n" + "For object: " +\
              filename + "\r\n" + "Error Message is:" + "\r\n" + (str(error_message) + "\r\n\r\n")
    # record error to both the run log and the errors log
    run_log.write(message)
    errors_log.write(message)
    print(message)
