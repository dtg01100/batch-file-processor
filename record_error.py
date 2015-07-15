def do(run_log, errors_log, error_message, filename, error_source):

    message = "From module: " + error_source + "\r\n" + "For file: " + filename + "\r\n" + "Error Message is:" + \
              "\r\n" + (str(error_message) + "\r\n\r\n")
    run_log.write(message)
    errors_log.write(message)
