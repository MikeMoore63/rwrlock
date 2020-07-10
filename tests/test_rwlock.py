#

######### test_rwrock.py #########


import threading
import time
from  rwrlock import RWRLock
import logging
import unittest
import random


def waitproduce(cv,myid,sleeptime):
    if myid == 0:
        time.sleep(sleeptime)
        cv.set()
    else:
        cv.wait(0.7)

def rotatethread(therwrlock,cv,cvfinish,sharedState,start,modulus,loopmax,chaos):

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)
    myid=None
    errors=False

    for loopi in range(loopmax):
        try:
            with therwrlock.r_locked():

                checklockstate(therwrlock,rlockexpected=1,wlockexpected=0)
                myid = (start + sharedState["base"]) % modulus
                log.debug("Read lock got {}:{}".format(myid,start))
                cv.clear()

                # grab my sub lock
                with sharedState["sublocks"][myid]["lock"]:
                    try:
                        log.debug("Write log {}:{} lock got".format(myid,start))
                        sharedState["sublocks"][myid]["lastwriter"]=start

                        # if controlling thread this loop
                        waitproduce(cv,myid,0.4)
                        log.debug("testing {}:{}".format(myid,start))

                        # validate thereadstate
                        for i in range(modulus - 1):
                            for j in range(modulus - 1,0,-1):
                                if i != j and sharedState["sublocks"][i]["lastwriter"] is not None and sharedState["sublocks"][j]["lastwriter"] is not None:
                                    if sharedState["sublocks"][i]["lastwriter"] == sharedState["sublocks"][j]["lastwriter"]:
                                        # only valid if nex oop a hread has
                                        assert abs(i - j) == 1 or abs(i-j) == modulus - 1
                        num_r = therwrlock.num_r
                        log.debug("modulus {}:{}".format(modulus, num_r ))
                        # as using even wuh ime oucan only vallidae
                        assert num_r <= modulus + chaos
                        waitproduce(cv,myid,0.3)
                        log.debug("moving on {}:{}".format(myid,start))
                    finally:
                        sharedState["sublocks"][i]["lastwriter"] = None


            if myid != 0:
                time.sleep(0.3)
            else:
                log.debug("geting w lock {}:{}".format(myid,start))
                with therwrlock.w_locked():
                    log.debug("base is me {}:{} new base {}".format(myid,start,sharedState["base"]))
                    checklockstate(therwrlock, rlockexpected=0, wlockexpected=1)
                    sharedState["base"] +=1
                log.debug("base done  {}:{} now {}".format(myid,start,sharedState["base"]))
        except Exception as e:
            errors=True
            log.exception("Thread excepion  {}:{}".format(myid, start))

    log.debug("done notifying {}:{} ".format(myid, start))
    with therwrlock.w_locked():
        marker = sharedState["finished"]
        sharedState["sublocks"][marker]["errors"] = errors
        sharedState["finished"] += 1

    with cvfinish:
        cvfinish.notify()

def chaosthread(therwrlock,cv,cvfinish,sharedState,start,modulus,loopmax):
    """
    Chaos monkey hread. grabs read lock and radomly grabs wrie lock on a sublock

    :param therwrlock:
    :param cv:
    :param cvfinish:
    :param sharedState:
    :param start:
    :param modulus:
    :param loopmax:
    :return:
    """

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    for i in range(loopmax):
        with therwrlock.r_locked():
            sleepfor = random.random() * 0.3
            log.debug("chaos read lock sleep {}".format(sleepfor))
            time.sleep(sleepfor)

            theone=random.randint(0,modulus-1)

            with sharedState["sublocks"][theone]["lock"]:
                sleepfor = random.random() * 0.3
                log.debug("chaos write lock {} sleep {}".format(theone,sleepfor))
                time.sleep(sleepfor)
            log.debug("chaos write lock done")
        log.debug("chaos read lock done")


def checklockstate(L,rlockexpected=None,wlockexpected=None):
    """ Check state of lock assumed called in a lock """

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    rlockcount, wlockcount = L.thread_lock_count()
    num_r = L.num_r
    num_w = L.num_w
    assert rlockcount >= 0
    assert wlockcount >= 0
    assert num_r >= 0
    assert num_w >= 0


    if rlockcount > 0 and wlockcount == 0:
        assert num_r >= 1

    if num_r > 0 or num_w > 0:
        assert num_w == 1
        assert L.w_lock.acquire(False) == False

    if wlockcount > 0 :
        assert L.w_lock.acquire(False) == False
        log.debug("num_r:{},num_w:{}".format(num_r,num_w))
        # if first reader is waiting fpr wrie lock read lock should no be acquirable
        # as read lock is acquired alllloherreaders will block
        if num_r ==1:
            assert L.num_r_lock.acquire(False) == False
        else:
            assert num_r == 0
        assert num_w == 1


    if rlockexpected is not None:
        assert rlockcount == rlockexpected

    if wlockexpected is not None:
        assert wlockexpected == wlockcount


