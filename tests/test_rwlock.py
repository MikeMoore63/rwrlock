#

######### test_rwrock.py #########


import threading
import time
from  rwrlock import RWRLock

def checklockstate(L,rlockexpected=None,wlockexpected=None):
    """ Check state of lock assumed called in a lock """
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



def test_reentrancy():
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


def test_reentrancyexceptions():
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



def test_reentrancy2locks():
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

def test_writeReadRead():
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


def test_writeReadReadWrite():
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


def test_writeReadReadtowrite():
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
