from PySide import QtCore
from datetime import datetime
from functools import partial
import time


class Task(object):
    """Task object. Is DIFFERENT than cosmosPlannig.core.data.tasks.Task

    Args:
        priority (int): priority of the task.
        func ():
        args (list):arguments.
        kwargs (dict): keywords arguments.

    """

    __slots__ = ["time", "priority", "func", "funcname", "last_first", "initdate", "enddate"]

    def __init__(self, priority, func, *args, **kwargs):
        self.time = datetime.today()
        self.priority = priority
        self.func = partial(func, *args, **kwargs)
        self.funcname = func.__name__
        self.last_first = False
        if func.__name__ == '_addWorkingDays':
            self.initdate = args[0]
            self.enddate = args[1]
            self.last_first = True

    def __call__(self):
        self.func()


class TaskQueue(object):
    """Queue of the TaskManager."""
    mutex = QtCore.QMutex()

    def __init__(self):
        QtCore.QMutexLocker(self.mutex)
        self.queue = []

    def clear(self):
        """Clears the queue."""
        QtCore.QMutexLocker(self.mutex)
        self.queue = []

    @staticmethod
    def order(a, b):
        """Sets the priority between two tasks, a and b.

        Args:
            a (cosmosPlanning.core.data.tasks.Task): First Task.
            b (cosmosPlanning.core.data.tasks.Task): Second Task.

        Returns:
            (int): 1 if 'a' has priority, -1 if b has it.

        """
        if a.priority < b.priority:
            return 1
        if a.priority > b.priority:
            return -1
        if a.last_first == b.last_first:
            if a.time < b.time:
                return -1
            elif a.time > b.time:
                return 1
        else:
            if a.time < b.time:
                return 1
            elif a.time > b.time:
                return -1
        return 0

    def put(self, priority, func, *args, **kwargs):
        """Adds a task to the queue.
        The queue is reordered by priority and time after the append
        last_first is a flag that specifies a task whose time order is inverted, and that can be retimed(?).

        Args:
            priority (int): priority of the task.
            func (Functional): function to be called.
            args (list): arguments.
            kwargs (dict): keyword arguments.

        """
        QtCore.QMutexLocker(self.mutex)
        task = Task(priority, func, *args, **kwargs)
        self.queue.append(task)
        # self.queue.sort(cmp=self.order)

    def get(self):
        """Gets a task from the queue.

        Returns:
            (`obj.cosmosPlanning.core.data.tasks.Task`): task returned.

        """
        QtCore.QMutexLocker(self.mutex)
        if len(self.queue) == 0:
            return None
        task = self.queue.pop(0)
        return task

    def resetTime(self, initdate, enddate):
        """Resets the time of the last_first tasks whose time is between datetime_init and datetime_end.

        Args:
            initdate (str): init date of the interval.
            enddate (str): end date of the interval.

        """
        QtCore.QMutexLocker(self.mutex)
        for task in self.queue:
            if task.last_first and task.initdate == initdate and task.enddate == enddate:
                task.time = datetime.today()
        self.queue.sort(cmp=self.order)

    def exists(self, initdate, enddate):
        """Verify if the task with initdate and enddate exists on the queue.

        Args:
            initdate (str): init date of the interval.
            enddate (str): end date of the interval.

        Returns:
            (bool): True if the starts and ends in the specific dates.

        """
        for task in self.queue:
            if task.last_first and task.initdate == initdate and task.enddate == enddate:
                return True
        return False

    def checkName(self, name):
        """Checks if a name is in a task.

        Args:
            name (str): name to check.

        Returns:
              (bool): True if exists the name, false otherwise.

        """

        for task in self.queue:
            if name.lower() in task.funcname.lower():
                return True
        return False


