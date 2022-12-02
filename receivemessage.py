from flask import Flask, jsonify, redirect, url_for, render_template, request, flash, session
import requests
import json
import os
from twilio.rest import Client
from oauth2client.service_account import ServiceAccountCredentials
import gspread

app = Flask(__name__)
app.secret_key = "five9chattranslate"
flask_session = requests.Session()

scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Assign credentials ann path of style sheet
creds = ServiceAccountCredentials.from_json_keyfile_name("twiliooutboundsurvey-782aa8d520f8.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Five9Whatsappintegration").sheet1

# Function to initaite a conversation in Five9
def initiate_conversation(whatsapp_number, w_message):

    # API to login to the chat as anonymous user
    chat_url = 'https://app.five9.com:443/appsvcs/rs/svc/auth/anon'
    # Set proper headers
    headers = {
        "Content-Type":"application/json",
        "Accept":"*/*", 
        "Accept-Encoding":"gzip, deflate, br"
        }
    
    flask_session.headers.update(headers)
    # Body of the request
    datas = {"tenantName":"Tata Consulting Services Trial Domain"}
        

    data = json.dumps(datas)

    # Send the request
    response = flask_session.post(chat_url, headers=headers ,data=data)
    response = response.json()
    print(response)

    # Store the response value in variable and google sheet
    # session['tokenId'] = response['tokenId']
    tokenId = response['tokenId']
    
    # session['userId'] = response['userId']
    # session['farmID'] = response['context']['farmId']
    farmID = response['context']['farmId']
    
    # API to initiate the chat 
    conversation_url = 'https://app-atl.five9.com:443/appsvcs/rs/svc/conversations'

    # Set the authorisation for header
    author = "Bearer "+ tokenId
    # Set proper headers
    headers = {
        "Content-Type":"application/json",
        "Accept":"*/*", 
        "Accept-Encoding":"gzip, deflate, br",
        "Authorization": author,
        "farmId" : farmID
        }
    
    flask_session.headers.update(headers)

    # body of the request
    datas = {"campaignName":"Z_chat",
            "tenantId":"131096",
            "callbackUrl":"https://0fe6-14-143-71-138.ngrok.io/",
            "contact":{"number1":whatsapp_number},
            "attributes":{ "Question":w_message}
            }
        

    data = json.dumps(datas)

    # Send the request
    response = flask_session.post(conversation_url, headers=headers ,data=data)
    response = response.json()
    print(response)

    # Add the details in the Google Sheet
    insertRow = [response['id'], whatsapp_number, farmID, tokenId, 'en', '{"message":[]}','en']
    append = sheet.append_row(insertRow)
    # data_message[response['id']] = []
    # print(session)
    print(append)
    return response

def send_message(user_message,ConversationID, convo_row_details,language_user, row_number):
    
    output = json.loads(convo_row_details[5])
    
    message = user_message
    # Google transltor API to translator customer message from their language to english 
    # message = translator.translate(user_message, src=language_user, dest ='en')
    # print(message.src)
    # print(message.dest)
    # message = message.text
    # print(message)
    
    # Update the existing google sheet conversation message with additional message
    output['message'].append({"User":message})
    
    update_cell = sheet.update_cell(row_number, 6, json.dumps(output))

    # Check whether the language user communicating is same as language selected before
    # If not update the current language
    # if not language_user == convo_row_details[3]:
    #     update_lang_cell = sheet.update_cell(row_number, 4, language_user)
    
     
    # API to send message to Agent
    message_url = 'https://app-atl.five9.com:443/appsvcs/rs/svc/conversations/'+ConversationID+'/messages'
    
    # update the authorizarion bearer with the token id in google sheet
    author = "Bearer "+convo_row_details[3]
    # Set proper headers with the authoriation and farm ID
    headers = {
        "Content-Type":"application/json",
        "Accept":"*/*", 
        "Accept-Encoding":"gzip, deflate, br",
        "Authorization": author,
        "farmId" : convo_row_details[2]
        }
    # session = requests.Session()
    flask_session.headers.update(headers)

    # Body of the request
    datas = {
        "messageType": "TEXT", 
        "message": message
        }
    
    data = json.dumps(datas)

    # Send the request
    response = flask_session.post(message_url, headers=headers ,data=data)
    
    print(response)
    return output



def find_row_content_by_number(whatsapp_number):
    row_details = sheet.find(whatsapp_number)
    if row_details==None:
        return None,None
    else:
        convo_row_details= sheet.row_values(row_details.row)
        print(convo_row_details)
        return convo_row_details, row_details.row


def find_row_content_by_converID(ConversationID):
    row_details = sheet.find(ConversationID)
    if row_details==None:
        return None,None
    else:
        convo_row_details= sheet.row_values(row_details.row)
        print(convo_row_details)
        return convo_row_details, row_details.row

