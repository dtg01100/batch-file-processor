import os
import emails

def do(process_parameters):
    os.chdir(process_parameters['foldersname'])
    for filename in os.listdir(process_parameters['foldersname']):
        print (filename)
        email_to_send = emails.Message(subject=filename,)
        email_to_send.attach(filename, data=(open(filename)))
        email_to_send.send(to=process_parameters['email_to'], smtp=process_parameters['email_destination_address'])
