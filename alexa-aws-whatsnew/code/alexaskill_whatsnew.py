
from __future__ import print_function
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
from datetime import timedelta
from collections import defaultdict
import json
import re
import os


aws_feed_tbl = os.environ['awslaunchdetails_tbl']

dynamo_tbl = boto3.resource('dynamodb').Table(aws_feed_tbl)
Whatsnew_AWS = " Say what is new?"
Next_item = " Say go to next item"
Previous_item = " Say go to previous item"
Not_Valid_Input = " Your input is not valid. Select a category by saying tell me about "
OR = ". Or, "
Repeat_item = ".\n To repeat all categories, Say repeate it"
Tell_more = ".\n To know more about it, Say more."
Refine_search =" To search features from a specific day. Say refine search from yesterday"
reprompt_play_text = "To read other features launched in this category, say go to next or previous. To know more about this feature, say more"
date_regex = re.compile('^\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])$')
skip_services = ["lex"]


def default_filter_date():
    refresh_days = 7
    filter_date = datetime.now() - timedelta(days=refresh_days)
    formatted_Date = filter_date.strftime("%Y-%m-%d")
    return formatted_Date

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to the Alexa Skill Cloud Assist. " \
                    "You can ask me about recent AWS features launched by saying, " \
                    "what is new?"
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Ask me about AWS recent launches by saying, " \
                    "what new in AWS?"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for trying the Alexa Cloud Assist skill. " \
                    "Have a wonderful day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def massage_category_name(category_name):
    #category_name = category_name.replace("53"," fifty three")
    if len(category_name) < 4 and category_name not in skip_services:
        #category_name = ".".join(category_name)
        #category_name = category_name.replace("2"," two")
        #category_name = category_name.replace("3"," three")
        category_name = category_name.upper()
    return category_name

def retrieve_features(qry_date):
    response = dynamo_tbl.scan(
        ProjectionExpression="catagories,guid,title",
        FilterExpression=Key('pub_date').gte(qry_date))
    category_dict=defaultdict(list)

    if( len(response['Items']) > 0 ):
        count = 1

        for record in response['Items']:
            for cat in record['catagories']:
                cat=massage_category_name(cat)
                category_dict[cat].append({'title':record['title'],'guid':record['guid']})

        while 'LastEvaluatedKey' in response:
            response = dynamo_tbl.scan(
                ProjectionExpression="catagories,guid,title",
                FilterExpression=Key('pub_date').gte(qry_date),
                ExclusiveStartKey=response['LastEvaluatedKey']
                )

            for record in response['Items']:
                for cat in record['catagories']:
                    cat=massage_category_name(cat)
                    category_dict[cat].append({'title':record['title'],'guid':record['guid']})
    return category_dict

def check_end_session(category_dict):
    categories = category_dict.keys()
    if len(categories) == 0 or \
        ( len(category_dict) == 1 and len(category_dict[categories[0]]) == 1 ):
        return True
    else :
        return False

def get_aws_titles(category_dict,session_attributes,repeat_flag):
    categories = category_dict.keys()
    if len(categories) == 0:
        speech_output = "Hmm. I think developers are resting. There is no new feature launched in A W S. Thank you."

    elif( len(category_dict) == 1 and len(category_dict[categories[0]]) == 1 ):
        speech_output = "There is one new feature released.\n"
        record = category_dict[categories[0]][0]
        speech_output = speech_output + record["title"]
        speech_output = speech_output + Tell_more
        session_attributes['selected_guid']=record['guid']
    else:
        if repeat_flag:
            speech_output ="Sure. The categories are "
        else:
            speech_output = "There are many new features released on following " \
                + str(len(categories)) + " categories namely, \n "
        count = 1
        categories.sort()
        for cat in categories:
            speech_output = speech_output + cat + ".\n "
            count = count + 1
        if not repeat_flag:
            speech_output = speech_output + ". To know about a category, say tell me about " + categories[1]
            speech_output = speech_output + OR + Refine_search
        session_attributes['search_json'] = category_dict

    return speech_output


def get_category_from_session(session_attributes,category):
    sel_category=""
    if session_attributes and "search_json" in session_attributes:
        search_json = session_attributes['search_json']
        if search_json and category in search_json:
            sel_category=category
        else:
            sel_category=get_category_by_partial_search(search_json,category)
    return sel_category

def get_category_by_partial_search(search_json,search_text):
    iterator = iter(search_json)
    category_name = next(iterator,"None")
    search_string_list= search_text.split( )
    while category_name is not "None":
        for search_str in  search_string_list:
            if search_str in category_name or search_str in json.dumps(search_json[category_name]):
                return category_name
        category_name = next(iterator,"None")
    return ""

def get_title_from_session(session_attributes,category,item_index):
    title=""
    if session_attributes and "search_json" in session_attributes:
        search_json = session_attributes['search_json']
        if search_json[category] and len(search_json[category]) > item_index:
                title = search_json[category][item_index]["title"]
    return title