def writer(L, value, after, rwlock, times):
    """Append value to L after a period of time."""
    try:
        with rwlock.w_locked():
            checklockstate(rwlock,rlockexpected=0,wlockexpected=1)
        # Get another lock, to test the fact that obtaining multiple
        # write locks from the same thread context doesn't block (lock
        # reentrancy).
            with rwlock.w_locked():
                checklockstate(rwlock, rlockexpected=0, wlockexpected=2)
        # Get a reader lock too; should be the same as getting another
        # writer since writers are inherently readers as well.
                with rwlock.r_locked():
                    checklockstate(rwlock, rlockexpected=1, wlockexpected=2)
                    times.append(time.time())
                    time.sleep(after)
                    L.append(value)
    finally:
        times.append(time.time())


def reader(L1, L2, after, rwlock, times):
    """Append values from L1 to L2 after a period of time."""
    try:
        with rwlock.r_locked():
            checklockstate(rwlock, rlockexpected=1, wlockexpected=0)
        # Get another lock, to test the fact that obtaining multiple
        # write locks from the same thread context doesn't block (lock
        # reentrancy).
            with rwlock.r_locked():
                checklockstate(rwlock, rlockexpected=2, wlockexpected=0)
                times.append(time.time())
                time.sleep(after)
                L2.extend(L1)
    finally:
        times.append(time.time())


def readerTurnedWriter(L, value, after, rwlock, times):
    """Append value to L after a period of time."""
    try:
        with rwlock.r_locked():
            checklockstate(rwlock, rlockexpected=1, wlockexpected=0)
            with rwlock.w_locked():
                checklockstate(rwlock, rlockexpected=1, wlockexpected=1)
                times.append(time.time())
                time.sleep(after)
                L.append(value)
    finally:
        times.append(time.time())

