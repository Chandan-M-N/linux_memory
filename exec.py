
import os
from random import choice
from string import ascii_lowercase
import time

def createFd():
    print("Creating anonymous fd")
    s = ""
    for _ in range(7):
        s += choice(ascii_lowercase)

    fd = os.memfd_create(s, 0)
    if fd == -1:
        print("Error in creating fd")
        exit(0)
    return fd

def writeToFile(fd, c):
    print("Writing contents to anonymous file")
    with open("/proc/self/fd/{}".format(fd), 'wb') as f:
        f.write(c)

def execAnonFile(fd, args, wait_for_proc_terminate):
    print("Spawning process...")
    child_pid = os.fork()
    if child_pid == -1:
        print("Error spawning new process")
        exit()
    elif child_pid == 0:
        print("[+] Executing...")
        fname = "/proc/self/fd/{}".format(fd)
        args.insert(0, fname)
        os.execve(fname, args, dict(os.environ))
    else:
        if wait_for_proc_terminate:
            print("Waiting for new process ({}) to terminate".format(child_pid))
            os.waitpid(child_pid, 0)
        else:
            print("New process is now orphaned")

# MAIN CODE
try:
    # Read the contents of hello.bin
    with open("hello.bin", "rb") as f:
        elf_contents = f.read()

    args = []  # List of arguments to pass to program
    wait_for_proc_terminate = True  # Wait for process termination

    # Create anonymous memory file, write to it, and execute it
    fd = createFd()
    print(f"My FD: {fd}")
    time.sleep(50)
    writeToFile(fd, elf_contents)
    execAnonFile(fd, args, wait_for_proc_terminate)

except KeyboardInterrupt:
    print("User interrupted!")
except FileNotFoundError:
    print("File hello.bin not found!")
