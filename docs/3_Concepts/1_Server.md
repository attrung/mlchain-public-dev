The main component of the ML-Chain library is the deployment of API effortlessly, 
customizable depending on developers' specification. This allows AI products to be scaled 
quickly, fostering better communication between various procedures.


## 1. Base Model

ML-Chain main function is the ServeModel class. This is essentially a wrapper, that
 takes various function created by your model and return the output in a web-based 
app.

This allows you to quickly deploy an app without having to build back-end software engineering 
products that might be time-consuming and cumbersome.

```python
from mlchain.base import ServeModel

class YourModel:
    def predict(self,input:str):
        '''
        function return output from input
        '''
        return output

model = YourModel()

serve_model = ServeModel(model)
```

To host the above model, you can simply run the command

```bash
mlchain run server.py --host localhost --port 5000
```

and your website should be hosting at http://localhost:5000

The definition of the ServeModel class is as followed:

```
class ServeModel(object):
    def __init__(self, model, name=None, deny_all_function=False, 
    blacklist=[], whitelist=[]):
```

#### Variables:

- model (instance): The model instance that you defined, including the model itself and 
accompanying function (eg. predict)

- deny_all_function (bool): Do not return any route, except for those in whitelist
(default: False)

- blacklist (list): list of functions that are not used. Use with deny_all_function == False.

- whitelist (list): list of functions that are always used. Use with deny_all_function == True.

## 2. Serializer:

ML-Chain server function provides 3 main serializer options that allows developers to decide 
how their packages can be sent and received. These includes:

#### Json:



#### Message Pack:




#### Message Pack Blosc:




## 3. Sever:

#### Flask:

ML-Chain is currently supporting Flask as its main framework to serve and deploy machine learning model. 




## 4. Server Wrapper:

#### Gunicorn Wapper:

ML-Chain is currently using Gunicorn as its main wrapper. This option is compatible with multiple server and operating systems, allowing ML chain to be deployed and used accross multiple devices. It is also stable for scaling to use multiple workers, which
speeds up application respond time in many AI-based applications.