class TestStringMethods(unittest.TestCase):
    def testmultirotatereaderwriter(self):
        """
        This tests a rotating reader writer
        All hreads attempt to read state
        One randomly attempts to write
        All readers should know who wrote last
        A sub object is protected by a lock
        Each loop each thread puts ona read lock
        reads the base adds offest and modulos by 3 to identify which sublock they shoulld acquire
        ttehy then each get the relevant sublock
        replace lasttWriter witth thread identtity
        the thread with modulus 0 sleeps then acquires cv noifies all and releases
        all non 0 acquire the cv immediaetly and wait until notified
        afer release hey alll assert read state (alll oher read locks are acquired) with non blocking check
        he hread with modulus 0 sleeps
        all non 0 acquire cv and wai to be noified
        thread 0 notifies after sleep
        all non 0 sleep
        0 grabs wrie lock increments base passing write responsibility to another thread
        they all loop 5 times

        """

        logging.basicConfig()
        therwrlock = RWRLock()
        cv = threading.Event()
        cvfinish = threading.Condition()

        sharedState = {
            "lastwriter": None,
            "base": 0,
            "finished":0,
            "sublocks": []
        }

        threadmax = 150
        loopmax = 15
        chaos = 7
        mythreads = []

        for i in range(threadmax):
            l = threading.Lock()
            sharedState["sublocks"].append({"lock": l, "lastwriter": None,"errors":True})
            mythreads.append(threading.Thread(
                target=rotatethread,
                args=(therwrlock, cv, cvfinish, sharedState, i, threadmax, loopmax,chaos),
            ))

        chaosmonkeys = []
        for i in range(chaos):
            chaosmonkeys.append(threading.Thread(
                    target=chaosthread,
                    args=(therwrlock, cv, cvfinish, sharedState, i, threadmax, loopmax),
                ))

        for monkey in chaosmonkeys:
            monkey.start()

        for i in mythreads:
            i.start()

        log = logging.getLogger(__name__)
        for i in mythreads:
            i.join()
            log.info("Test thread complete")


        for monkey in chaosmonkeys:
            monkey.join()
            log.info("Monkey complete")

        for i in range(threadmax):
            assert sharedState["sublocks"][i]["errors"] == False

    def test_reentrancy(self):
        lock = RWRLock()
        # these are single threaded so safeto check lock state without a lock
        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        # Reentrant read locks.
        with lock.r_locked():
            checklockstate(lock, rlockexpected=1, wlockexpected=0)
            with lock.r_locked():
                checklockstate(lock, rlockexpected=2, wlockexpected=0)
                pass
        checklockstate(lock, rlockexpected=0, wlockexpected=0)

        # Reentrant write locks.
        with lock.w_locked():
            checklockstate(lock, rlockexpected=0, wlockexpected=1)
            with lock.w_locked():
                checklockstate(lock, rlockexpected=0, wlockexpected=2)
                pass
        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        # Writers are also readers.
        with lock.w_locked():
            checklockstate(lock, rlockexpected=0, wlockexpected=1)
            with lock.r_locked():
                checklockstate(lock, rlockexpected=1, wlockexpected=1)
                pass
        checklockstate(lock, rlockexpected=0, wlockexpected=0)


    def test_reentrancyexceptions(self):
        lock = RWRLock()
        # these are single threaded so safeto check lock state without a lock
        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        # Reentrant read locks.
        try:
            with lock.r_locked():
                checklockstate(lock, rlockexpected=1, wlockexpected=0)
                with lock.r_locked():
                    checklockstate(lock, rlockexpected=2, wlockexpected=0)
                    raise Exception('a dummy exception')
        except:
            pass
        checklockstate(lock, rlockexpected=0, wlockexpected=0)

        # Reentrant write locks.
        try:
            with lock.w_locked():
                with lock.w_locked():
                    raise Exception('a dummy exception')
        except:
            pass

        checklockstate(lock, rlockexpected=0, wlockexpected=0)

        # Writers are also readers.
        try:
            with lock.w_locked():
                with lock.r_locked():
                    raise Exception('a dummy exception')
        except:
            pass

        checklockstate(lock, rlockexpected=0, wlockexpected=0)



    def test_reentrancy2locks(self):
        lock = RWRLock()
        lock2 = RWRLock()
        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        checklockstate(lock2, rlockexpected=0, wlockexpected=0)

        # Reentrant read locks 2locks.
        with lock.r_locked():
            checklockstate(lock, rlockexpected=1, wlockexpected=0)
            checklockstate(lock2, rlockexpected=0, wlockexpected=0)
            with lock.r_locked():
                checklockstate(lock, rlockexpected=2, wlockexpected=0)
                checklockstate(lock2, rlockexpected=0, wlockexpected=0)
                with lock2.r_locked():
                    checklockstate(lock, rlockexpected=2, wlockexpected=0)
                    checklockstate(lock2, rlockexpected=1, wlockexpected=0)
                    with lock2.r_locked():
                        checklockstate(lock, rlockexpected=2, wlockexpected=0)
                        checklockstate(lock2, rlockexpected=2, wlockexpected=0)
                        pass
        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        checklockstate(lock2, rlockexpected=0, wlockexpected=0)

        # Reentrant write locks.
        with lock.w_locked():
            checklockstate(lock, rlockexpected=0, wlockexpected=1)
            checklockstate(lock2, rlockexpected=0, wlockexpected=0)
            with lock.w_locked():
                checklockstate(lock, rlockexpected=0, wlockexpected=2)
                checklockstate(lock2, rlockexpected=0, wlockexpected=0)
                with lock2.w_locked():
                    checklockstate(lock, rlockexpected=0, wlockexpected=2)
                    checklockstate(lock2, rlockexpected=0, wlockexpected=1)
                    with lock2.w_locked():
                        checklockstate(lock, rlockexpected=0, wlockexpected=2)
                        checklockstate(lock2, rlockexpected=0, wlockexpected=2)
                        pass

        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        checklockstate(lock2, rlockexpected=0, wlockexpected=0)

        # Writers are also readers.
        with lock.w_locked():
            checklockstate(lock, rlockexpected=0, wlockexpected=1)
            checklockstate(lock2, rlockexpected=0, wlockexpected=0)
            with lock.r_locked():
                checklockstate(lock, rlockexpected=1, wlockexpected=1)
                checklockstate(lock2, rlockexpected=0, wlockexpected=0)
                with lock2.w_locked():
                    checklockstate(lock, rlockexpected=1, wlockexpected=1)
                    checklockstate(lock2, rlockexpected=0, wlockexpected=1)
                    with lock2.r_locked():
                        checklockstate(lock, rlockexpected=1, wlockexpected=1)
                        checklockstate(lock2, rlockexpected=1, wlockexpected=1)
                        pass

        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        checklockstate(lock2, rlockexpected=0, wlockexpected=0)

        # Writers are also readers 2llocks.
        with lock.w_locked():
            checklockstate(lock, rlockexpected=0, wlockexpected=1)
            checklockstate(lock2, rlockexpected=0, wlockexpected=0)
            with lock2.r_locked():
                checklockstate(lock, rlockexpected=0, wlockexpected=1)
                checklockstate(lock2, rlockexpected=1, wlockexpected=0)
                with lock.w_locked():
                    checklockstate(lock, rlockexpected=0, wlockexpected=2)
                    checklockstate(lock2, rlockexpected=1, wlockexpected=0)
                    with lock2.r_locked():
                        checklockstate(lock, rlockexpected=0, wlockexpected=2)
                        checklockstate(lock2, rlockexpected=2, wlockexpected=0)
                        pass
        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        checklockstate(lock2, rlockexpected=0, wlockexpected=0)

        with lock.w_locked():
            checklockstate(lock, rlockexpected=0, wlockexpected=1)
            checklockstate(lock2, rlockexpected=0, wlockexpected=0)
            with lock2.r_locked():
                checklockstate(lock, rlockexpected=0, wlockexpected=1)
                checklockstate(lock2, rlockexpected=1, wlockexpected=0)
                with lock2.w_locked():
                    checklockstate(lock, rlockexpected=0, wlockexpected=1)
                    checklockstate(lock2, rlockexpected=1, wlockexpected=1)
                    with lock.r_locked():
                        checklockstate(lock, rlockexpected=1, wlockexpected=1)
                        checklockstate(lock2, rlockexpected=1, wlockexpected=1)
                        pass
        checklockstate(lock, rlockexpected=0, wlockexpected=0)
        checklockstate(lock2, rlockexpected=0, wlockexpected=0)

    def test_writeReadRead(self):
        lock = RWRLock()
        W, R1, R2 = [], [], []
        TW, TR1, TR2 = [], [], []
        thread1 = threading.Thread(
            target=writer,
            args=(W, 'foo', 0.2, lock, TW),
            )
        thread2 = threading.Thread(
            target=reader,
            args=(W, R1, 0.2, lock, TR1),
            )
        thread3 = threading.Thread(
            target=reader,
            args=(W, R2, 0.2, lock, TR2),
            )
        thread1.start()
        time.sleep(0.1)
        thread2.start()
        thread3.start()
        time.sleep(0.8)
        assert 'foo' in R1
        assert 'foo' in R2
        assert TR1[0] <= TR2[1]             # Read 1 started during read 2.
        assert TR2[0] <= TR1[1]             # Read 2 started during read 1.
        assert TR1[0] >= TW[1]              # Read 1 started after write.
        assert TR2[0] >= TW[1]              # Read 2 started after write.


    def test_writeReadReadWrite(self):
        lock = RWRLock()
        W, R1, R2 = [], [], []
        TW1, TR1, TR2, TW2 = [], [], [], []
        thread1 = threading.Thread(
            target=writer,
            args=(W, 'foo', 0.3, lock, TW1),
            )
        thread2 = threading.Thread(
            target=reader,
            args=(W, R1, 0.3, lock, TR1),
            )
        thread3 = threading.Thread(
            target=reader,
            args=(W, R2, 0.3, lock, TR2),
            )
        thread4 = threading.Thread(
            target=writer,
            args=(W, 'bar', 0.3, lock, TW2),
            )
        thread1.start()
        time.sleep(0.1)
        thread2.start()
        time.sleep(0.1)
        thread3.start()
        time.sleep(0.1)
        thread4.start()
        time.sleep(1.7)
        assert 'foo' in R1
        assert 'foo' in R2
        assert 'bar' not in R1
        assert 'bar' not in R2
        assert 'bar' in W
        assert TR1[0] <= TR2[1]              # Read 1 started during read 2.
        assert TR2[0] <= TR1[1]              # Read 2 started during read 1.
        assert TR1[0] >= TW1[1]              # Read 1 started after write 1.
        assert TR2[0] >= TW1[1]              # Read 2 started after write 1.
        assert TW2[0] >= TR1[1]              # Write 2 started after read 1.
        assert TW2[0] >= TR2[1]              # Write 2 started after read 2.

    def test_writeReadReadtowrite(self):
        lock = RWRLock()
        W, R1 = [], []
        TW1, TR1, TW2 = [], [], []
        thread1 = threading.Thread(
            target=writer,
            args=(W, 'foo', 0.3, lock, TW1),
            )
        thread2 = threading.Thread(
            target=reader,
            args=(W, R1, 0.3, lock, TR1),
            )
        thread3 = threading.Thread(
            target=readerTurnedWriter,
            args=(W, 'bar', 0.3, lock, TW2),
            )
        thread1.start()
        time.sleep(0.1)
        thread2.start()
        time.sleep(0.1)
        thread3.start()
        time.sleep(1.7)
        assert 'foo' in R1
        assert 'bar' not in R1
        assert 'bar' in W
        assert TR1[0] >= TW1[1]              # Read 1 started after write 1.
        assert TW2[0] >= TR1[1]              # Write 2 started after read 1.

if __name__ == '__main__':
    unittest.main()