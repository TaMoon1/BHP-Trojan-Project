import os
def run(**args):
    print("[*] In dirlister module.")
    return str(os.listdir("."))
