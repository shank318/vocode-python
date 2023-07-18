class BaseConversationRecorder:
    def add_data_stream(self, chunk: bytes):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop_recording(self):
        raise NotImplementedError
