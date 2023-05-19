class A:
    def __init__(self):
        self.value = 0


class B:
    def __init__(self, a: A):
        self.a = a


class C:
    def __init__(self):
        self.a = None


a = A()
b = B(a)
c = C()
c.a = b.a

a.value += 10
print(c.a.value)

