This is rwrlock a yet another python re-entrant rw lock

Goals
* To make a rentrant read write ock as opposed to non re-entrant
* Within one thread multiple readlocks can be obtained in reality only first in stack takes lock restreference count
* Within onethreadmultiple write locks can be obtained again first gets lock restreference count
* Withion one thread if you want a readlock and have a write lock it acts as if read lock is obtained but keeps the write lock
* What this does not do is promote a read lock to a write lock that instead throws a runtime error

This does not implement and priority between readers and writers
  
```
Usage:
            from rwrlock import RWLock
            
            my_obj_rwlock = RWLock()
            
            # When reading from my_obj:
            with my_obj_rwlock.r_locked():
                do_read_only_things_with(my_obj)
                
            # When writing to my_obj:
            with my_obj_rwlock.w_locked():
                mutate(my_obj)

```
    