class VQIB:
    def __init__(self, voice_client=None, queue=None, interaction=None, bot=None, query=None):
        self._voice_client = voice_client
        self._queue = queue
        self._interaction = interaction
        self._bot = bot
        self._query = query

    @property
    def voice_client(self):
        return self._voice_client
    
    @voice_client.setter
    def voice_client(self, value):
        self._voice_client = value

    @property
    def queue(self):
        return self._queue
    
    @queue.setter
    def queue(self, value):
        self._queue = value

    @property
    def interaction(self):
        return self._interaction
    
    @interaction.setter
    def interaction(self, value):
        self._interaction = value

    @property
    def bot(self):
        return self._bot
    
    @bot.setter
    def bot(self, value):
        self._bot = value

    @property
    def query(self):
        return self._query
    
    @query.setter
    def query(self, value):
        self._query = value