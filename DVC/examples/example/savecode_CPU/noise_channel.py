import numpy as np

def noise_channel(arr1, arr2, arr3, p1, p2, p3):
    def modify(a_inp, p):
        a = list(a_inp)
        for i in range(len(a)):
            rn = np.random.uniform(0, 1)
            if rn < p:
                a[i] = 0
        return bytes(a)
    return modify(arr1, p1), modify(arr2, p2), modify(arr3, p3)
