from fedasync.commons.utils.producer import Producer


class TestProducer(Producer):
    def __init__(self):
        super().__init__()

    def send_msg(self, msg):
        self.publish_message(
            ""
        )



