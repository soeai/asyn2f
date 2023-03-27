# Python program to illustrate the concept
# of threading
import threading
import os

from fedasync.commons.conf import Config
from fedasync.server.server_queue_manager import ServerConsumer

Config.QUEUE_NAME = "server_queue"
Config.QUEUE_URL = "amqp://guest:guest@localhost:5672/%2F"

server_consumer = ServerConsumer()


def task1():
    print("Task 1 assigned to thread: {}".format(threading.current_thread().name))
    print("ID of process running task 1: {}".format(os.getpid()))


def task2():
    print("Task 2 assigned to thread: {}".format(threading.current_thread().name))
    print("ID of process running task 2: {}".format(os.getpid()))


if __name__ == "__main__":
    # print ID of current process
    print("ID of process running main program: {}".format(os.getpid()))

    # print name of main thread
    print("Main thread name: {}".format(threading.current_thread().name))

    # creating threads
    t1 = threading.Thread(target=server_consumer.run, name='t1')



    # starting threads
    t1.start()

    print("Main thread here still running")

    # wait until all threads finish
    t1.join()
