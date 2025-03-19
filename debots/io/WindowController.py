class WindowController:
    class WindowOperation:
        pass

    class PrintOperation(WindowOperation):
        def __init__(self, text):
            self.text = text

    class TerminateOperation(WindowOperation):
        pass

    class SetLabelOperation(WindowOperation):
        def __init__(self, label):
            self.label = label

    class SetTitleOperation(WindowOperation):
        def __init__(self, title):
            self.title = title

    def __init__(self, queue):
        self.queue = queue

    def print(self, text):
        self.queue.put(WindowController.PrintOperation(text))

    def set_label(self, label):
        self.queue.put(WindowController.SetLabelOperation(label))

    def terminate(self):
        self.queue.put(WindowController.TerminateOperation())

    def set_title(self, title):
        self.queue.put(WindowController.SetTitleOperation(title))