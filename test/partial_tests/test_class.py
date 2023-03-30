class A:
    def __init__(self):
        self.value = 0


class B:
    def __init__(self, a: A):
        self.a = a


a = A()
b = B(a)

a.value += 10
print(b.a.value)
