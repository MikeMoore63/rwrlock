# -*- coding: utf-8 -*-
""" rwlock.py

    A class to implement read-write locks on top of the standard threading
    library.

    This is implemented with two mutexes (threading.Lock instances) as per this
    wikipedia pseudocode:

    https://en.wikipedia.org/wiki/Readers%E2%80%93writer_lock#Using_two_mutexes

    Code written by Mike Moore.
    
    Based upon code by Tyler Neylon at Unbox Research.
    
    see this gist https://gist.github.com/tylerneylon/a7ff6017b7a1f9a506cf75aa23eacfd6
    
    Added that itappears as a reentrant locks and reference countingto make rw reentrant
"""


# _______________________________________________________________________
# Imports

from contextlib import contextmanager
import threading


# _______________________________________________________________________
# Class

class RWRLock(object):
    """ RWLock class; this is meant to allow an object to be read from by
        multiple threads, but only written to by a single thread at a time. See:
        https://en.wikipedia.org/wiki/Readers%E2%80%93writer_lock

        Usage:

            from rwlock import RWLock

            my_obj_rwlock = RWLock()

            # When reading from my_obj:
            with my_obj_rwlock.r_locked():
                do_read_only_things_with(my_obj)

            # When writing to my_obj:
            with my_obj_rwlock.w_locked():
                mutate(my_obj)
    """

    def __init__(self):
        # as possible to have manyrw locks
        # created per class as lock is expected
        # to be used across many threads
        self._threadlocal = threading.local()

        # has to be a lock and non reentrant as locks can be acquired
        # in one threadand released in another
        self.w_lock = threading.Lock()
        self.num_r_lock = threading.RLock()
        self.num_r = 0
        self.num_w =0
        self.promoteacquire = False

    # ___________________________________________________________________
    # Reading methods.
    def thread_lock_count(self):
        rlockcount = getattr(self._threadlocal, 'rlockcount', None)
        wlockcount = getattr(self._threadlocal, 'wlockcount', None)
        if rlockcount is None:
            rlockcount = 0
        if wlockcount is None:
            wlockcount = 0
        return(rlockcount,wlockcount)

    def set_thread_lock_count(self,rlockcount, wlockcount):
        self._threadlocal.rlockcount =  rlockcount
        self._threadlocal.wlockcount =  wlockcount

    # non re-entrant acquire rentrancy on per thread basis
    def nr_acquire(self):
        self.num_r_lock.acquire()
        self.num_r += 1
        if self.num_r == 1:
            self.w_lock.acquire()
            self.num_w += 1
        self.num_r_lock.release()

    # rentrant acquire
    def r_acquire(self):
        rlockcount,wlockcount = self.thread_lock_count()
        if rlockcount==0 and wlockcount==0:
            self.nr_acquire()
        rlockcount=rlockcount+1
        self.set_thread_lock_count(rlockcount, wlockcount)

    # non reentrant release
    def nr_release(self):
        assert self.num_r > 0
        self.num_r_lock.acquire()
        self.num_r -= 1
        if self.num_r == 0:
            self.num_w -= 1
            self.w_lock.release()
        self.num_r_lock.release()

    # rentrant release
    def r_release(self):
        rlockcount,wlockcount = self.thread_lock_count()
        assert  rlockcount > 0
        rlockcount = rlockcount - 1
        if rlockcount == 0 and wlockcount==0:
            self.nr_release()
        self.set_thread_lock_count(rlockcount, wlockcount)

    @contextmanager
    def r_locked(self):
        """ This method is designed to be used via the `with` statement. """
        try:
            self.r_acquire()
            yield
        # need finally as documented here https://docs.python.org/3/library/contextlib.html
        finally:
            self.r_release()

    # ___________________________________________________________________
    # Writing methods.
    def nw_acquire(self):
        # as any one reader ensures in any threadis still running this lock
        # wi notbe obrainable so we wi block
        # if this thread is onlly one running it willl work as arentrant lock
        self.w_lock.acquire()
        self.num_w += 1

    def w_acquire(self):
        rlockcount, wlockcount = self.thread_lock_count()
        if wlockcount == 0:
            # if we havea read lock
            # we remove readlock
            # then getawrite llock
            # nb this means data beforeand afterwrite may change
            # in 1 thread but nit in an inconsistentfashion
            # means non repeated reads for sharedstate
            if rlockcount > 0:
                self.nr_release()
            self.nw_acquire()

        wlockcount = wlockcount + 1
        self.set_thread_lock_count(rlockcount, wlockcount)

    def nw_release(self):
        self.num_w -= 1
        self.w_lock.release()

    def w_release(self):
        rlockcount, wlockcount = self.thread_lock_count()
        assert wlockcount > 0
        wlockcount = wlockcount - 1
        if wlockcount == 0:
            # put back the fact we are a reader
            # if wearea reader i.e. demote write ock back to read
            # if we had no ock before do nothing
            self.nw_release()

            if rlockcount > 0:
                self.nr_acquire()

        self.set_thread_lock_count(rlockcount, wlockcount)

    @contextmanager
    def w_locked(self):
        """ This method is designed to be used via the `with` statement. """
        try:
            self.w_acquire()
            yield
        # need finally as documented here https://docs.python.org/3/library/contextlib.html
        finally:
            self.w_release()