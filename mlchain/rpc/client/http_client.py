from urllib.error import HTTPError
import httpx
from mlchain.base.client import ClientBase
from mlchain import logger

TIMEOUT = httpx.Timeout(5 * 60)
# TIMEOUT = httpx.Timeout()

class HttpClient(ClientBase):
    """
    Mlchain Client Class
    """
    def __init__(self, api_key = None, api_address = None, serializer='json'):
        """
        Client to communicate with Mlchain server 
        :api_key: Your API KEY 
        :api_address: API or URL of server to communicate with 
        :serializer: The way to serialize data ['json', 'msgpack', 'msgpack_blosc']
        """
        super().__init__(api_key, api_address, serializer)

    def __format_error(self, response):
        if response.status_code == 404:
            return {
                'error': 'This request url is not found',
                'time': 0
            }
        elif response.status_code == 500:
            try:
                error = self.serializer.decode(response.content)
            except:
                error = self.json_serializer.decode(response.content)

            if 'error' in error:
                return {
                    'error': error['error'],
                    'time': 0
                }
            else:
                return {
                    'error': 'Server run error, please try again',
                    'time': 0
                }
        else:
            return {
                'error': "There's something error, error code: {0}".format(response.status_code),
                'time': 0
            }

    def check_response_ok(self, response):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        try:
            response.raise_for_status()
        except:
            return False
        return True

    def post(self, url, input, files, headers = None, **params):
        """
        POST input data and get result with synchronous 
        """
        assert isinstance(files, list), "files must be list"
        if headers is None:
            headers = {}
        headers = {
            'Content-type': self.content_type,
            **headers
        }


        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        with httpx.Client(timeout=TIMEOUT) as client:
            if len(files) > 0:
                # It must be Json here
                input_encoded = self.json_serializer.encode(input)

                files.append(("MLCHAIN INPUT", (None, input_encoded, 'application/octet-stream')))
                headers.pop("Content-type")
                headers['serializer'] = "application/json" # Msgpack hasn't supported yet

                output = client.post("{0}/{1}".format(self.api_address, url), headers=headers, params=params, files=files)
            else:
                input_encoded = self.serializer.encode(input)
                output = client.post("{0}/{1}".format(self.api_address, url), data = input_encoded, headers=headers, params=params)

        if not self.check_response_ok(output):
            return self.__format_error(output)
        if output.status_code != 200:
            if len(files) > 0:
                output_decoded = self.json_serializer.decode(output.content)
            else:
                output_decoded = self.serializer.decode(output.content)
            raise AssertionError("\nREMOTE API ERROR: {0}".format(output_decoded))
        if len(files) > 0:
            output_decoded = self.json_serializer.decode(output.content)
        else:
            output_decoded = self.serializer.decode(output.content)
        return output_decoded
    
    def get(self, url, **params):
        """
        GET data from url 
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        with httpx.Client(timeout=TIMEOUT) as client:
            output = client.get("{0}/{1}".format(self.api_address, url), headers=headers, params=params)

        if not self.check_response_ok(output):
            return self.__format_error(output)

        output_decoded = self.serializer.decode(output.content)
        return output_decoded

    def put(self, url, input, **params):
        """
        PUT data from url 
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        inputs_encoded = self.serializer.encode(input)

        with httpx.Client(timeout=TIMEOUT) as client:
            output = client.put("{0}/{1}".format(self.api_address, url), data=inputs_encoded, headers=headers, params=params)

        if not self.check_response_ok(output):
            return self.__format_error(output)

        output_decoded = self.serializer.decode(output.content)
        return output_decoded
    
    def patch(self, url, **params):
        """
        PATCH data from url 
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        with httpx.Client(timeout=TIMEOUT) as client:
            output = client.patch("{0}/{1}".format(self.api_address, url), headers=headers, params=params)

        if not self.check_response_ok(output):
            return self.__format_error(output)

        output_decoded = self.serializer.decode(output.content)
        return output_decoded

    def delete(self, url, **params):
        """
        DELETE data from url 
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        with httpx.Client(timeout=TIMEOUT) as client:
            output = client.delete("{0}/{1}".format(self.api_address, url), headers=headers, params=params)
            
        if not self.check_response_ok(output):
            return self.__format_error(output)

        output_decoded = self.serializer.decode(output.content)
        return output_decoded

    async def post_async(self, url, input, files, **params):
        """
        POST input data and get result in asynchronous 
        """
        assert isinstance(files, list), "files must be list"
        headers = {
            'Content-type': self.content_type
        }

        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        async with httpx.AsyncClient(backend="trio", timeout=TIMEOUT) as client:
            if len(files) > 0:
                # It must be Json here
                input_encoded = self.json_serializer.encode(input)

                files.append(("MLCHAIN INPUT", (None, input_encoded, 'application/octet-stream')))
                headers.pop("Content-type")
                headers['serializer'] = "application/json" # Msgpack hasn't supported yet

                output = await client.post("{0}/{1}".format(self.api_address, url), headers=headers, params=params, files=files, timeout=TIMEOUT)
            else:
                input_encoded = self.serializer.encode(input)

                output = await client.post("{0}/{1}".format(self.api_address, url), data = input_encoded, headers=headers, params=params, timeout=TIMEOUT)

        if not self.check_response_ok(output):
            return self.__format_error(output)

        if len(files) > 0:
            output_decoded = self.json_serializer.decode(output.content)
        else:
            output_decoded = self.serializer.decode(output.content)
        return output_decoded
    
    async def get_async(self, url, **params):
        """
        GET data from url in asynchronous 
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        async with httpx.AsyncClient(backend="trio", timeout=TIMEOUT) as client:
            output = await client.get("{0}/{1}".format(self.api_address, url), headers=headers, params=params, timeout=TIMEOUT)
        if not self.check_response_ok(output):
            return self.__format_error(output)

        output_decoded = self.serializer.decode(output.content)
        return output_decoded

    async def put_async(self, url, input, **params):
        """
        PUT data from url in asynchronous 
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        inputs_encoded = self.serializer.encode(input)

        async with httpx.AsyncClient(backend="trio", timeout=TIMEOUT) as client:
            output = await client.put("{0}/{1}".format(self.api_address, url), data=inputs_encoded, headers=headers, params=params, timeout=TIMEOUT)
        if not self.check_response_ok(output):
            return self.__format_error(output)

        output_decoded = self.serializer.decode(output.content)
        return output_decoded
    
    async def patch_async(self, url, **params):
        """
        PATCH data from url in asynchronous  
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        async with httpx.AsyncClient(backend="trio", timeout=TIMEOUT) as client:
            output = await client.patch("{0}/{1}".format(self.api_address, url), headers=headers, params=params, timeout=TIMEOUT)
        if not self.check_response_ok(output):
            return self.__format_error(output)
            
        output_decoded = self.serializer.decode(output.content)
        return output_decoded

    async def delete_async(self, url, **params):
        """
        DELETE data from url in asynchronous  
        """
        headers = {
            'Content-type': self.content_type
        }
        if self.api_key is not None:
            headers['Authorization'] = self.api_key

        async with httpx.AsyncClient(backend="trio", timeout=TIMEOUT) as client:
            output = await client.delete("{0}/{1}".format(self.api_address, url), headers=headers, params=params, timeout=TIMEOUT)
        if not self.check_response_ok(output):
            return self.__format_error(output)
            
        output_decoded = self.serializer.decode(output.content)
        return output_decoded