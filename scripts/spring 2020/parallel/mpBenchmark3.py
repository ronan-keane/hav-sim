
"""
@author: rlk268@cornell.edu
"""
import time
import multiprocessing

def fun(args):
    a,b = args
    a,b = a/10000,b/10000
    temp = a**(b*a+a**b+(a+b)/(b+1))
    return temp**(b*a+b**a)

def wrapfun(args):
    start, stop = args
    for i in range(start, stop):
        a, b = i/10000, b/10000
        temp = a**(b*a+a**b+(a+b)/(b+1))
        temp = temp**(b*a+b**a)
    return out

# start = time.time()
# for arg in ((i,i) for i in range(10000)):
#     fun(arg)
# print(time.time()-start)

# #BENCHMARK POOL
# if __name__ == "__main__":
#     start = time.time()
#     with multiprocessing.Pool() as pool:
#         pool.map(fun, ((i,i) for i in range(10000)))
#     print(time.time()-start)

#benchmark process
cpu = 2
n = 10000
if __name__ == '__main__':
    start = time.time()
    chunk = n // cpu
    chunks = list(range(0,n,chunk))
    chunks.append(n)
    args = ((chunks[i], chunks[i+1]) for i in range(n // chunk))
    plist = []
    for i in range(cpu):
        p = multiprocessing.Process(target = wrapfun, args = args)
        plist.append(p)
        p.start()
    for p in plist:
        p.join()
    print(time.time()-start)

