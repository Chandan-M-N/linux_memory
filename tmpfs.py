import os
import tarfile
import subprocess
from random import choice
from string import ascii_lowercase
import tempfile
import stat
import sys

def createFd():
    print("Creating anonymous fd")
    s = ''.join(choice(ascii_lowercase) for _ in range(7))
    fd = os.memfd_create(s, 0)
    if fd == -1:
        print("Error in creating fd")
        exit(0)
    return fd

def writeToFile(fd, contents):
    print("Writing contents to anonymous file")
    with open(f"/proc/self/fd/{fd}", 'wb') as f:
        f.write(contents)

def archive_directory(directory_path):
    """Compresses the directory into a tar archive."""
    temp_archive = tempfile.NamedTemporaryFile(delete=False)
    with tarfile.open(temp_archive.name, "w:gz") as tar:
        tar.add(directory_path, arcname=os.path.basename(directory_path))
    temp_archive.seek(0)
    with open(temp_archive.name, 'rb') as f:
        archive_data = f.read()
    os.unlink(temp_archive.name)  # Delete the temp archive after reading
    return archive_data

def mount_tmpfs(mount_point, size="100M"):
    """Mounts a tmpfs filesystem at the given mount point."""
    print(f"Mounting tmpfs at {mount_point} with size {size}")
    subprocess.run(["sudo", "mount", "-t", "tmpfs", "-o", f"size={size}", "tmpfs", mount_point], check=True)

def unmount_tmpfs(mount_point):
    """Unmounts the tmpfs filesystem from the mount point."""
    print(f"Unmounting tmpfs from {mount_point}")
    subprocess.run(["sudo", "umount", mount_point], check=True)

def execAnonFile(fd, wait_for_proc_terminate):
    print("Spawning process...")
    child_pid = os.fork()
    if child_pid == -1:
        print("Error spawning new process")
        exit()
    elif child_pid == 0:
        # In child process
        print("[+] Executing...")

        # Create a temporary directory manually
        tmpdir = tempfile.mkdtemp()
        try:
            # Mount tmpfs to tmpdir
            mount_tmpfs(tmpdir)
            print(f"Extracting in {tmpdir} (tmpfs mounted)...")

            # Extract tar.gz from anonymous file
            with open(f"/proc/self/fd/{fd}", 'rb') as f:
                with tarfile.open(fileobj=f) as tar:
                    tar.extractall(path=tmpdir)
            
            # Change directory to the temp directory where files were extracted
            print("Contents of tmpdir:")
            for root, dirs, files in os.walk(tmpdir):
                print(root, dirs, files)

            # Prepare to execute main.py
            main_py_path = os.path.join(tmpdir, "packing_code", "main.py")
            print(main_py_path)
            if not os.path.exists(main_py_path):
                print("main.py not found!")
                exit()

            os.chmod(main_py_path, stat.S_IRWXU)

            os.chdir(os.path.dirname(main_py_path))

            # Use subprocess to run the script and wait for it to complete
            result = subprocess.run([sys.executable, main_py_path], check=True)

            print(f"Script executed with return code: {result.returncode}")

        finally:
            # Unmount tmpfs after execution
            os.chdir("/")
            unmount_tmpfs(tmpdir)
            # Clean up the temporary directory
            # os.rmdir(tmpdir)  # Remove the directory after unmounting
    else:
        if wait_for_proc_terminate:
            print(f"Waiting for new process ({child_pid}) to terminate")
            os.waitpid(child_pid, 0)

# MAIN CODE
try:
    directory_path = "/home/sunlab/packing_code"  # Path to the directory containing main.py, subdirectories, config.yaml, etc.
    args = []  # List of arguments to pass to program
    wait_for_proc_terminate = True  # Wait for process termination

    # Archive the directory
    archive_data = archive_directory(directory_path)

    # Create anonymous memory file, write to it, and execute it
    fd = createFd()
    print(f"My FD: {fd}")
    writeToFile(fd, archive_data)
    execAnonFile(fd, wait_for_proc_terminate)

except KeyboardInterrupt:
    print("User interrupted!")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except subprocess.CalledProcessError as e:
    print(f"Error with tmpfs mount/unmount: {e}")
