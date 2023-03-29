# Python program to illustrate the concept
# of threading
import threading
import os
lock = threading.Lock()


class Tasks:
    def __init__(self):
        self.value = 0

    def add(self):
        lock.acquire()
        print(f"add 1 at thread: id={threading.current_thread()}")
        self.value += 1
        lock.release()


if __name__ == "__main__":

    # print ID of current process
    print("ID of process running main program: {}".format(os.getpid()))

    # print name of main thread
    print("Main thread name: {}".format(threading.current_thread().name))

    task = Tasks()

    # creating threads
    t1 = threading.Thread(target=task.add, name='t1')

    # starting threads
    t1.start()
    task.add()
    print("Main thread here still running")

    # wait until all threads finish
    t1.join()

    print(f"{task.value}")
