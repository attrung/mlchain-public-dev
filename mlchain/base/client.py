import os 
import warnings
from mlchain.base.serializer import JsonSerializer, MsgpackSerializer, MsgpackBloscSerializer, JpgMsgpackSerializer, PngMsgpackSerializer
import mlchain

class ClientBase:
    """
    Mlchain Client base class
    """

    def __init__(self, api_key = None, api_address = None, serializer = 'msgpack', image_encoder=None):
        """
        Client to communicate with Mlchain server 
        :api_key: Your API KEY 
        :api_address: API or URL of server to communicate with 
        :serializer: The way to serialize data ['json', 'msgpack', 'msgpack_blosc']
        """
        assert serializer in ['json', 'msgpack', 'msgpack_blosc']
        assert image_encoder in ['jpg', 'png', None]

        if api_key is None and os.getenv('MLCHAIN_API_KEY') is not None:
            api_key = os.getenv('MLCHAIN_API_KEY')
        self.api_key = api_key

        if api_address is None:
            if os.getenv('MLCHAIN_API_ADDRESS') is not None:
                api_address = os.getenv('MLCHAIN_API_ADDRESS')
            else:
                api_address = mlchain.api_address
        self.api_address = api_address
        if isinstance(self.api_address, str):
            self.api_address = self.api_address.strip()
            if len(self.api_address) > 0 and self.api_address[-1] == '/':
                self.api_address = self.api_address[:-1]

            if len(self.api_address) > 0 and self.api_address[0] != 'h':
                self.api_address = 'http://{0}'.format(api_address)

        self.json_serializer = JsonSerializer()

        # Serializer initalization
        self.serializer_type = serializer
        try:
            if serializer == 'msgpack':
                if self.image_encoder is None:
                    self.serializer = MsgpackSerializer()
                elif self.image_encoder == 'jpg':
                    self.serializer = JpgMsgpackSerializer()
                elif self.image_encoder == 'png':
                    self.serializer = PngMsgpackSerializer()
            elif serializer == 'msgpack_blosc':
                self.serializer = MsgpackBloscSerializer()
            else:
                self.serializer_type = 'json'
                self.serializer = self.json_serializer
        except:
            self.serializer_type = 'json'
            self.serializer = self.json_serializer

        self.content_type = 'application/{0}'.format(self.serializer_type)
        self.image_encoder = image_encoder

    def get(self):
        raise NotImplementedError

    def post(self):
        raise NotImplementedError

    def put(self):
        raise NotImplementedError
    
    def patch(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def get_async(self):
        raise NotImplementedError

    def post_async(self):
        raise NotImplementedError

    def put_async(self):
        raise NotImplementedError
    
    def patch_async(self):
        raise NotImplementedError

    def delete_async(self):
        raise NotImplementedError