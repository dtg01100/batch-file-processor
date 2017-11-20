import os


def do_clear(folder_path, maximum_files):
    while len(os.listdir(folder_path)) > maximum_files:
        os.remove(os.path.join(folder_path, min(os.listdir(folder_path),
                                                key=lambda f: os.path.getctime("{}/{}".format(folder_path, f)))))
