class MyTestClass:

    def __init__(self, sometext):
        self.text = sometext

    def printtext(self):
        print(self.text)

if __name__ == '__main__':
    MTC = MyTestClass("Hello")
    MTC.printtext()