class TaskThread(QtCore.QThread):
    """TaskThread class.

    Args:
        queue (list): list of cosmosPlanning.core.thread.threadManager.Task.
        parent(): (Default = None).

    """

    def __init__(self, queue, parent=None):
        QtCore.QThread.__init__(self, parent=parent)
        self.queue = queue
        self.time_init = None
        self.funcname = ''
        self.stopped = False

    def run(self):
        while not self.stopped:
            task = self.queue.get()
            if task:
                try:
                    self.funcname = task.funcname
                    self.time_init = datetime.today()
                    task.func()
                except StandardError, e:
                    print "({0}) exception raised: {1}".format(task.funcname, str(e))
                self.time_init = None
                self.funcname = ''
            else:
                time.sleep(0.01)

    def stop(self):
        self.stopped = True
        while self.isRunning():
            time.sleep(0.01)


class ThreadPool(QtCore.QThread):
    """ThreadPool class.

    Args:
        numthreads (int): number of threads.
        queue (list): list of cosmosPlanning.core.thread.threadManager.Task.
        threadErrorSignal(QtCore.QThread....):

    """

    def __init__(self, numthreads, queue, threadErrorSignal):
        super(ThreadPool, self).__init__()
        self.numthreads = numthreads
        self.threadErrorSignal = threadErrorSignal
        self.queue = queue
        self.pool = []
        self.stopped = False

    def start(self):
        """Starts the thread pool."""
        for _ in range(self.numthreads):
            thread = TaskThread(self.queue)
            self.pool.append(thread)
            thread.start()

    def run(self):
        """Runs the thread pool."""
        while not self.stopped:
            for item in self.pool:
                if item.time_init:
                    elapsed = datetime.today() - item.time_init
                    if elapsed.total_seconds() > 60 and self.threadErrorSignal:
                        self.threadErrorSignal.emit('blocked thread {0}'.format(item.funcname))
                        item.time_init = None
            time.sleep(0.001)

    def stop(self):
        """Stops the thread pool."""
        self.stopped = True
        for item in self.pool:
            item.stop()
        # self.pool = []


class TaskManager(object):
    """TaskManager Object.

    Args:
        numthreads (int): number of threads to manage(Default = 0).
        thredErrorSignal(): (Default = None).

    """

    def __init__(self, numthreads=0, threadErrorSignal=None):
        self.queue = TaskQueue()
        self.pool = None
        self.numthreads = numthreads
        self.threadErrorSignal = threadErrorSignal

    def start(self):
        """ Starts the taskManager."""
        self.queue = TaskQueue()
        self.instance = QtCore.QThreadPool.globalInstance()
        maxthreads = self.instance.maxThreadCount()
        num = self.numthreads

        if num < 0:
            nthreads = maxthreads + num
        elif num == 0:
            nthreads = maxthreads
        else:
            nthreads = self.numthreads

        if nthreads == 0:
            nthreads = 1
        elif nthreads >= maxthreads:
            nthreads = maxthreads

        print 'Start with {0} threads...'.format(nthreads)

        self.pool = ThreadPool(nthreads, self.queue, self.threadErrorSignal)
        self.pool.start()

    def stop(self):
        """Stops all threads."""
        while self.queue.checkName('save') or self.queue.checkName('delete'):
            time.sleep(0.001)
        self.pool.stop()
        time.sleep(0.5)
        self.queue = TaskQueue()

    def addTask(self, priority, func, *args, **kwargs):
        """Adds a task to the queue.
        The queue is reordered by priority and time after the append.

        Args:
            priority (int): priority of the task.
            func (): function to realize. Example: Future.delete -> to delete a future.
            args (list): arguments.
            kwargs (dict): keyword arguments.

        """
        self.queue.put(priority, func, *args, **kwargs)

    def resetTime(self, initdate, enddate):
        """Resets the time of the last_first tasks whose initdate and enddate are as specified.

        Args:
            initdate (str): specific init date.
            enddate (str): specific end date.

        """
        self.queue.resetTime(initdate, enddate)

    def exists(self, initdate, enddate):
        """Checks if a period exists in the queue.

        Args:
            initdate (str): init date of the period.
            enddate (str): end date of the period.

        """
        return self.queue.exists(initdate, enddate)

    def checkName(self, name):
        """Checks if name is part of any funcname in the queue.

        Args:
            name(str): name to check.

        Returns:
            (bool): True if the function name is in the queue, False otherwise.

        """
        return self.queue.checkName(name)
