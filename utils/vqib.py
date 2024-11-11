class vqib:
    def __init__(self):
        self.voice_client = None
        self.queue = None
        self.interaction = None
        self.bot = None
            
    def set(self, voice_client, queue, interaction, bot):
        self.voice_client = voice_client
        self.queue = queue
        self.interaction = interaction
        self.bot = bot