def set_new_features_in_session(intent, session,filterdate):
    should_end_session = True
    reprompt_text=""
    session_attributes = {}
    category_dict = retrieve_features(filterdate)
    speech_output = get_aws_titles(category_dict,session_attributes,False)
    should_end_session = check_end_session(category_dict)
    if not should_end_session:
        reprompt_text = "Yeah! thats a hard choice. You can select a category by simply saying tell me about " \
            + next(iter(category_dict))
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def get_item_for_category(intent, category, session):
    session_attributes = session.get('attributes', {})
    should_end_session = False
    reprompt_text = reprompt_play_text
    if session_attributes and "search_json" in session_attributes:
        sel_category = get_category_from_session(session_attributes,category)
        search_json = session_attributes['search_json']
        if sel_category:
            session_attributes["selected_cat"]=sel_category
            session_attributes["item_index"]="0"
            print(search_json[sel_category][0])
            session_attributes['selected_guid']=search_json[sel_category][0]["guid"]
            speech_output = "You have selected category as " + session_attributes["selected_cat"] + ". "
            if len(search_json[sel_category]) > 1:
                speech_output = speech_output + " There are " + str(len(search_json[sel_category])) + " features launched. "
            speech_output = speech_output + get_title_from_session(session_attributes,sel_category,0)
            speech_output = speech_output + Tell_more
            if len(search_json[sel_category]) > 1:
                speech_output = speech_output + OR + Next_item
        else:
            speech_output = Not_Valid_Input + next(iter(search_json))
    else:
        speech_output = "Before selecting a category," + Whatsnew_AWS

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


def tell_more_about_feature(intent, session):
    session_attributes = session.get('attributes', {})
    reprompt_text = reprompt_play_text
    should_end_session = False
    if session_attributes and "selected_guid" in session_attributes:
        response = dynamo_tbl.query(
            ProjectionExpression="description",
            KeyConditionExpression=Key('guid').eq(session_attributes["selected_guid"])
        )
        if len(response['Items']) > 0 :
            speech_output = response['Items'][0]["description"]
    else:
        speech_output = "You need to retrieve features," + Whatsnew_AWS

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def go_to_previous_feature(intent, session):
    reprompt_text = reprompt_play_text
    should_end_session = False
    session_attributes = session.get('attributes', {})
    if session_attributes and "search_json" in session_attributes \
       and "selected_cat" in session_attributes and "item_index" in session_attributes:
        sel_category = session_attributes["selected_cat"]
        item_index = int(session_attributes["item_index"]) - 1
        category_size = len(session_attributes["search_json"][sel_category])
        if item_index < category_size and item_index >= 0:
            title = get_title_from_session(session_attributes,sel_category,item_index)
            if title:
                session_attributes["item_index"]=str(item_index)
                session_attributes['selected_guid']=session_attributes["search_json"][sel_category][item_index]['guid']
                speech_output = " The previous selected feature in category " + sel_category
                speech_output = speech_output + " " + title + Tell_more
        elif category_size == 1:
            speech_output = "The category " + sel_category + " has only one feature." + Repeat_item
        else:
            speech_output = "No more feature to go back in category " + sel_category + Repeat_item
    else:
        speech_output = "You need to retrieve features," + Whatsnew_AWS

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def go_to_next_feature(intent, session):
    reprompt_text = reprompt_play_text
    should_end_session = False
    session_attributes = session.get('attributes', {})
    if session_attributes and "search_json" in session_attributes \
      and "selected_cat" in session_attributes and "item_index" in session_attributes:
        sel_category = session_attributes["selected_cat"]
        item_index = int(session_attributes["item_index"]) + 1
        category_size = len(session_attributes["search_json"][sel_category])
        if item_index < category_size and item_index >= 0:
            title = get_title_from_session(session_attributes,sel_category,item_index)
            if title:
                session_attributes["item_index"]=str(item_index)
                session_attributes['selected_guid']=session_attributes["search_json"][sel_category][item_index]['guid']
                speech_output = " The next selected feature in category " + sel_category
                speech_output = speech_output + " " + title + Tell_more
        elif category_size == 1:
            speech_output = "The category " + sel_category + " has only one feature." + Repeat_item
        else:
            speech_output = "No more feature to go next in category " + sel_category + Repeat_item
            speech_output = speech_output + " Or, " + Previous_item
    else:
        speech_output = "You need to retrieve features," + Whatsnew_AWS

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def go_to_main_menu(intent,session):
    should_end_session = False
    session_attributes = session.get('attributes', {})
    if session_attributes and "search_json" in session_attributes :
        category_dict=session_attributes["search_json"]
        speech_output = get_aws_titles(category_dict,session_attributes,True)
    reprompt_text =" To know more say tell me about " + next(iter(category_dict))

    return build_response(session_attributes, build_speechlet_response(
         intent['name'], speech_output, reprompt_text, should_end_session))

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "Whatsnew_AWS":
        return set_new_features_in_session(intent, session,default_filter_date())
    if intent_name == "Whatsnew_AWS_Date":
        if 'value' in intent_request['intent']['slots']['Date']:
            filterdate = intent_request['intent']['slots']['Date']['value']
            if date_regex.match(filterdate):
                return set_new_features_in_session(intent, session,filterdate)
            else:
                return set_new_features_in_session(intent, session,default_filter_date())
        else:
            return set_new_features_in_session(intent, session,default_filter_date())
    #elif intent_name == "Select_free_category":
    #    category_name = intent_request['intent']['slots']['FreeCategory']['value']
    #    category_id = get_category_id_from_name(intent, category_name, session)
    #    return get_item_for_category_id(intent, category_id, session)
    elif intent_name == "Select_category":
        category_name = intent_request['intent']['slots']['Category']['value']
        #category_id = get_category_id_from_name(intent, category_name, session)
        print(category_name)
        return get_item_for_category(intent, category_name, session)
    elif intent_name == "Tell_more":
        return tell_more_about_feature(intent, session)
    elif intent_name == "Next_item":
        return go_to_next_feature(intent, session)
    elif intent_name == "Previous_item":
        return go_to_previous_feature(intent, session)
    elif intent_name == "Repeat_categories":
        return go_to_main_menu(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.ask.skill.50da5a53-425b-4f2f-a032-7f420096cda0"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
