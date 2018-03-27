# gremlin-python-example
An example project for gremlin_python, as there is very little public code out there using it.

This project also uses Chalice (https://github.com/aws/chalice)

### Instructions
```commandline
>> mkvirtualenv neptunedemo --python=python3.6
>> pip install chalice
>> pip install gremlinpython
```
* Clone this repo to your project folder
* Set GRAPH_DB in .chalice/config.json to your graph db
* _export AWS_DEFAULT_REGION=us-east-1_ if using AWS Neptune

```commandline
>> chalice deploy
```

Then send http requests (examples below) to your new endpoint.

If using AWS Neptune:
* Add AWSLambdaVPCAccessExecutionRole to the lambda role
* Set the correct VPC, subnet and SG

### Example Requests

##### New Person
POST to https://whatever.execute-api.us-east-1.amazonaws.com/api/person
```json
{"id": "XYZ1234", "prop1": "Some", "prop2": "Value"}
```

##### Retrieve Person
GET to https://whatever.execute-api.us-east-1.amazonaws.com/api/person/XYZ1234

##### Update Person
PUT to https://whatever.execute-api.us-east-1.amazonaws.com/api/person/XYZ1234
```json
{"id": "XYZ1234", "prop1": "Some", "prop2": "NewValue"}
```

##### Upsert Relationship
POST to https://whatever.execute-api.us-east-1.amazonaws.com/api/relationship
```json
{"from": "XYZ1234", "to": "BOB", "weight": "1.0"}
```

##### Retrieve Known Associates
GET to https://whatever.execute-api.us-east-1.amazonaws.com/api/relationship/XYZ1234

You can optionally add a ?threshold=0.n parameter to the querystring to set the 
threshold of relationship weighting to retrieve.

##### Clear Graph
DELETE to https://whatever.execute-api.us-east-1.amazonaws.com/api/clear

### TODOs

* Cleanup the retrieval query
* Add more unit tests using TinkerGraph
* Add Cognito for authorisation of requests
* Extend demo instructions to include graph db setup
* Add additional options to the search 

### Additional reading
* http://kelvinlawrence.net/book/Gremlin-Graph-Guide.html
* https://docs.aws.amazon.com/neptune/latest/userguide/
* http://chalice.readthedocs.io/