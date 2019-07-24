import logging
import os

from chalice import Chalice, BadRequestError, NotFoundError
from gremlin_python import statics
from gremlin_python.structure.graph import Graph
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.strategies import *
from gremlin_python.process.traversal import T, P, Operator
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection


app = Chalice(app_name='neptunedemochalice')
app.debug = True

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


def setup_graph():
    try:
        graph = Graph()
        connstring = os.environ.get('GRAPH_DB')
        logging.info('Trying To Login')
        g = graph.traversal().withRemote(DriverRemoteConnection(connstring, 'g'))
        logging.info('Successfully Logged In')
    except Exception as e:  # Shouldn't really be so broad
        logging.error(e, exc_info=True)
        raise BadRequestError('Could not connect to Neptune')
    return g


def get_person(person_id, g):
    """
    TODO - add more ways of finding a person than just the id.

    :param person_id:
    :param g:
    :return:
    """

    person = g.V(person_id).toList()
    logging.info("People found are: %s" % person)
    # If not found
    if not person:
        return None
    # Just in case there is more than one - shouldn't happen
    if len(person) > 1:
        raise ValueError('More than one person found for id: %s' % person_id)
    return person[-1]


def vertex_to_json(vertex, g):
    # TODO - Almost certainly a better way of doing this
    values = g.V(vertex).valueMap().toList()[0]
    values["id"] = vertex.id
    return values


#  Insert new person
@app.route('/person', methods=['POST'])
def new_person():
    logging.info('Request Received: Add New Person')
    g = setup_graph()
    try:
        properties = app.current_request.json_body
        # TODO - Validate the JSON
        logging.info('Adding New Person to Graph')
        # Get the ID from the JSON
        person_id = properties.pop('id')
        if not person_id:
            raise BadRequestError('Missing "id" in body')
        person = get_person(person_id=person_id, g=g)
        if person:
            raise BadRequestError('id "%s" already exists' % person_id)
        # TODO - Validate there is a single unique ID
        person = g.addV('person').property(T.id, person_id).next()
        # Ideally I would roll this into a single call
        logging.info("Received Properties: " + str(properties))
        for prop_name, prop_value in properties.items():
            g.V(person).property(prop_name, prop_value).next()
    except(ValueError, AttributeError, TypeError) as e:
        logging.error(e, exc_info=True)
        raise BadRequestError('Could not insert person.  Error: ' + str(e))
    logging.info("Successfully inserted person")
    return {"id": person_id}

#  get all persons
@app.route('/persons', methods=['GET'])
def get_persons():
    logging.info('Request Received: Persons')
    g = setup_graph()
    return [{**node.__dict__, **properties} for node in g.V()
            for properties in g.V(node).valueMap()]

#  Update/get person details
@app.route('/person/{person_id}', methods=['PUT', 'GET'])
def process_person(person_id):
    log_string = 'Update' if app.current_request.method == 'PUT' else 'Get'
    logging.info('Request Received: %s Person' % log_string)
    g = setup_graph()
    try:
        person = get_person(person_id=person_id, g=g)
        if not person:
            raise NotFoundError('id "%s" not found' % person_id)
        if app.current_request.method == 'GET':
            return vertex_to_json(vertex=person, g=g)
        else:
            properties = app.current_request.json_body
            # TODO - Validate the JSON
            logging.info('Updating Person on Graph')
            # Remove the existing properties
            g.V(person).properties().drop().iterate()
            # Ideally I would roll this into a single call
            logging.info("Received Properties: " + str(properties))
            for prop_name, prop_value in properties.items():
                g.V(person).property(prop_name, prop_value).next()
    except (ValueError, AttributeError, TypeError) as e:
        logging.error(e, exc_info=True)
        raise BadRequestError('Could not %s person.  Error: ' % log_string + str(e))
    logging.info("Successfully inserted person")
    return {"id": person_id}


#  Upsert relationship between people
@app.route('/relationship', methods=['POST'])
def upsert_relationship():
    logging.info('Request Received: Upsert Relationship')
    g = setup_graph()
    try:
        properties = app.current_request.json_body
        # TODO - Validate the JSON
        logging.info('Upserting Relationship to Graph')
        # Pull out the details
        from_person_id = properties.get('from')
        to_person_id = properties.get('to')
        weight = float(properties.get('weight', '0.5'))
        # This shouldn't be necessary, but is because of the open question about ids
        from_person = get_person(from_person_id, g)
        if not from_person:
            raise NotFoundError('id "%s" not found' % from_person_id)
        to_person = get_person(to_person_id, g)
        if not to_person:
            raise NotFoundError('id "%s" not found' % to_person_id)

        # There might be a better way of checking whether to addE or not
        # I saw reference to tryNext().orElseGet({addE}) but I need to get it to work in Python
        if g.V(from_person).outE('knows').filter(__.inV().is_(to_person)).toList():
            logging.info('Updating relationship')
            g.V(from_person).outE('knows').filter(__.inV().is_(to_person)).property('weight', weight).next()
        else:
            logging.info('Creating relationship')
            g.V(from_person).addE('knows').to(to_person).property('weight', weight).next()
    except(ValueError, AttributeError, TypeError) as e:
        logging.error(e, exc_info=True)
        raise BadRequestError('Could not upsert relationship.  Error: ' + str(e))
    logging.info("Successfully upserted relationship")


#  Search for known associates of person with criminality > x and relationship strength > y
@app.route('/relationship/{person_id}', methods=['GET'])
def get_known_associates(person_id):
    logging.info('Request Received: Get Known Associates')
    g = setup_graph()
    try:
        params = app.current_request.query_params if app.current_request.query_params else {}
        threshold = float(params.get('threshold', '0.5'))
        originating_person = get_person(person_id=person_id, g=g)
        # DEDUP

        people = g.withSack(1.0).V(originating_person).repeat(__.outE('knows').sack(Operator.mult).by('weight')
                                                              .inV()).until(__.sack().is_(P.lt(threshold))).emit()\
            .as_('b').sack().as_('a').select('a', 'b').toList()
        # Unfortunately the above query will include the final node which goes below the threshold
        # I'm sure there is a way to improve this query to not include it!  Until then, handle explicitly.
        # Similarly, I am deduping in Python - but ideally I would push this into the query (it's not a simple dedup
        # since I need to retain the max edge weight to make sure I don't mistakenly filter a dupe with < threshold)
        people = list(set([person['b'] for person in people if person['a'] >= 0.5]))
        logging.info("Found People: %s" % str(people))
        results = []
        for person in people:
            results.append(vertex_to_json(vertex=person, g=g))
    except(ValueError, AttributeError, TypeError) as e:
        logging.error(e, exc_info=True)
        raise BadRequestError('Could not retrieve known associates.  Error: ' + str(e))
    logging.info("Successfully retrieved known associates")
    return {'known_associates': results}


#  Update person details
@app.route('/clear', methods=['DELETE'])
def clear_graph():
    g = setup_graph()
    g.V().drop().iterate()
    return