@app.route('/receive',methods=["POST",'GET'])
def receivemessage():
    # print("hello")
    # print((request.form['Body']))
    # print((request.form['To']))
    request_data = request.form
    Twilio_Whatsapp_res = request.form['From']
    whatsapp_number = Twilio_Whatsapp_res[10:]
    w_message = request.form['Body']
    print(whatsapp_number)
    convo_row_details, row_number = find_row_content_by_number(whatsapp_number)
    #Check for Whatsappp number in Google sheet, if not present initiate a new conversation in five9 as anonymous user    row_details = sheet.find(whatsapp_number)
    if convo_row_details == None:
        initiate_conv = initiate_conversation(whatsapp_number, w_message)
        convo_row_details, row_number = find_row_content_by_number(whatsapp_number)
        send_conv = send_message(w_message, convo_row_details[0], convo_row_details, 'en', row_number)
    else:
        send_conv = send_message(w_message, convo_row_details[0], convo_row_details, 'en', row_number)
    
    # print(row_details)
    # convo_row_details= sheet.row_values(row_details.row)
    # print(convo_row_details)
    
    return request.form

# @app.route('/send',methods=["POST",'GET'])
def send_to_whatsapp(whatsapp_number, a_message):
    whatsapp_number = 'whatsapp:+'+whatsapp_number
    account_sid = 'ACdda77ed9521627c00b41ca7663e30713'
    auth_token = '0c4ff07a620d690cfd730f3946e8b572'
    client = Client(account_sid, auth_token)

    message = client.messages.create(
                                from_='whatsapp:+14155238886',
                                body=a_message,
                                to=whatsapp_number
                            )

    print(str(message))
    return str(message)

def async_get_data(request, ConversationID, convo_row_details, row_number):
    # global data_message
    data = json.loads(request.data)
    # print(session)
    # print(data['text'])

    # print(convo_row_details)
    output = json.loads(convo_row_details[5])
    
    
    # output['message'].append({data['displayName']:data['text']})
    # update_cell = sheet.update_cell(row_number, 5, json.dumps(output))
    
    # print(output)
    # message = translator.translate(data['text'], src=convo_row_details[6], dest='en')
    # print(message)
    # message = message.text
    # print(message)
    message = data['text']
    output['message'].append({data['displayName']:message})
    update_cell = sheet.update_cell(row_number, 6, json.dumps(output))
    
    # print(data_message)
    
    # data_message[ConversationID].append({data['displayName']: message})
    
    print('Message Received from agent')
    return message


# route to get the message sent from the agent
@app.route('/conversations/<convoid>/message',methods=["POST",'GET'])
def contsendmessage(convoid):
    # if request.method=='POST':
    request_data = request.form
    print(request)
    # Search for the conversation ID in the Google sheet
    convo_row_details, row_number = find_row_content_by_converID(convoid)
    
    if not convo_row_details == None:

        # Call the async_get_data function
        data = async_get_data(request, convoid, convo_row_details,row_number)
        # Send message to whatsapp number
        whatsapp_res = send_to_whatsapp(convo_row_details[1], data)

    return 'OK'


# Function to get the message and users language from the google sheet
def process_url(ConversationID, update):
    
    row_details = sheet.find(ConversationID)
    # Update the message cell to below if the conversation is terminated on the agent end
    if update:
        update_cell = sheet.update_cell(row_details.row, 6, '{"message":["ended"]}')
    convo_row_details= sheet.row_values(row_details.row)
    output = json.loads(convo_row_details[5])

    return output,convo_row_details[2]


# route to check the chat accepted by the agent

@app.route('/conversations/<convoid>/accept',methods=["POST",'GET','PUT'])
def contacceptmessage(convoid):
    message = {"message":"Agent accepted the chat"}
    flash(message)
    output,whatsapp_number = process_url(convoid, False)
    send_to_whatsapp(whatsapp_number,"Agent has joined the chat")
    return {'body':'success'}

# route to check the chat created

@app.route('/conversations/<convoid>/create',methods=["POST",'GET','PUT'])
def contcreatemessage(convoid):
    message = {"message":"Chat created successfully"}
    flash(message)
    output,lang = process_url(convoid, False)
    return {'body':'success'}

# route to check status message typing by the agent
@app.route('/conversations/<convoid>/typing',methods=["POST",'GET','PUT'])
def conttypingmessage(convoid):
    message = {"message":"Agent typing"}
    flash(message)
    output,lang = process_url(convoid, False)
    return {'body':'success'} 

# route to get the chat terminated by the agent
@app.route('/conversations/<convoid>/terminate',methods=["POST",'GET','PUT'])
def contterminatemessage(convoid):
    message = {"message":"Chat terminated by agent, Create a new chat"}
    flash(message)
    output,whatsapp_number = process_url(convoid, True)
    send_to_whatsapp(whatsapp_number,"Agent has left the chat")

    
    return {'body':'success'}

if __name__ == '__main__':
   app.run(port=8080)