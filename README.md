This is rwrlock a yet another python re-entrant rw lock

Goals
* To make a rentrant read write lock as opposed to non re-entrant
* Within one thread multiple readlocks can be obtained in reality only first in stack takes lock restreference count
* Within onethreadmultiple write locks can be obtained again first gets lock restreference count
* Within one thread if you want a read lock and have a write lock it acts as if read lock is obtained but keeps the write lock
* Wihin one thread if you have a read lock and want a write lock read lock is dropped a write lock acquired. But when write is release the read lock is reobtained. This can lead to read consistency issues if not used carefuly. 

This does not implement and priority between readers and writers
  
```
Usage:
            from rwrlock import RWRLock
            
            my_obj_rwlock = RWRLock()
            
            # When reading from my_obj:
            with my_obj_rwlock.r_locked():
                do_read_only_things_with(my_obj)
                    # promote to a write lock
                    with my_obj_rwlock.w_locked():
                        mutate(my_obj)
                
            # When writing to my_obj:
            with my_obj_rwlock.w_locked():
                mutate(my_obj)
                    # ok do to do read things as has a write lock
                    with my_obj_rwlock.r_locked():
                        do_read_only_things_with(my_obj)

```
    